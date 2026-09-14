#!/usr/bin/env python3
"""dedupe.py - 对已结构化的 Opportunity 记录做确定性去重。

处理确定性问题（URL / 标题 / 机构 / 截止日），把模糊重复标为 maybe 交给 LLM 判断。
不调用网络，不调用模型。

用法：
  python3 dedupe.py --input opps.json
  python3 dedupe.py --input .opportunity-radar/last-run.json --output deduped.json
  python3 dedupe.py --input opps.json --format text
  python3 dedupe.py --input opps.json --threshold 0.80 --maybe-threshold 0.60
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from itertools import combinations

TRUST_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, None: 4}

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "gclid", "fbclid", "yclid", "msclkid", "ref", "referrer", "source", "spm",
    "from", "share_source", "share_token", "share_medium", "wxshare", "_ga", "mc_cid",
    "mc_eid", "igshid", "trk", "trackingid", "custom_source",
}

ORG_SUFFIXES = [
    "incorporated", "inc", "limited", "ltd", "llc", "plc", "gmbh", "ag", "bv", "nv",
    "sa", "srl", "spa", "pty", "co", "corp", "corporation", "company", "holdings",
    "group", "株式会社", "有限会社", "合同会社", "有限公司", "股份有限公司", "集团",
]

SEASON_WORDS = [
    "spring", "summer", "autumn", "fall", "winter", "online", "remote",
    "春", "夏", "秋", "冬", "暑期", "寒假", "サマー", "ウィンター", "夏季", "冬季",
]

GENERIC_WORDS = [
    "program", "programme", "internship", "internships", "intern", "position",
    "opening", "openings", "recruitment", "campaign", "session", "term",
    "招募", "招聘", "计划", "项目", "实习", "選考", "採用", "募集", "インターン",
]

# 冲突检测关注的字段（顺序即报告顺序）
CONFLICT_FIELDS = [
    "deadline", "application_open", "event_start", "event_end", "cost", "compensation",
    "education_level", "student_year", "graduation_window", "country", "city",
    "language_requirement", "GPA_requirement", "official_url",
]

# 用于"完整度"计分的字段
COMPLETENESS_FIELDS = [
    "title", "organization", "summary", "country", "remote", "education_level",
    "student_year", "major_requirement", "skills_required", "language_requirement",
    "deadline", "cost", "compensation", "official_url", "time_commitment", "tags",
]


# ------------------------------------------------------------------ 归一化

def canonical_url(url):
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if not u:
        return None
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = u.split("#", 1)[0]
    q = ""
    if "?" in u:
        u, q = u.split("?", 1)
    u = u.lower().rstrip("/")
    if u.startswith("www."):
        u = u[4:]
    if q:
        kept = []
        for pair in q.split("&"):
            if not pair:
                continue
            k = pair.split("=", 1)[0].lower()
            if k in TRACKING_PARAMS:
                continue
            kept.append(pair)
        if kept:
            u = u + "?" + "&".join(sorted(kept))
    return u


def norm_org(text):
    if not text:
        return ""
    s = str(text).lower()
    s = re.sub(r"[^\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", " ", s)
    tokens = [t for t in s.split() if t not in ORG_SUFFIXES]
    return " ".join(tokens).strip()


def norm_title(text):
    """去掉年份、季节、通用项目词，得到比较用核心串。"""
    if not text:
        return ""
    s = str(text).lower()
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    s = re.sub(r"\d{4}\s*年", " ", s)
    s = re.sub(r"[（(][^）)]{0,12}[）)]", " ", s)
    s = re.sub(r"[^\w\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", " ", s)
    tokens = [t for t in s.split() if t not in SEASON_WORDS and t not in GENERIC_WORDS]
    return " ".join(tokens).strip()


def tokens(text):
    return set(t for t in (text or "").split() if t)


def sim(a, b):
    a, b = a or "", b or ""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = tokens(a), tokens(b)
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return max(seq, jac)


def as_text(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return " | ".join(str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)


def norm_compare_value(field, v):
    v = as_text(v)
    if v is None:
        return None
    v = v.strip().lower()
    if field.endswith("url"):
        return canonical_url(v)
    return re.sub(r"\s+", " ", v)


# ------------------------------------------------------------------ 相似度

def pair_score(a, b, score_floor=0.56):
    """返回 (score, detail) —— score 越高越像同一条机会。

    score_floor: "标题几乎一致但机构署名不同"时的最低分（抬进模糊重复区间，交 LLM 判断）。
    """
    ua, ub = canonical_url(a.get("official_url")), canonical_url(b.get("official_url"))
    detail = {}
    if ua and ub and ua == ub:
        return 1.0, {"reason": "same_canonical_url", "url": ua}

    t_sim = sim(norm_title(a.get("title")), norm_title(b.get("title")))
    o_sim = sim(norm_org(a.get("organization")), norm_org(b.get("organization")))
    detail.update(title_sim=round(t_sim, 3), org_sim=round(o_sim, 3))

    score = 0.45 * t_sim + 0.30 * o_sim

    dl_a = norm_compare_value("deadline", a.get("deadline"))
    dl_b = norm_compare_value("deadline", b.get("deadline"))
    if dl_a and dl_a == dl_b:
        score += 0.12
        detail["same_deadline"] = True
    if a.get("country") and a.get("country") == b.get("country"):
        score += 0.05
    if a.get("primary_category") and a.get("primary_category") == b.get("primary_category"):
        score += 0.04
    if a.get("event_start") and a.get("event_start") == b.get("event_start"):
        score += 0.04

    # 保护：机构名差异大时不允许自动合并（业务主体不同 → 不是同一条）
    if o_sim < 0.55:
        score = min(score, 0.60)
        detail["org_mismatch_cap"] = True
    # 保护：标题与机构都很不像
    if t_sim < 0.35 and o_sim < 0.35:
        score = min(score, 0.50)
        detail["weak_both"] = True

    # 标题高度一致（difflib ≥0.60）+ 同类别 + 同国家，但机构名不同
    # → 可能是同一活动的不同署名 / D 级转载，不足以自动合并，但值得交给 LLM 判断，
    #   因此抬到"模糊重复"区间（仍低于自动合并阈值）。
    # 门槛刻意偏松：漏判重复（用户看到同一条两次、或看到 D 级站的过期截止日）代价高，
    # 误判只是多一条待 LLM 复核项，代价低。
    same_cat = bool(a.get("primary_category")) and a.get("primary_category") == b.get("primary_category")
    same_country = bool(a.get("country")) and a.get("country") == b.get("country")
    if t_sim >= 0.60 and same_cat and same_country and score < score_floor:
        score = score_floor
        detail["org_variant_review"] = True

    return min(score, 1.0), detail


class UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


# ------------------------------------------------------------------ 合并

def completeness(rec):
    return sum(1 for f in COMPLETENESS_FIELDS if rec.get(f) not in (None, "", [], {}))


def pick_canonical(members):
    """优先 trust_tier，其次字段完整度，最后按 id 稳定排序。"""
    return sorted(
        members,
        key=lambda r: (TRUST_RANK.get(r.get("trust_tier"), 4), -completeness(r), str(r.get("id"))),
    )[0]


def merge_cluster(members):
    canonical = pick_canonical(members)
    merged = dict(canonical)
    conflicts = []

    for field in COMPLETENESS_FIELDS + CONFLICT_FIELDS:
        if field in ("official_url",):
            continue
        if merged.get(field) in (None, "", [], {}):
            for m in sorted(members, key=lambda r: TRUST_RANK.get(r.get("trust_tier"), 4)):
                if m is canonical:
                    continue
                if m.get(field) not in (None, "", [], {}):
                    merged[field] = m[field]
                    merged.setdefault("_merged_fields", {})[field] = m.get("id")
                    break

    for field in CONFLICT_FIELDS:
        values = {}
        for m in members:
            v = norm_compare_value(field, m.get(field))
            if v is None:
                continue
            values.setdefault(v, []).append(m)
        if len(values) > 1:
            variants = []
            for v, ms in values.items():
                variants.append({
                    "value": v,
                    "ids": [m.get("id") for m in ms],
                    "tiers": [m.get("trust_tier") for m in ms],
                })
            conflicts.append({
                "field": field,
                "variants": variants,
                "resolved_by": canonical.get("id"),
                "resolution": "以 trust_tier 最高者的值为准；差异需在输出中说明",
            })

    alt = []
    for m in members:
        if m.get("id") == canonical.get("id"):
            continue
        alt.append({
            "id": m.get("id"),
            "url": m.get("official_url") or m.get("discovery_url"),
            "tier": m.get("trust_tier"),
            "note": "同一机会的其它来源",
        })
    if alt:
        merged["alternate_sources"] = (merged.get("alternate_sources") or []) + alt

    return merged, canonical, conflicts, alt


def load_records(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        for key in ("opportunities", "records", "items", "results"):
            if isinstance(data.get(key), list):
                return data[key]
        raise SystemExit(f"输入 JSON 对象中未找到机会数组（期望键之一：opportunities/records/items/results）：{path}")
    if isinstance(data, list):
        return data
    raise SystemExit(f"无法识别的输入结构：{path}")


def dedupe(records, threshold=0.72, maybe_threshold=0.55):
    records = [r for r in records if isinstance(r, dict)]
    n = len(records)
    uf = UnionFind(n)
    maybe = []
    auto_pairs = []
    # 抬升下限必须仍低于自动合并阈值，否则会把"待人工判断"误升级为自动合并
    score_floor = min(maybe_threshold + 0.01, threshold - 0.01)

    for i, j in combinations(range(n), 2):
        score, detail = pair_score(records[i], records[j], score_floor=score_floor)
        if score >= threshold:
            uf.union(i, j)
            auto_pairs.append({"a": records[i].get("id"), "b": records[j].get("id"),
                               "score": round(score, 3), **detail})
        elif score >= maybe_threshold:
            maybe.append({
                "a": records[i].get("id"), "b": records[j].get("id"),
                "score": round(score, 3), **detail,
                "hint": "模糊重复，交 LLM 判断：是否为同一机会？",
            })

    groups = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(records[i])

    clusters = []
    for idx, members in enumerate(sorted(groups.values(), key=lambda g: -len(g))):
        merged, canonical, conflicts, alt = merge_cluster(members)
        merged = dict(merged)
        merged["id"] = canonical.get("id")
        clusters.append({
            "cluster_id": f"c{idx + 1:03d}",
            "canonical_id": canonical.get("id"),
            "size": len(members),
            "member_ids": [m.get("id") for m in members],
            "merged": merged,
            "conflicts": conflicts,
            "alternate_sources": alt,
        })

    return {
        "input_count": n,
        "cluster_count": len(clusters),
        "duplicates_removed": n - len(clusters),
        "clusters": clusters,
        "auto_merged_pairs": auto_pairs,
        "maybe_pairs": maybe,
        "params": {"threshold": threshold, "maybe_threshold": maybe_threshold},
    }


def render_text(res):
    out = []
    out.append(f"input={res['input_count']}  clusters={res['cluster_count']}  removed={res['duplicates_removed']}")
    for c in res["clusters"]:
        title = c["merged"].get("title")
        out.append(f"\n[{c['cluster_id']}] size={c['size']} canonical={c['canonical_id']}")
        out.append(f"  title: {title}")
        out.append(f"  org  : {c['merged'].get('organization')}")
        for m in c["member_ids"]:
            if m != c["canonical_id"]:
                out.append(f"  - merged in: {m}")
        for cf in c["conflicts"]:
            vals = " vs ".join(f"{v['value']}({','.join(str(t) for t in v['tiers'])})" for v in cf["variants"])
            out.append(f"  ! conflict {cf['field']}: {vals}")
    if res["maybe_pairs"]:
        out.append("\nmight be duplicates (LLM review):")
        for p in res["maybe_pairs"]:
            out.append(f"  ? {p['a']} <-> {p['b']}  score={p['score']}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Opportunity 记录确定性去重")
    ap.add_argument("--input", required=True, help="机会 JSON（数组 / {opportunities:[...]} / last-run.json）")
    ap.add_argument("--output", help="输出文件；省略则打印到 stdout")
    ap.add_argument("--threshold", type=float, default=0.72, help="自动合并阈值")
    ap.add_argument("--maybe-threshold", type=float, default=0.55, help="模糊重复（交 LLM 判断）阈值")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args(argv)

    records = load_records(args.input)
    res = dedupe(records, args.threshold, args.maybe_threshold)
    payload = render_text(res) if args.format == "text" else json.dumps(res, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + ("\n" if not payload.endswith("\n") else ""))
        print(f"写入 {args.output}（input={res['input_count']} → clusters={res['cluster_count']}）", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
