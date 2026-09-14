#!/usr/bin/env python3
"""score.py - Opportunity 匹配度与优先级的确定性打分（决策辅助，不是结论）。

三条核心原则：

1. **硬条件优先于模型判断。**
   页面明确写了"仅限博士"，而用户明确是本科 → 结果就是 Ineligible。
   模型 verdict 只能补充语义判断（related field、经验相关性），
   不能推翻 deadline、学历、年级、毕业年份、国籍、学校、GPA、语言成绩这些确定项。
   见 `merge_verdict()`。

2. **画像缺失 ≠ 不满足。**
   Profile 是渐进式构建的，没填语言成绩不等于不会日语。
   信息缺失一律 `Unknown`，只有用户**明确表示**不具备时才向 Ineligible 方向判断。

3. **未知不作 0 分。**
   页面没写技能要求 → 中性分；避免错杀信息不全的真实机会。

Match 与 Priority 分离：`Priority = 0.85*Match + 0.15*Urgency`；
区间类截止日以**截止端点**计算紧迫度（`normalize_date.urgency_days`）。

用法：
  python3 score.py --profile profile.json --opportunities opps.json
  python3 score.py --profile examples/profile.example.json \
                  --opportunities examples/opportunity.batch.example.json --format table
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    EVIDENCE_FIELDS, WEIGHTS, load_records as load_records_common, validate_opportunity,
)
from normalize_date import parse_date  # noqa: E402

VERDICT_ORDER = {
    "Eligible": 0, "Probably Eligible": 1, "Unknown": 2,
    "Probably Ineligible": 3, "Ineligible": 4,
}
VERDICT_SCORE = {"Eligible": 100, "Probably Eligible": 82, "Unknown": 55,
                 "Probably Ineligible": 25, "Ineligible": 0}

TRUST_SCORE = {"A": 100, "B": 85, "C": 60, "D": 35, None: 50}

GOAL_TO_CATEGORY = {
    "internship": ["career"], "fulltime": ["career"], "research": ["research"],
    "competition": ["competition"], "education": ["education"], "language": ["language"],
    "skill": ["skill_development"], "open_source": ["open_source"], "hobby": ["hobby"],
    "funding": ["funding"], "event": ["event"], "project": ["project"],
    "entrepreneurship": ["entrepreneurship"], "networking": ["networking"],
}

PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.35, None: 0.5}

GOAL_TO_VALUE_DIM = {
    "internship": ["career", "portfolio"], "fulltime": ["career", "financial"],
    "research": ["research", "skill"], "competition": ["portfolio", "skill"],
    "education": ["research", "career"], "language": ["skill", "career"],
    "skill": ["skill"], "open_source": ["skill", "portfolio", "networking"],
    "hobby": ["interest"], "funding": ["financial"],
    "event": ["networking", "skill"], "project": ["portfolio", "skill"],
    "entrepreneurship": ["career", "networking"], "networking": ["networking"],
}

VALUE_LEVEL = {"high": 1.0, "medium": 0.6, "low": 0.3, "unknown": 0.5, None: 0.5}

INTEREST_ALIASES = {
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "llm", "生成"],
    "agent": ["agent", "agents", "multi-agent", "llm agent", "autonomous"],
    "iot": ["iot", "internet of things", "sensor network", "smart device", "スマート"],
    "embedded": ["embedded", "firmware", "mcu", "microcontroller", "rtos", "esp32", "stm32", "組み込み"],
    "robotics": ["robotics", "robot", "ros", "mechatronics", "ロボット"],
    "drone": ["drone", "uav", "quadcopter", "无人机", "ドローン"],
    "photography": ["photography", "camera", "photo", "写真", "摄影"],
    "game": ["game", "gamedev", "unity", "unreal", "esports", "ゲーム"],
    "design": ["design", "ui", "ux", "graphic", "industrial design", "デザイン"],
    "automotive": ["automotive", "vehicle", "adas", "automobile", "モビリティ"],
    "aviation": ["aviation", "aerospace", "space", "航空", "宇宙"],
    "maker": ["maker", "3d printing", "diy", "fabrication", "ものづくり"],
    "energy": ["energy", "climate", "sustainability", "renewable"],
    "data": ["data", "analytics", "statistics", "visualization"],
    "security": ["security", "ctf", "cybersecurity", "penetration"],
}

#: 出现频率过高、单独命中不能说明技能满足的通用 token
GENERIC_SKILL_TOKENS = frozenset({
    "data", "engineering", "analysis", "analytics", "development", "programming",
    "software", "hardware", "system", "systems", "research", "design", "science",
    "technology", "technical", "computer", "management", "learning", "machine",
    "tools", "tool", "framework", "frameworks", "platform", "application",
    "applications", "related", "field", "knowledge", "experience", "background",
    "ability", "communication", "teamwork", "basic", "advanced", "fundamental",
    "fundamentals", "general", "skill", "skills", "concept", "concepts",
})

#: 明确表示"用户不具备"的语言水平标记（只有这些才允许判不满足）
#: 注意：判断时必须排除 None —— `str(None).lower()` 恰好等于 "none"，会造成
#: "未填写语言成绩"被误判为"明确不会该语言"。
LANGUAGE_NONE_MARKERS = ("none", "no", "cannot", "not-available", "不会", "无", "未学", "未修", "不懂")


def is_explicit_none(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value is False
    s = str(value).strip().lower()
    return bool(s) and s in LANGUAGE_NONE_MARKERS

#: 页面写明"不限制国籍/向所有人开放"的信号
NATIONALITY_OPEN_SIGNALS = (
    "国籍不問", "国籍不问", "国籍不限", "無国籍要件", "no nationality requirement",
    "open to all nationalities", "any nationality", "regardless of nationality",
    "open to students worldwide", "international students welcome", "all applicants",
    "不限国籍", "面向全球学生",
)

#: 页面写明"仅限某国国籍/居民"的信号
NATIONALITY_RESTRICT_SIGNALS = (
    "citizens only", "nationals only", "must be a citizen", "citizenship required",
    "permanent resident", "must reside in", "work authorization", "sponsorship not provided",
    "no sponsorship", "legally authorized to work", "国内在住", "日本国籍", "国籍要件",
    "仅限中国籍", "限本校学生", "本国籍",
)

#: 国籍/地区 -> 可识别的措辞（用于把"仅限 X 国籍"与画像国籍做显式比对）
NATIONALITY_DEMONYMS = {
    "japanese": ("japan", "japanese", "日本"),
    "chinese": ("china", "chinese", "中国"),
    "american": ("united states", "usa", "us citizen", "american", "美国"),
    "korean": ("korea", "korean", "韓国", "한국", "韩国"),
    "indian": ("india", "indian", "インド", "印度"),
    "german": ("germany", "german", "ドイツ", "德国"),
    "french": ("france", "french", "フランス", "法国"),
    "british": ("united kingdom", "uk ", "britain", "british", "英国"),
    "australian": ("australia", "australian", "オーストラリア", "澳大利亚"),
    "canadian": ("canada", "canadian", "カナダ", "加拿大"),
    "singaporean": ("singapore", "singaporean", "シンガポール", "新加坡"),
}


def demonym_of(text) -> set[str]:
    low = f" {str(text or '').lower()} "
    out = set()
    for key, aliases in NATIONALITY_DEMONYMS.items():
        if any(a in low for a in aliases):
            out.add(key)
    return out

#: 排除国际申请人的信号
NO_SPONSORSHIP_SIGNALS = ("sponsorship not provided", "no sponsorship", "without sponsorship",
                          "must be legally authorized to work", "work authorization required")


# ------------------------------------------------------------------ 小工具

def norm(s):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u30ff+#.]+", " ", str(s or "").lower()).strip()


def as_list(v):
    if v in (None, "", [], {}):
        return []
    return v if isinstance(v, list) else [v]


def text_of(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return " ".join(text_of(x) for x in v)
    if isinstance(v, dict):
        return " ".join(str(x) for x in v.values() if x is not None)
    return str(v)


def match_any(text: str, needles) -> str | None:
    low = (text or "").lower()
    for n in needles:
        if n.lower() in low:
            return n
    return None


# ------------------------------------------------------------------ 技能匹配

def skill_tokens(text) -> list[str]:
    """技能名 → token 列表。保留 + / # / . 这些对技能名有意义的字符（C++ ≠ C）。"""
    return [t for t in norm(text).split() if t]


def tok_matches(need: str, have: str) -> bool:
    if need == have:
        return True
    if need in GENERIC_SKILL_TOKENS or have in GENERIC_SKILL_TOKENS:
        return False                      # 通用词必须精确相等
    if len(need) >= 4 and (have.startswith(need) or need.startswith(have)):
        return True                       # python ↔ python3、esp32 ↔ esp32-s3
    return False


def skill_hit(required, profile_skills) -> bool:
    """判断某个要求技能是否被画像中的技能覆盖。

    刻意避免"任意 token 交集"式误判：`data engineering` 不应被 `data analysis` 命中
    （仅有通用词 data 重合）。只在以下情况算命中：
      1. 归一化后完全相等
      2. required 的**全部非通用 token** 都能在某个画像技能里找到对应 token
      3. 全是通用词时（如 "data engineering"），要求完整 token 集合都被包含
    """
    req_tokens = skill_tokens(required)
    if not req_tokens:
        return False
    for ps in profile_skills:
        p_tokens = skill_tokens(ps)
        if not p_tokens:
            continue
        if req_tokens == p_tokens:
            return True
        sig = [t for t in req_tokens if t not in GENERIC_SKILL_TOKENS and len(t) >= 2]
        if sig and all(any(tok_matches(t, h) for h in p_tokens) for t in sig):
            return True
        if not sig and all(any(tok_matches(t, h) for h in p_tokens) for t in req_tokens):
            return True
    return False


# ------------------------------------------------------------------ 硬条件：日期 / 学历 / 年级 / 毕业

def deadline_days(date_str, today: dt.date):
    """返回 (urgency_days, deadline_type, expired)。区间以截止端点为准。"""
    if date_str in (None, ""):
        return None, "unknown", None
    res = parse_date(str(date_str), now=today.isoformat())
    return res.get("urgency_days"), res.get("deadline_type"), res.get("expired")


def parse_ym_pairs(text) -> list[tuple[int, int | None]]:
    """从文本中抽取 (年, 月) 对；只有年份时月为 None。"""
    s = str(text or "")
    out: list[tuple[int, int | None]] = []
    for m in re.finditer(r"(?<!\d)(\d{4})\s*[-/.年]\s*(\d{1,2})\s*月?", s):
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            out.append((y, mo))
        else:
            out.append((y, None))
    if not out:
        for m in re.finditer(r"(?i)\b" + r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
                             + r"[a-z]*\.?\s*,?\s*(\d{4})", s):
            mon = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                   "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}[m.group(1).lower()]
            out.append((int(m.group(2)), mon))
    if not out:
        for m in re.finditer(r"(?<!\d)((?:19|20)\d{2})(?!\d)", s):
            out.append((int(m.group(1)), None))
    return out


def parse_grad_window(text):
    """把毕业时间要求解析成可比较的月份区间 (start_ym, end_ym, year_only)。

    start_ym/end_ym 形如 (2027, 9) / (2028, 6)；(year, None) 表示只有年份精度。
    无法解析时返回 None。
    """
    pairs = parse_ym_pairs(text)
    if not pairs:
        return None
    if len(pairs) == 1:
        y, m = pairs[0]
        if m is None:
            return (y, 1), (y, 12), True
        return (y, m), (y, m), False
    y0, m0 = pairs[0]
    y1, m1 = pairs[-1]
    a = (y0, m0 if m0 is not None else 1)
    b = (y1, m1 if m1 is not None else 12)
    if a > b:
        a, b = b, a
    return a, b, (m0 is None and m1 is None)


def ym_of_graduation(value):
    """用户毕业时间 → (year, month|None)。"""
    pairs = parse_ym_pairs(value)
    if not pairs:
        return None
    return pairs[0]


def in_grad_window(user_ym, window) -> tuple[bool | None, str]:
    if not user_ym or not window:
        return None, "无法比较"
    start, end, year_only = window
    uy, um = user_ym
    if year_only or um is None:
        lo, hi = start[0], end[0]
        return (lo <= uy <= hi), f"按年份比较（要求 {lo}-{hi}）"
    lo = (start[0], start[1] if start[1] else 1)
    hi = (end[0], end[1] if end[1] else 12)
    return (lo <= (uy, um) <= hi), f"按月比较（要求 {lo[0]}-{lo[1]:02d} ~ {hi[0]}-{hi[1]:02d}）"


# ------------------------------------------------------------------ 硬条件：GPA / 语言 / 国籍 / 学校

def parse_gpa(value):
    """解析 GPA 表达 → (数值, 满分) ；无法解析返回 None。不做跨体系换算。"""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value), None
    s = str(value).strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), None
    return None


def gpa_check(required, user_value) -> tuple[str, str]:
    """返回 (结果, 说明)。结果 ∈ ok / fail / unknown_missing / unknown_incomparable。"""
    req = parse_gpa(required)
    usr = parse_gpa(user_value)
    if req is None:
        return "unknown_incomparable", "页面 GPA 要求无法解析"
    if usr is None:
        return "unknown_missing", "画像未提供 GPA，无法确认是否达标"
    (rv, rs), (uv, us) = req, usr
    if rs is None or us is None:
        return "unknown_incomparable", "评分体系不完整，无法比较（不做换算）"
    if abs(rs - us) > 1e-6:
        return "unknown_incomparable", f"评分体系不同（{uv}/{us} vs {rv}/{rs}），不做换算"
    if uv + 1e-6 >= rv:
        return "ok", f"GPA {uv}/{us} 满足要求 {rv}/{rs}"
    return "fail", f"GPA {uv}/{us} 低于要求 {rv}/{rs}"


def level_value(tokens) -> float | None:
    """把语言等级转成可比较数值：JLPT N1..N5 → 5..1；数字分数原样。"""
    for t in tokens:
        m = re.fullmatch(r"n([1-5])", t)
        if m:
            return 6 - int(m.group(1))
    for t in tokens:
        m = re.fullmatch(r"\d+(?:\.\d+)?", t)
        if m:
            return float(t)
    return None


def language_check(opp, profile) -> tuple[str, str]:
    """返回 (结果, 说明)。结果 ∈ ok / unknown_missing / unknown_low_info / fail。"""
    entries = [e for e in as_list(profile.get("languages")) if isinstance(e, dict)]
    prof_tokens = {id(e): skill_tokens(f"{e.get('language','')} {e.get('exam','')} "
                                       f"{e.get('score','')} {e.get('level','')}") for e in entries}
    results = []
    for item in as_list(opp.get("language_requirement")):
        if isinstance(item, dict):
            lang = norm(item.get("language"))
            exam = norm(item.get("exam"))
            need = skill_tokens(f"{exam} {item.get('min_level','')}")
            raw_level = str(item.get("min_level") or "")
        else:
            lang, exam, need, raw_level = norm(item), "", skill_tokens(item), ""

        cands = [e for e in entries
                 if lang and any(lang in t for t in prof_tokens[id(e)])]
        if not cands:
            results.append(("unknown_missing",
                            f"页面要求{f' {lang}' if lang else '语言能力'}，"
                            "画像中未记录该语言 → 无法判断（缺失不等于不会）"))
            continue

        none_marked = [e for e in cands
                       if is_explicit_none(e.get("level")) or is_explicit_none(e.get("score"))]
        if none_marked:
            results.append(("fail", f"画像明确标注不具备该语言（{lang}），而页面有硬性语言要求"))
            continue

        if not (exam or need):
            results.append(("ok", f"页面只要求 {lang}，画像已有该语言记录"))
            continue

        hit = False
        for e in cands:
            toks = prof_tokens[id(e)]
            if exam and exam not in toks and not any(tok_matches(exam, t) for t in toks):
                continue
            req_v = level_value(need) if need else None
            have_v = level_value(toks)
            if req_v is None:
                hit = True
                break
            if have_v is None:
                continue
            if have_v + 1e-6 >= req_v:
                hit = True
                break
        if hit:
            results.append(("ok", f"语言要求（{exam or ''} {raw_level}）与画像记录相符"))
        else:
            has_score = any(level_value(prof_tokens[id(e)]) is not None for e in cands)
            if has_score:
                results.append(("fail", f"页面要求 {exam or ''} {raw_level}，画像中的成绩未达该等级"))
            else:
                results.append(("unknown_low_info",
                                f"页面要求 {exam or ''} {raw_level}，画像有该语言但未记录成绩/等级 → "
                                "信息不足（不是不满足）"))
    if not results:
        return "ok", ""
    for kind, msg in results:
        if kind == "fail":
            return "fail", msg
    for kind, msg in results:
        if kind.startswith("unknown"):
            return kind, msg
    return "ok", results[0][1]


def nationality_check(opp, profile) -> tuple[str, str]:
    req_text = text_of(opp.get("nationality_requirement"))
    if not req_text:
        return "none", ""
    if match_any(req_text, NATIONALITY_OPEN_SIGNALS):
        return "ok", "页面明确不限制国籍"
    user_nat = (profile.get("nationality")
                or (profile.get("education") or {}).get("nationality") or "")
    visa = (profile.get("constraints") or {}).get("visa") or ""
    no_sponsor = match_any(req_text, NO_SPONSORSHIP_SIGNALS)
    if no_sponsor and "need_sponsor" in str(visa).lower():
        return "fail", "页面明确不提供工作签证赞助，而画像标注需要赞助"
    if not user_nat and not visa:
        return "unknown_missing", (
            f"页面有国籍/工作许可限制（{req_text[:40]}），画像未提供国籍与签证信息 → 无法判断")

    required_demo = demonym_of(req_text)
    user_demo = demonym_of(user_nat) if user_nat else set()
    if required_demo and user_demo:
        if required_demo & user_demo:
            return "ok", f"画像国籍与页面要求相符（{user_nat}）"
        return "fail", (f"页面限定 {'/'.join(sorted(required_demo))} 国籍，"
                        f"画像为 {user_nat} → 明确不符")
    if required_demo and not user_demo:
        return "unknown_low_info", "页面写有国籍限制，但画像国籍表述无法与之比对"
    restricted = match_any(req_text, NATIONALITY_RESTRICT_SIGNALS)
    if restricted:
        return "unknown_low_info", "页面含限制性措辞，但未写明具体国籍，信息不足以确认是否影响你"
    if user_nat or visa:
        return "ok", "页面未写明国籍限制"
    return "none", ""


def school_check(opp, profile) -> tuple[str, str]:
    req = text_of(opp.get("school_requirement"))
    if not req:
        return "none", ""
    school = (profile.get("education") or {}).get("school")
    if not school:
        return "unknown_missing", f"页面有学校限制（{req[:40]}），画像未提供学校信息"
    if norm(school) and norm(school) in norm(req):
        return "ok", f"画像学校与页面要求相符（{school}）"
    return "unknown_low_info", "页面写有学校限制，但无法确认你的学校是否在其范围内"


# ------------------------------------------------------------------ 资格判定

def _sev(verdict: str) -> int:
    return VERDICT_ORDER.get(verdict, 2)


def merge_verdict(hard: str | None, hard_kind: str, agent: str | None) -> tuple[str, str]:
    """合并硬条件结论与模型 verdict。

    hard_kind ∈ hard_conflict | hard_ok | missing_profile | missing_source |
                incomparable | none

    * 硬冲突（hard_conflict）→ 模型不得推翻（可降不可升）
    * 硬条件满足（hard_ok）→ 模型只能更保守，不能更乐观
    * missing_profile → 模型可判断（它可能在对话里拿到了画像之外的信息）
    * missing_source / incomparable → 模型最多给到 Probably Eligible
    """
    if hard is None:
        return (agent or "Unknown"), ("agent" if agent else "none")
    if hard_kind == "hard_conflict" and _sev(hard) >= 3:
        return hard, "hard_constraint"
    if hard_kind == "missing_profile":
        return (agent or hard), ("agent" if agent else "hard_constraint")
    if hard_kind in ("missing_source", "incomparable"):
        # 页面信息不足或口径不可比：模型可以补上它读到的额外信息，
        # 但不得给出比"Probably Eligible"更确定的结论。
        if agent and _sev(agent) < _sev("Probably Eligible"):
            return "Probably Eligible", "agent_clamped"
        return (agent or hard), ("agent" if agent else "hard_constraint")
    # hard_ok / none：模型可以更保守，但不能更乐观
    if agent and _sev(agent) > _sev(hard):
        return agent, "agent_downgrade"
    return hard, "hard_constraint"


def eligibility_component(opp, profile, today):
    """对**所有**有数据的硬条件逐项检查，取最严重的结论作为最终硬判定。

    刻意不做"第一个满足就返回"的短路：学历满足但语言成绩信息缺失时，
    结论应当是 Unknown 而不是 Eligible——只有全部硬条件都确认满足才算 Eligible。

    返回 (score, verdict, reasons[], needs_llm, verdict_source, kind)。
    """
    reasons: list[str] = []
    today = today or dt.date.today()
    ed = profile.get("education") or {}
    degree = ed.get("degree")
    if isinstance(degree, list):
        degree = degree[0] if degree else None
    agent_verdict = (opp.get("eligibility") or {}).get("verdict")
    needs_llm = False

    found: list[tuple[str, str, str]] = []      # (verdict, kind, reason)

    def add(verdict, kind, reason):
        found.append((verdict, kind, reason))
        reasons.append(reason)

    # 1. 时间窗口（最硬的确定性条件）
    ug, dtype, expired = deadline_days(opp.get("deadline"), today)
    if expired:
        add("Ineligible", "hard_conflict", f"报名截止日已过（{opp.get('deadline')}）")
    elif dtype == "rolling":
        reasons.append("滚动招募，无固定截止日")

    # 2. 学历
    levels = [str(x) for x in as_list(opp.get("education_level"))]
    if levels and "any" not in levels:
        if not degree:
            add("Unknown", "missing_profile", f"页面限定学历 {levels}，画像未提供学历 → 无法判断")
        elif degree not in levels:
            add("Probably Ineligible", "hard_conflict", f"页面限定学历 {levels}，画像学历为 {degree}")
        else:
            add("Eligible", "hard_ok", f"学历相符（{degree} 在 {levels} 内）")

    # 3. 学年
    years = [y for y in as_list(opp.get("student_year")) if str(y).isdigit()]
    cy = ed.get("current_year")
    if years:
        if not cy:
            add("Unknown", "missing_profile", f"页面限定学年 {years}，画像未提供年级 → 无法判断")
        elif int(cy) not in [int(y) for y in years]:
            add("Probably Ineligible", "hard_conflict", f"页面限定学年 {years}，画像为 {cy} 年级")
        else:
            add("Eligible", "hard_ok", f"学年相符（{cy} 在 {years} 内）")

    # 4. 毕业时间窗口（按月比较）
    if opp.get("graduation_window"):
        window = parse_grad_window(opp["graduation_window"])
        user_ym = ym_of_graduation(ed.get("expected_graduation"))
        if window and not user_ym:
            add("Unknown", "missing_profile",
                f"页面要求毕业时间 {opp['graduation_window']}，画像未提供毕业时间 → 无法判断")
        elif window and user_ym:
            ok, how = in_grad_window(user_ym, window)
            if ok is True:
                add("Eligible", "hard_ok", f"毕业时间落在要求窗口内（{how}）")
            elif ok is False:
                add("Probably Ineligible", "hard_conflict", f"毕业时间不在要求窗口内（{how}）")
            else:
                add("Unknown", "incomparable", "毕业时间无法比较（解析失败）")
        else:
            add("Unknown", "incomparable", f"页面毕业时间要求无法解析：{opp['graduation_window']!r}")

    # 5. 国籍 / 工作许可
    nat_state, nat_msg = nationality_check(opp, profile)
    if nat_msg:
        if nat_state == "fail":
            add("Probably Ineligible", "hard_conflict", nat_msg)
        elif nat_state == "unknown_missing":
            add("Unknown", "missing_profile", nat_msg)
        elif nat_state == "unknown_low_info":
            add("Unknown", "incomparable", nat_msg)
        elif nat_state == "ok":
            add("Eligible", "hard_ok", nat_msg)

    # 6. 学校限制
    sch_state, sch_msg = school_check(opp, profile)
    if sch_msg:
        if sch_state == "unknown_missing":
            add("Unknown", "missing_profile", sch_msg)
        elif sch_state == "unknown_low_info":
            add("Unknown", "incomparable", sch_msg)
        elif sch_state == "ok":
            add("Eligible", "hard_ok", sch_msg)

    # 7. GPA（同体系才比较）
    if opp.get("GPA_requirement"):
        state, msg = gpa_check(opp["GPA_requirement"], ed.get("GPA"))
        if state == "fail":
            add("Probably Ineligible", "hard_conflict", msg)
        elif state.startswith("unknown"):
            add("Unknown", "missing_profile" if state == "unknown_missing" else "incomparable", msg)
        else:
            add("Eligible", "hard_ok", msg)

    # 8. 语言
    if opp.get("language_requirement"):
        state, msg = language_check(opp, profile)
        if state == "fail":
            add("Probably Ineligible", "hard_conflict", msg)
        elif state.startswith("unknown"):
            add("Unknown", "missing_profile" if state == "unknown_missing" else "incomparable", msg)
        else:
            add("Eligible", "hard_ok", msg)

    # 9. 专业（语义条件：不作为硬冲突，只标记需要人工判断）
    if opp.get("major_requirement"):
        mr = text_of(opp.get("major_requirement"))
        major = norm(ed.get("major"))
        if not major:
            add("Unknown", "missing_profile", "页面有专业要求，但画像未提供专业 → 无法判断")
        else:
            tokens = [t for t in major.split() if len(t) > 2]
            if tokens and any(t in norm(mr) for t in tokens):
                reasons.append("专业要求与画像专业字面相关（最终以组织方定义为准）")
            else:
                needs_llm = True
                reasons.append("专业要求需语义判断（related field 类表述），硬条件不冲突")

    if not found:
        hard, kind = "Probably Eligible", "none"
        reasons.append("页面未写明硬性资格范围，也没有可判定的冲突项")
    else:
        hard, kind, _ = max(found, key=lambda x: _sev(x[0]))

    final, source = merge_verdict(hard, kind, agent_verdict)
    if agent_verdict and _sev(agent_verdict) < _sev(hard) and kind == "hard_conflict":
        reasons.append(f"注意：模型判定为 {agent_verdict}，但被硬性条件覆盖为 {hard}")
    return VERDICT_SCORE.get(final, 55), final, reasons, needs_llm, source, kind


# ------------------------------------------------------------------ 其余分项

def goal_component(opp, profile):
    goals = as_list(profile.get("goals"))
    if not goals:
        return 60.0, "画像未提供目标，按中性处理"
    cats = {opp.get("primary_category")} | set(as_list(opp.get("secondary_categories")))
    best, note = 0.0, "与声明的目标不重合"
    for g in goals:
        if not isinstance(g, dict):
            continue
        w = PRIORITY_WEIGHT.get(g.get("priority"), 0.5)
        for c in GOAL_TO_CATEGORY.get(g.get("type"), []):
            if opp.get("primary_category") == c:
                if w > best:
                    best, note = w, f"命中目标 {g.get('type')}（priority={g.get('priority')}）"
            elif c in cats:
                if w * 0.8 > best:
                    best, note = w * 0.8, f"作为次要类别命中目标 {g.get('type')}"
    return (100.0 * best if best else 15.0), note


def skill_component(opp, profile):
    ps = [s.get("name") if isinstance(s, dict) else s for s in as_list(profile.get("skills"))]
    req = as_list(opp.get("skills_required"))
    pref = as_list(opp.get("skills_preferred"))
    if not ps:
        return 50.0, "画像未提供技能，按中性处理"
    if req:
        hit = [r for r in req if skill_hit(r, ps)]
        rc = len(hit) / len(req)
        pc = (sum(1 for p in pref if skill_hit(p, ps)) / len(pref)) if pref else 0.0
        return 100 * (0.75 * rc + 0.25 * pc), f"硬性技能覆盖 {len(hit)}/{len(req)}" + (
            f"（命中：{', '.join(map(str, hit))}）" if hit else "")
    if pref:
        pc = sum(1 for p in pref if skill_hit(p, ps)) / len(pref)
        return 100 * (0.35 + 0.5 * pc), f"页面只写了偏好技能，覆盖 {pc:.0%}"
    return 50.0, "页面未写明技能要求"


def interest_component(opp, profile):
    interests = as_list(profile.get("interests"))
    if not interests:
        return 55.0, "画像未提供兴趣"
    text = " ".join([norm(str(opp.get("title"))), norm(str(opp.get("summary"))),
                     " ".join(norm(t) for t in as_list(opp.get("tags"))),
                     norm(str(opp.get("primary_category"))),
                     " ".join(norm(x) for x in as_list(opp.get("major_requirement"))),
                     " ".join(norm(x) for x in as_list(opp.get("skills_preferred"))),
                     " ".join(norm(x) for x in as_list(opp.get("skills_required")))])
    matched = []
    for it in interests:
        key = norm(it)
        aliases = INTEREST_ALIASES.get(key, [key])
        if any(norm(a) and norm(a) in text for a in aliases):
            matched.append(it)
    if not matched:
        return 20.0, "未发现与画像兴趣的重合信号"
    ratio = len(matched) / len(interests)
    return 100 * (0.25 + 0.75 * min(1.0, ratio * 2)), f"兴趣命中：{', '.join(matched)}"


def location_component(opp, profile):
    c = profile.get("constraints") or {}
    countries = [norm(x) for x in as_list(c.get("preferred_country"))]
    cities = [norm(x) for x in as_list(c.get("preferred_city"))]
    remote_pref = c.get("remote")
    relocation = c.get("relocation")
    if not countries and not cities and remote_pref is None:
        return 60.0, "画像未提供地区约束"
    oc, oci = norm(opp.get("country")), norm(opp.get("city"))
    if cities and oci and any(x and (x in oci or oci in x) for x in cities):
        return 100.0, f"城市匹配：{opp.get('city')}"
    if countries and oc and any(x and (x in oc or oc in x) for x in countries):
        return 95.0, f"国家/地区匹配：{opp.get('country')}"
    if opp.get("remote") and remote_pref:
        return 95.0, "远程，符合你的 remote 偏好"
    if opp.get("remote") and remote_pref is None:
        return 85.0, "远程机会（画像未表态，按可接受处理）"
    if oc and countries:
        return (60.0 if relocation else 25.0), f"地区为 {opp.get('country')}，不在偏好列表中"
    if not oc and not opp.get("remote"):
        return 45.0, "页面未写明地点，无法确认地区匹配"
    return 55.0, "地区信息不足"


def value_component(opp, profile):
    v = opp.get("value") or {}
    if not v:
        return 55.0, "尚未评估价值维度"
    goals = as_list(profile.get("goals"))
    dims = []
    for g in sorted([g for g in goals if isinstance(g, dict)],
                    key=lambda g: -PRIORITY_WEIGHT.get(g.get("priority"), 0.5)):
        dims = GOAL_TO_VALUE_DIM.get(g.get("type"), [])
        if dims:
            break
    if not dims:
        dims = list(v.keys())
    vals = [VALUE_LEVEL.get(str(v.get(d, "")).lower(), 0.5) for d in dims if d in v]
    if not vals:
        return 55.0, "价值评估与目标维度无交集"
    return 100 * sum(vals) / len(vals), f"按目标相关维度（{', '.join(dims)}）评分"


def trust_component(opp):
    t = opp.get("trust_tier")
    score = TRUST_SCORE.get(t, 50)
    vs = opp.get("verification_status")
    note = f"来源 Tier {t}" if t else "来源层级未知"
    if vs == "conflicting":
        score -= 5
        note += "，官方与第三方信息冲突（已以官方为准）"
    elif vs == "unverified":
        score -= 10
        note += "，未获官方确认"
    elif vs == "expired":
        score -= 30
        note += "，官方页面显示已结束"
    elif vs == "verified_official":
        note += "，3 项关键事实已官方确认"
    return max(0, score), note


def novelty_component(opp, seen_index):
    if seen_index is None:
        return 80.0, "无本地状态，按新机会处理"
    st = opp.get("seen_status") or seen_index.get(opp.get("id"))
    if st == "repeat":
        return 40.0, "上次已推荐且无变化"
    if st == "changed":
        return 90.0, "已见过但有关键字段变化"
    if st == "new" or st is None:
        return 100.0, "新发现"
    return 80.0, "状态未知"


def urgency_score(days):
    if days is None:
        return None
    if days < 0:
        return 0.0
    if days <= 3:
        return 100.0
    if days <= 7:
        return 92.0
    if days <= 14:
        return 82.0
    if days <= 30:
        return 68.0
    if days <= 60:
        return 50.0
    if days <= 120:
        return 35.0
    return 20.0


def band(score):
    return "High" if score >= 80 else ("Medium" if score >= 60 else "Low")


# ------------------------------------------------------------------ 主流程

def parse_hours(text):
    if text in (None, ""):
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"(\d{1,3})\s*(?:h\b|hr|hrs|hours?|時間|小时|時間/週|h/週)", str(text), re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{1,3})", str(text))
    return float(m.group(1)) if m else None


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def evidence_gaps(opp) -> list[str]:
    """按 evidence 结构指出关键字段的证据缺口（没有 evidence 时退回 notes 提示）。"""
    ev = opp.get("evidence") or {}
    gaps = []
    for f in EVIDENCE_FIELDS:
        entry = ev.get(f)
        if not isinstance(entry, dict):
            continue
        st = entry.get("status")
        if st in ("inferred", "unknown"):
            gaps.append(f"{f}: {st}" + (f"（{entry.get('note')}）" if entry.get("note") else ""))
        elif st == "explicit" and not entry.get("source_url"):
            gaps.append(f"{f}: explicit 但缺 source_url")
    return gaps


def score_all(profile, opps, seen_index=None, today=None, strict=False):
    today = today or dt.date.today()
    results, excluded, contract_issues = [], [], []

    for opp in opps:
        if not isinstance(opp, dict):
            continue
        issues = validate_opportunity(opp)
        if issues:
            contract_issues.append({"id": opp.get("id"), "errors": issues})
            if strict:
                continue

        el_score, verdict, el_reasons, needs_llm, v_source, v_kind = eligibility_component(
            opp, profile, today)
        goal_fit, goal_note = goal_component(opp, profile)
        skill_fit, skill_note = skill_component(opp, profile)
        interest_fit, interest_note = interest_component(opp, profile)
        location_fit, location_note = location_component(opp, profile)
        value_fit, value_note = value_component(opp, profile)
        trust, trust_note = trust_component(opp)
        novelty, novelty_note = novelty_component(opp, seen_index)
        comp = {
            "eligibility": el_score, "goal_fit": goal_fit, "skill_fit": skill_fit,
            "interest_fit": interest_fit, "location_fit": location_fit,
            "value_fit": value_fit, "trust": trust, "novelty": novelty,
        }
        match = round(sum(WEIGHTS[k] * v for k, v in comp.items()))

        ug, dtype, expired = deadline_days(opp.get("deadline"), today)
        us = urgency_score(ug)
        flags, warnings = [], []

        if verdict == "Ineligible":
            excluded.append({"id": opp.get("id"), "title": opp.get("title"),
                             "reason": "Ineligible: " + "；".join(el_reasons)})
            continue
        if expired:
            excluded.append({"id": opp.get("id"), "title": opp.get("title"),
                             "reason": f"deadline 已过（{opp.get('deadline')}）"})
            continue

        if ug is not None and ug <= 14:
            flags.append("urgent")
        if dtype == "rolling":
            flags.append("rolling")
        if dtype in ("tbd", "unknown") and opp.get("deadline") in (None, ""):
            flags.append("no_deadline")
        hours = parse_hours(opp.get("time_commitment"))
        limit = parse_hours((profile.get("constraints") or {}).get("weekly_time"))
        if hours and limit and hours > limit:
            flags.append("heavy_load")
            warnings.append(f"时间投入（{opp.get('time_commitment')}）超出你的每周上限 {limit:g}h")
        if opp.get("verification_status") == "unverified":
            flags.append("unverified")
            warnings.append("未找到官方确认来源")
        if needs_llm:
            flags.append("needs_semantic_check")
        if not opp.get("language_requirement"):
            flags.append("language_unspecified")
            warnings.append("页面未写明语言要求")
        for g in evidence_gaps(opp):
            warnings.append(f"证据缺口 {g}")

        priority = round(0.85 * match + 0.15 * us) if us is not None else match
        if "heavy_load" in flags:
            priority -= 5
        if "unverified" in flags:
            priority -= 8

        results.append({
            "id": opp.get("id"),
            "title": opp.get("title"),
            "organization": opp.get("organization"),
            "primary_category": opp.get("primary_category"),
            "layer": opp.get("layer"),
            "components": comp,
            "eligibility_verdict": verdict,
            "eligibility_source": v_source,
            "eligibility_kind": v_kind,
            "eligibility_reasons": el_reasons,
            "match_score": match,
            "match_band": band(match),
            "urgency": us,
            "days_remaining": ug,
            "deadline_type": dtype,
            "priority_score": priority,
            "priority_band": band(priority),
            "flags": flags,
            "warnings": warnings,
            "reasons": {
                "goal_fit": goal_note,
                "skill_fit": skill_note,
                "interest_fit": interest_note,
                "location_fit": location_note,
                "value_fit": value_note,
                "trust": trust_note,
                "novelty": novelty_note,
            },
        })

    results.sort(key=lambda r: (-r["priority_score"], -r["match_score"], str(r["id"])))

    cats, layers = {}, {}
    for r in results:
        cats[r["primary_category"]] = cats.get(r["primary_category"], 0) + 1
        if r["layer"]:
            layers[r["layer"]] = layers.get(r["layer"], 0) + 1
    diversity = {
        "categories": cats,
        "layers": layers,
        "checks": {
            "categories_ge_3": len(cats) >= 3,
            "has_adjacent": layers.get("adjacent", 0) >= 1,
            "has_explore": layers.get("explore", 0) >= 1,
            "single_category_share_ok": (max(cats.values()) / len(results) <= 0.5) if results else None,
        },
        "note": "这是覆盖面自检（参考值），不是硬性配额：Adjacent/Explore 只在达到质量与"
                "验证门槛时纳入，绝不为凑配额塞入弱机会。见 references/ranking.md §3。",
    }

    return {
        "params": {"weights": WEIGHTS,
                   "priority_formula": "0.85*match + 0.15*urgency（区间以截止端点计）",
                   "today": today.isoformat(),
                   "disclaimer": "确定性打分，仅作排序辅助；展示时用档次 + 理由，不要展示裸分数当结论"},
        "scored": len(results),
        "results": results,
        "excluded": excluded,
        "contract_issues": contract_issues,
        "diversity": diversity,
    }


def render_table(res):
    out = ["| # | 机会 | 类别 | Match | 紧迫 | Priority | 档 | 资格 | 判定来源 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(res["results"], 1):
        out.append(f"| {i} | {r['title']} | {r['primary_category']} | {r['match_score']} "
                   f"| {'' if r['urgency'] is None else int(r['urgency'])} | {r['priority_score']} "
                   f"| {r['priority_band']} | {r['eligibility_verdict']} | {r['eligibility_source']} |")
    if res["excluded"]:
        out += ["", "已排除："] + [f"- {e['id']}: {e['reason']}" for e in res["excluded"]]
    if res.get("contract_issues"):
        out += ["", "contract 问题："] + [f"- {c['id']}: {c['errors'][0]}" for c in res["contract_issues"]]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Opportunity 匹配度/优先级确定性打分（决策辅助）")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--opportunities", required=True)
    ap.add_argument("--seen", help="seen.json，用于 novelty 与重复处理")
    ap.add_argument("--today", help="参照日期 YYYY-MM-DD，默认今天")
    ap.add_argument("--output")
    ap.add_argument("--format", choices=["json", "table"], default="json")
    ap.add_argument("--strict", action="store_true", help="出现 contract 问题时跳过该记录")
    args = ap.parse_args(argv)

    profile = load_json(args.profile)
    opps = load_records_common(args.opportunities)
    seen_index = None
    if args.seen and os.path.exists(args.seen):
        seen_index = {k: v.get("status") for k, v in (load_json(args.seen).get("entries") or {}).items()}

    today = dt.date.fromisoformat(args.today) if args.today else None
    res = score_all(profile, opps, seen_index, today, strict=args.strict)
    if res["contract_issues"]:
        print(f"[warn] {len(res['contract_issues'])} 条记录存在 contract 问题"
              "（见输出 contract_issues 字段）", file=sys.stderr)
    payload = render_table(res) if args.format == "table" else json.dumps(res, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print(f"写入 {args.output}（scored={res['scored']} excluded={len(res['excluded'])}）", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
