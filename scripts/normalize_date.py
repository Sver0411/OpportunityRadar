#!/usr/bin/env python3
"""normalize_date.py - 把多语言日期/截止日字符串归一化为 ISO 日期。

设计原则：
  1. **年份不明就不猜**：宁可返回 year_unknown=true，也不要编一个年份。
  2. **不同语义不混为一谈**：rolling / asap / flexible / tbd / unknown 是五种不同状态，
     不能都当成"滚动招募"。
  3. **区间的紧迫度以截止端点为准**：`9月20日~10月5日` 的紧迫度取决于 10-05，
     而不是 09-20。因此输出 days_until_start / days_until_end / urgency_days。
  4. **不丢时间与时区**：保留原文时间与时区标记并写明未做换算，不伪造 UTC。

用法：
  python3 normalize_date.py "2026-09-20"
  python3 normalize_date.py "9月20日" --default-year 2026
  python3 normalize_date.py "Sep 20 ~ Oct 5, 2026" --now 2026-09-14
  python3 normalize_date.py "2026-10-03 23:59 JST"
  python3 normalize_date.py "TBD"
  python3 normalize_date.py --file examples/dates.example.txt --default-year 2026
  python3 normalize_date.py "2026年9月20日" --format iso

支持：2026-09-20 / 2026/9/20 / 2026.9.20 / 2026年9月20日 / 9月20日 / 9月20号 /
      Sep 20, 2026 / 20 September 2026 / 20-Sep-2026 / September 2026 / Q3 2026 /
      区间：2026-09-20 ~ 2026-10-05 / 9月20日-10月5日 / Sep 20 - Oct 5, 2026 /
      状态：rolling / 随時受付 / 常年招募 / 招满即止 ｜ asap / 尽快 ｜
            flexible / 応相談 ｜ tbd / 未定 / 未公开
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys

# ---------------------------------------------------------------- 预处理

#: 滚动招募 / 招满为止 —— 没有固定截止日，随时可报
ROLLING_PATTERNS = (
    "rolling", "rolling basis", "on a rolling basis", "open until filled",
    "open until position is filled", "ongoing",
    "随時", "常時", "通年", "通年採用", "先着", "先着順", "定員になり次第",
    "常年", "随时", "常年招募", "招满即止", "招满为止", "先到先得", "长期有效", "无截止",
)

#: 尽快 / 即时 —— 有紧迫性但没有具体日期
ASAP_PATTERNS = ("asap", "a.s.a.p", "as soon as possible", "immediately", "urgent",
                 "尽快", "即時", "即日", "尽早")

#: 可协商 / 弹性 —— 时间存在但不固定
FLEXIBLE_PATTERNS = ("flexible", "flexibly", "negotiable", "to be negotiated",
                     "柔軟", "応相談", "相談可", "可协商", "弹性", "可调整")

#: 未公布 / 待定 —— 目前根本不知道
TBD_PATTERNS = ("tbd", "t.b.d", "tba", "to be announced", "to be determined",
                "to be confirmed", "not announced", "unannounced",
                "未定", "待定", "未公开", "未公布", "未确定", "不公开",
                "後日発表", "追って連絡", "另行通知", "另行公布")

LABEL_PREFIXES = (
    "application deadline", "application period", "deadline", "apply by", "due",
    "closes", "closing date", "registration",
    "报名截止", "截止日期", "申请截止", "投递截止", "报名时间", "截止",
    "応募締切", "申込締切", "締切", "応募期間", "申込期間",
)

MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

TZ_RE = re.compile(
    r"\b(JST|PST|PDT|EST|EDT|CST|CDT|MST|MDT|CET|CEST|GMT|UTC|BST|KST|HKT|IST|AEST|PT|ET|CT|MT)\b",
    re.I,
)
#: 时间之后的偏移量（09:00+09:00 / 09:00 +09:00）。必须紧跟时间：
#: 否则 "20-Sep-2026" 里的 "-2026" 会被误判成时区偏移。
TZ_OFFSET_ATTACHED_RE = re.compile(r"(?<=\d{2}:\d{2})\s*(Z|[+-]\d{2}:?\d{2})(?!\d)", re.I)
TIME_RE = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm|ＡＭ|ＰＭ)?", re.I)

#: 月份名只匹配真实月份（不能用 [A-Za-z]{3,9}——否则 "opens"、"Rolling" 这类词会
#: 被当成月份名并**吞掉后面的真实日期**，导致整条日期解析失败）
_MONTH_ALT = "|".join(sorted((re.escape(k) for k in MONTH_NAMES), key=len, reverse=True))

# 单个日期片段的匹配模式，顺序敏感（长的/更具体的放前面）
_PART = "|".join([
    r"(?P<iso_ymd>(?P<iso_y>\d{4})\s*[-/.年]\s*(?P<iso_m>\d{1,2})\s*[-/.月]\s*(?P<iso_d>\d{1,2})\s*日?|(?P<iso_y2>\d{4})\s*年\s*(?P<iso_m2>\d{1,2})\s*月\s*(?P<iso_d2>\d{1,2})\s*日)",  # noqa: E501
    r"(?P<ym>(?P<ym_y>\d{4})\s*[-/.年]\s*(?P<ym_m>\d{1,2})\s*月?)",
    r"(?P<slashed>(?P<sa>\d{1,2})\s*[-/.]\s*(?P<sb>\d{1,2})\s*[-/.]\s*(?P<sy>\d{4}))",
    rf"(?P<mdy>(?P<mname1>{_MONTH_ALT})\.?\s*(?P<md_d>\d{{1,2}})(?!\d)(?:st|nd|rd|th)?\s*[-\s]?\s*,?\s*(?P<md_y>\d{{4}})?)",
    rf"(?P<dmy>(?P<dm_d>\d{{1,2}})(?!\d)(?:st|nd|rd|th)?\s*[-\s]?\s*(?P<mname2>{_MONTH_ALT})\.?\s*[-\s]?\s*,?\s*(?P<dm_y>\d{{4}})?)",
    rf"(?P<my>(?P<mname3>{_MONTH_ALT})\.?\s*,?\s*(?P<my_y>\d{{4}}))",
    r"(?P<cnd>(?P<cn_m>\d{1,2})\s*月\s*(?P<cn_d>\d{1,2})\s*[日号])",
    r"(?P<cnm>(?P<cn_m2>\d{1,2})\s*月(?!\s*\d))",
    r"(?P<quarter>[Qq](?P<q_n>[1-4])\s*(?P<q_y>\d{4})?|(?P<q_y2>\d{4})\s*[Qq](?P<q_n2>[1-4]))",
])

DATE_RE = re.compile(_PART, re.I)


def _match_status(low: str):
    """返回 (deadline_type, matched_pattern) 或 None。按"信息量"从具体到模糊判断。"""
    for name, pats in (("rolling", ROLLING_PATTERNS), ("asap", ASAP_PATTERNS),
                       ("flexible", FLEXIBLE_PATTERNS), ("tbd", TBD_PATTERNS)):
        for p in pats:
            if p in low:
                return name, p
    return None


def preprocess(text: str) -> tuple[str, list[str]]:
    """归一化标点、去标签、全角转半角。返回 (clean_text, notes)。"""
    notes: list[str] = []
    s = (text or "").strip()
    if not s:
        return "", notes

    s = s.translate(str.maketrans("０１２３４５６７８９（）～．／－：", "0123456789()~./-:"))

    # 去星期标注：(月) （月） (Mon) (Monday) 月曜日
    s = re.sub(r"[(（]\s*(?:[月火水木金土日]|Mon|Tue|Wed|Thu|Fri|Sat|Sun|[A-Za-z]{6,9})\s*[)）]", " ", s)
    s = re.sub(r"[月火水木金土日]曜日", " ", s)

    low = s.lower()
    for label in LABEL_PREFIXES:
        idx = low.find(label)
        if idx != -1 and idx <= 8:
            s = s[idx + len(label):].lstrip(" :： 　-—")
            break

    s = s.replace("–", "-").replace("—", "-").replace("～", "~").replace("〜", "~")
    s = re.sub(r"\s+", " ", s).strip()
    return s, notes


def extract_time_tz(text: str):
    """抽取时间与时区标记。不换算，只记录。"""
    out = {"time": None, "timezone": None, "has_time": False}
    m = TIME_RE.search(text or "")
    if m:
        out["time"] = f"{m.group(1).zfill(2)}:{m.group(2)}" + (f":{m.group(3)}" if m.group(3) else "")
        if m.group(4):
            out["time"] += f" {m.group(4).lower()}"
        out["has_time"] = True
    tz = TZ_RE.search(text or "")
    if tz:
        out["timezone"] = tz.group(1).upper()
    else:
        attached = TZ_OFFSET_ATTACHED_RE.search(text or "")
        if attached:
            out["timezone"] = attached.group(1).upper()
    return out


def _mk_part(y, m, d, precision, note=None):
    return {"year": y, "month": m, "day": d, "precision": precision, "note": note}


def extract_parts(clean: str, order: str = "auto", notes: list[str] | None = None):
    """抽取所有日期片段，返回按出现顺序排列的 part 列表。"""
    notes = notes if notes is not None else []
    parts: list[dict] = []
    for m in DATE_RE.finditer(clean):
        g = m.groupdict()
        if g.get("iso_ymd"):
            parts.append(_mk_part(int(g["iso_y"] or g["iso_y2"]),
                                  int(g["iso_m"] or g["iso_m2"]),
                                  int(g["iso_d"] or g["iso_d2"]), "day"))
        elif g.get("ym"):
            parts.append(_mk_part(int(g["ym_y"]), int(g["ym_m"]), None, "month"))
        elif g.get("slashed"):
            a, b, y = int(g["sa"]), int(g["sb"]), int(g["sy"])
            if a > 12:
                mm, dd = b, a
            elif b > 12:
                mm, dd = a, b
            else:
                if order == "eu":
                    mm, dd = b, a
                else:
                    mm, dd = a, b
                    if order == "auto":
                        notes.append(f"顺序歧义：{m.group(0)!r} 按 month/day 解析（可用 --order eu 覆盖）")
            parts.append(_mk_part(y, mm, dd, "day"))
        elif g.get("mdy"):
            name = (g["mname1"] or "").lower().rstrip(".")
            if name in MONTH_NAMES:
                parts.append(_mk_part(int(g["md_y"]) if g["md_y"] else None,
                                      MONTH_NAMES[name], int(g["md_d"]), "day"))
        elif g.get("dmy"):
            name = (g["mname2"] or "").lower().rstrip(".")
            if name in MONTH_NAMES:
                parts.append(_mk_part(int(g["dm_y"]) if g["dm_y"] else None,
                                      MONTH_NAMES[name], int(g["dm_d"]), "day"))
        elif g.get("my"):
            name = (g["mname3"] or "").lower().rstrip(".")
            if name in MONTH_NAMES:
                parts.append(_mk_part(int(g["my_y"]), MONTH_NAMES[name], None, "month"))
        elif g.get("cnd"):
            parts.append(_mk_part(None, int(g["cn_m"]), int(g["cn_d"]), "day"))
        elif g.get("cnm"):
            parts.append(_mk_part(None, int(g["cn_m2"]), None, "month"))
        elif g.get("quarter"):
            y = int(g["q_y"] or g["q_y2"]) if (g["q_y"] or g["q_y2"]) else None
            n = g["q_n"] or g["q_n2"]
            parts.append(_mk_part(y, None, None, "quarter", note=f"季度 Q{n}，无法确定具体日期"))
    return parts


def _iso(y, m, d) -> str | None:
    if not (y and m and d):
        return None
    try:
        return dt.date(y, m, d).isoformat()
    except ValueError:
        return None


def _days_between(iso_date: str | None, today: dt.date) -> int | None:
    if not iso_date:
        return None
    try:
        return (dt.date.fromisoformat(iso_date) - today).days
    except ValueError:
        return None


def parse_date(text: str, default_year: int | None = None,
               order: str = "auto", now: str | None = None) -> dict:
    """主入口：返回归一化结果 dict。

    关键字段：
      deadline_type : fixed | range | rolling | asap | flexible | tbd | unknown
      iso / end     : 起止日期（range 时两者都有）
      days_until_start / days_until_end / urgency_days
      urgency_days  : **紧迫度应以截止端点为基准**（range 取 end，否则取唯一日期）
      expired       : 按 urgency_days 判断
      time / timezone / has_time : 原文时间与时区，仅记录不换算
    """
    notes: list[str] = []
    raw = text
    clean, pre_notes = preprocess(text or "")
    notes.extend(pre_notes)
    result = {
        "raw": raw, "clean": clean,
        "iso": None, "end": None,
        "deadline_type": "unknown", "precision": "unknown",
        "year_unknown": False, "order_ambiguous": False,
        "rolling": False,
        "days_until_start": None, "days_until_end": None, "urgency_days": None,
        "expired": None,
        "year": None, "month": None, "day": None, "end_month": None, "end_day": None,
        "time": None, "timezone": None, "has_time": False,
        "notes": notes,
    }
    if not clean:
        notes.append("空输入")
        return result

    tz_info = extract_time_tz(clean)
    result.update(tz_info)
    if tz_info["has_time"] or tz_info["timezone"]:
        notes.append("原文含时间/时区，已保留原值，未做 UTC 换算")

    hit = _match_status(clean.lower())
    parts = extract_parts(clean, order=order, notes=notes)
    result["order_ambiguous"] = any("顺序歧义" in n for n in notes)

    # 状态词优先，但若同时存在可解析日期（如 "Rolling, opens 2026-09-01"）则保留日期
    if hit and not parts:
        dtype, pat = hit
        result["deadline_type"] = dtype
        result["rolling"] = dtype == "rolling"
        notes.append({
            "rolling": f"滚动招募/招满为止（命中 {pat!r}）：无固定截止日",
            "asap": f"尽快/即时（命中 {pat!r}）：有紧迫性但无具体日期",
            "flexible": f"时间可协商/弹性（命中 {pat!r}）",
            "tbd": f"时间待定/未公布（命中 {pat!r}）：目前无法判断",
        }[dtype])
        return result
    if hit:
        result["deadline_type"] = "range" if len(parts) > 1 else "fixed"
        notes.append(f"同时存在状态词 {hit[1]!r} 与可解析日期，已优先采用日期")
    elif not parts:
        notes.append("无法解析为日期（不猜测）")
        return result

    start = parts[0]
    end = parts[1] if len(parts) > 1 else None

    # 只有月/季度精度时：保留已确认的年月，但不假装知道具体日期
    if end is None and start["precision"] in ("month", "quarter"):
        result["deadline_type"] = "unknown"
        result["precision"] = start["precision"]
        result["year"] = start["year"]
        result["month"] = start["month"]
        if start["precision"] == "quarter":
            notes.append(start["note"] or "仅有季度精度，无法确定具体日期")
        elif start["year"] and start["month"]:
            notes.append(f"仅有月份精度（{start['year']}-{start['month']:02d}），无法确定具体日期")
        elif start["month"]:
            notes.append(f"仅知月份（{start['month']} 月）、未知年份，无法确定日期（不猜测）")
        else:
            notes.append("精度不足以确定日期（不猜测）")
        return result

    result["deadline_type"] = "range" if end is not None else "fixed"

    # 年份传播
    if end is not None:
        if start["year"] is None and end["year"] is not None:
            start["year"] = end["year"] - 1 if (start["month"] and end["month"] and start["month"] > end["month"]) else end["year"]
            notes.append("起始日期年份由区间结束推导，请复核")
        if end["year"] is None and start["year"] is not None:
            end["year"] = start["year"] + 1 if (start["month"] and end["month"] and end["month"] < start["month"]) else start["year"]
            notes.append("结束日期年份由区间起始推导，请复核")

    if start["year"] is None and default_year:
        start["year"] = default_year
        if end is not None and end["year"] is None:
            end["year"] = default_year
        result["year_unknown"] = True
        notes.append(f"原文未写年份，按 --default-year {default_year} 填充（请复核）")
    elif start["year"] is None:
        result["year_unknown"] = True
        notes.append("原文未写年份，未猜测：仅记录月日")

    result["precision"] = start["precision"]
    result["year"] = start["year"]
    result["month"] = start["month"]
    result["day"] = start["day"]
    result["iso"] = _iso(start["year"], start["month"], start["day"])
    if end is not None:
        result["end"] = _iso(end["year"], end["month"], end["day"])
        result["end_month"] = end["month"]
        result["end_day"] = end["day"]
        if result["iso"] and result["end"] and result["end"] < result["iso"]:
            notes.append("结束日期早于起始日期，请复核原文")

    try:
        today = dt.date.fromisoformat(now) if now else dt.date.today()
    except ValueError:
        notes.append(f"无法解析 --now 参数：{now!r}")
        today = dt.date.today()

    result["days_until_start"] = _days_between(result["iso"], today)
    result["days_until_end"] = _days_between(result["end"], today)
    result["urgency_days"] = (result["days_until_end"] if result["days_until_end"] is not None
                              else result["days_until_start"])
    if result["urgency_days"] is not None:
        result["expired"] = result["urgency_days"] < 0
    if end is not None and result["days_until_end"] is not None:
        notes.append("紧迫度以区间截止端点为准（urgency_days = days_until_end）")

    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="多语言日期归一化为 ISO 日期")
    ap.add_argument("text", nargs="?", help="日期字符串；不提供时用 --file")
    ap.add_argument("--file", help="从文件逐行读取日期")
    ap.add_argument("--default-year", type=int, help="原文缺年份时使用的年份（会标记 year_unknown）")
    ap.add_argument("--now", help="参照日期 YYYY-MM-DD，用于 days_until_*；默认今天")
    ap.add_argument("--order", choices=["auto", "us", "eu"], default="auto",
                    help="a/b/y 顺序歧义时的解释（默认 auto→month/day）")
    ap.add_argument("--format", choices=["json", "iso"], default="json")
    ap.add_argument("--jsonl", action="store_true", help="多行输入时输出 JSONL")
    args = ap.parse_args(argv)

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
        out = [parse_date(ln, args.default_year, args.order, args.now) for ln in lines]
        if args.format == "iso":
            print("\n".join(str(o["iso"] or "") for o in out))
        elif args.jsonl:
            for o in out:
                print(json.dumps(o, ensure_ascii=False))
        else:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if not args.text:
        ap.error("需要提供日期字符串或 --file")
    res = parse_date(args.text, args.default_year, args.order, args.now)
    if args.format == "iso":
        print(res["iso"] or "")
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
