#!/usr/bin/env python3
"""state.py - 本地轻量状态：seen / saved / ignored。

目的：不重复推荐同一件事；注意到关键字段变化；让用户反馈（有界地）影响下一轮。
不引入服务、数据库或网络请求。纯标准库。

目录结构（默认 ./.opportunity-radar，可用 --dir 覆盖）：
  seen.json    已见机会（first_seen / last_seen / tracked_hash / change_log）
  saved.json   interested / saved / applied
  ignored.json ignored / not_relevant

用法：
  python3 state.py init
  python3 state.py mark-seen --input .opportunity-radar/last-run.json
  python3 state.py check --input opps.json
  python3 state.py feedback saved --id sony-embedded-internship-2027 --note "关注"
  python3 state.py list --status saved
  python3 state.py show --id sony-embedded-internship-2027
  python3 state.py suggest
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import TRACKED_FIELDS, canonical_url, derive_id, load_records  # noqa: E402

DEFAULT_DIR = ".opportunity-radar"
STATE_VERSION = 1

SAVED_STATUSES = {"interested", "saved", "applied"}
IGNORED_STATUSES = {"ignored", "not_relevant"}
ALL_STATUSES = SAVED_STATUSES | IGNORED_STATUSES


# ------------------------------------------------------------------ IO

def now_iso():
    return dt.datetime.now().replace(microsecond=0).isoformat()


def path_for(base, kind):
    return os.path.join(base, f"{kind}.json")


def empty(kind):
    return {"version": STATE_VERSION, "updated_at": now_iso(), "entries": {}}


def load(base, kind):
    """读取状态文件。损坏时备份为 .bak 并返回空结构（不静默丢用户数据）。"""
    p = path_for(base, kind)
    if not os.path.exists(p):
        return empty(kind)
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
            raise ValueError("结构不符合预期")
        data.setdefault("version", STATE_VERSION)
        return data
    except Exception as exc:                                    # noqa: BLE001
        bak = p + ".bak"
        shutil.copy2(p, bak)
        print(f"[warn] {p} 无法解析（{exc}），已备份到 {bak}，并重建空状态文件", file=sys.stderr)
        return empty(kind)


def save(base, kind, data):
    os.makedirs(base, exist_ok=True)
    data["updated_at"] = now_iso()
    data["version"] = STATE_VERSION
    p = path_for(base, kind)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, p)


# ------------------------------------------------------------------ 哈希与变化

def canonical_value(field, value):
    """变化检测用的规范化值。URL 复用 common.canonical_url，
    保证"只是 utm/参数顺序变化"不会被误报为 changed。
    """
    if value is None:
        return None
    if field.endswith("url"):
        return canonical_url(value)
    if isinstance(value, (list, tuple)):
        return sorted(str(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def tracked_of(rec):
    return {f: canonical_value(f, rec.get(f)) for f in TRACKED_FIELDS}


def tracked_hash(tracked):
    blob = json.dumps(tracked, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def entry_stub(rec, status, prev=None):
    ts = now_iso()
    return {
        "opportunity_id": rec.get("id"),
        "title": rec.get("title"),
        "organization": rec.get("organization"),
        "official_url": rec.get("official_url"),
        "first_seen": (prev or {}).get("first_seen", ts),
        "last_seen": ts,
        "status": status,
        "tracked_hash": tracked_hash(tracked_of(rec)),
        "tracked": tracked_of(rec),
        "change_log": (prev or {}).get("change_log", []),
    }


# ------------------------------------------------------------------ 命令

def cmd_init(base, force=False):
    if os.path.exists(base) and not force:
        print(f"{base} 已存在（幂等，不覆盖）。如需重建请加 --force", file=sys.stderr)
    os.makedirs(base, exist_ok=True)
    for kind in ("seen", "saved", "ignored"):
        p = path_for(base, kind)
        if os.path.exists(p) and not force:
            continue
        if os.path.exists(p) and force:
            shutil.copy2(p, p + ".bak")
        save(base, kind, empty(kind))
    print(f"状态目录就绪：{os.path.abspath(base)}")


def classify(base, records, write=True):
    seen = load(base, "seen")
    out = {"new": [], "changed": [], "repeat": [], "details": {}, "dry_run": not write}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        rid = rec.get("id") or derive_id(rec)
        rec.setdefault("id", rid)
        prev = seen["entries"].get(rid)
        cur = tracked_of(rec)
        if prev is None:
            out["new"].append(rid)
            if write:
                seen["entries"][rid] = entry_stub(rec, "new")
            continue
        changes = []
        prev_tracked = prev.get("tracked") or {}
        for f in TRACKED_FIELDS:
            if canonical_value(f, prev_tracked.get(f)) != cur[f]:
                changes.append({"at": now_iso(), "field": f,
                                "from": prev_tracked.get(f), "to": cur[f]})
        if changes:
            out["changed"].append(rid)
            out["details"][rid] = changes
            if write:
                stub = entry_stub(rec, "changed", prev)
                stub["change_log"] = (prev.get("change_log") or [])[-20:] + changes
                seen["entries"][rid] = stub
        else:
            out["repeat"].append(rid)
            if write:
                prev["last_seen"] = now_iso()
                prev["status"] = "repeat"
    if write:
        save(base, "seen", seen)
    return out


def cmd_mark_seen(base, input_path, quiet=False):
    records = load_records(input_path)
    if not os.path.exists(base):
        os.makedirs(base, exist_ok=True)
        for kind in ("seen", "saved", "ignored"):
            if not os.path.exists(path_for(base, kind)):
                save(base, kind, empty(kind))
    res = classify(base, records, write=True)
    if not quiet:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def cmd_check(base, input_path):
    res = classify(base, load_records(input_path), write=False)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def cmd_feedback(base, status, rid, note=None, title=None, org=None, url=None,
                 tags=None, category=None):
    if status not in ALL_STATUSES:
        raise SystemExit(f"未知状态：{status}（可用：{', '.join(sorted(ALL_STATUSES))}）")
    os.makedirs(base, exist_ok=True)
    own, other = ("saved", "ignored") if status in SAVED_STATUSES else ("ignored", "saved")
    own_data = load(base, own)
    other_data = load(base, other)
    prev = own_data["entries"].get(rid) or {}
    ts = now_iso()
    own_data["entries"][rid] = {
        "opportunity_id": rid,
        "title": title or prev.get("title"),
        "organization": org or prev.get("organization"),
        "official_url": url or prev.get("official_url"),
        "status": status,
        "primary_category": category or prev.get("primary_category"),
        "tags": (tags.split(",") if isinstance(tags, str) else tags) or prev.get("tags"),
        "first_seen": prev.get("first_seen", ts),
        "last_seen": ts,
        "note": note or prev.get("note"),
    }
    if rid in other_data["entries"]:
        del other_data["entries"][rid]
        save(base, other, other_data)
    save(base, own, own_data)
    print(f"已记录 {rid} → {status}（{own}.json）")


def cmd_list(base, status=None):
    rows = []
    for kind in ("seen", "saved", "ignored"):
        data = load(base, kind)
        for rid, e in data["entries"].items():
            rows.append({"file": f"{kind}.json", "id": rid, "status": e.get("status"),
                         "title": e.get("title"), "org": e.get("organization"),
                         "last_seen": e.get("last_seen")})
    if status:
        rows = [r for r in rows if r["status"] == status]
    if not rows:
        print("（无记录）")
        return
    for r in sorted(rows, key=lambda x: (x["file"], str(x["title"]))):
        print(f"[{r['status']:<14}] {r['id']:<50} {r['title']}")


def cmd_show(base, rid):
    found = False
    for kind in ("seen", "saved", "ignored"):
        e = load(base, kind)["entries"].get(rid)
        if e:
            found = True
            print(f"--- {kind}.json ---")
            print(json.dumps(e, ensure_ascii=False, indent=2))
    if not found:
        print(f"未找到 {rid}")


def cmd_suggest(base):
    """只读：根据 saved/ignored 给出权重建议（不修改 profile）。

    标签/类别优先取反馈条目自身携带的值（feedback --tags/--category），
    其次回落到 .opportunity-radar/last-run.json。
    """
    saved = load(base, "saved")["entries"]
    ignored = load(base, "ignored")["entries"]
    pos, neg = {}, {}
    unresolved = 0

    def bump(bag, key, weight=1):
        if key:
            bag[key] = bag.get(key, 0) + weight

    last_run = os.path.join(base, "last-run.json")
    catalog = {}
    if os.path.exists(last_run):
        try:
            with open(last_run, encoding="utf-8") as fh:
                for o in (json.load(fh).get("opportunities") or []):
                    catalog[o.get("id")] = (o.get("tags") or [], o.get("primary_category"))
        except Exception:                                       # noqa: BLE001
            pass

    for rid, e in saved.items():
        w = 2 if e.get("status") == "applied" else 1
        tg = e.get("tags") or (catalog.get(rid) or ([], None))[0]
        cat = e.get("primary_category") or (catalog.get(rid) or ([], None))[1]
        if not tg and not cat:
            unresolved += 1
        for t in tg or []:
            bump(pos, t, w)
        bump(pos, cat, w)
    for rid, e in ignored.items():
        w = 2 if e.get("status") == "not_relevant" else 1
        tg = e.get("tags") or (catalog.get(rid) or ([], None))[0]
        cat = e.get("primary_category") or (catalog.get(rid) or ([], None))[1]
        if not tg and not cat:
            unresolved += 1
        for t in tg or []:
            bump(neg, t, w)
        bump(neg, cat, w)

    if not pos and not neg:
        if unresolved:
            print(f"有 {unresolved} 条反馈记录，但没有可用的标签/类别信息，无法给出方向建议。\n"
                  "记录反馈时请带上 --category/--tags，或先写入 .opportunity-radar/last-run.json。")
        else:
            print("还没有足够的反馈记录（saved/ignored 为空），暂不建议调整权重。")
        return

    lines = ["基于本地反馈的权重建议（仅供参考，未修改 profile）："]
    for k, v in sorted(pos.items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  ↑ 提高「{k}」方向权重（正向信号 {v} 次）")
    for k, v in sorted(neg.items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  ↓ 降低「{k}」方向权重（负向信号 {v} 次）")
    if unresolved:
        lines.append(f"  注：有 {unresolved} 条记录缺少标签/类别，未计入。")
    lines.append("提示：连续 3 次以上对同一大类给出负反馈才建议下调整个类别。"
                 "如需写入画像，请先向用户确认。")
    print("\n".join(lines))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="OpportunityRadar 本地状态（seen/saved/ignored）")
    ap.add_argument("--dir", default=DEFAULT_DIR, help=f"状态目录，默认 {DEFAULT_DIR}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="创建状态目录与空文件（幂等）")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("mark-seen", help="标记已见并检测变化")
    p.add_argument("--input", required=True)
    p.add_argument("--quiet", action="store_true")

    p = sub.add_parser("check", help="只分类（new/changed/repeat），不写入")
    p.add_argument("--input", required=True)

    p = sub.add_parser("feedback", help="记录用户反馈")
    p.add_argument("status", choices=sorted(ALL_STATUSES))
    p.add_argument("--id", required=True)
    p.add_argument("--note")
    p.add_argument("--title")
    p.add_argument("--org")
    p.add_argument("--url")
    p.add_argument("--category", help="primary_category，用于后续权重建议")
    p.add_argument("--tags", help="逗号分隔的标签，用于后续权重建议")

    p = sub.add_parser("list", help="列出条目")
    p.add_argument("--status")

    p = sub.add_parser("show", help="查看单条")
    p.add_argument("--id", required=True)

    sub.add_parser("suggest", help="只读：输出权重建议")

    args = ap.parse_args(argv)
    base = args.dir
    if args.cmd == "init":
        cmd_init(base, args.force)
    elif args.cmd == "mark-seen":
        cmd_mark_seen(base, args.input, args.quiet)
    elif args.cmd == "check":
        cmd_check(base, args.input)
    elif args.cmd == "feedback":
        cmd_feedback(base, args.status, args.id, args.note, args.title, args.org, args.url,
                     args.tags, args.category)
    elif args.cmd == "list":
        cmd_list(base, args.status)
    elif args.cmd == "show":
        cmd_show(base, args.id)
    elif args.cmd == "suggest":
        cmd_suggest(base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
