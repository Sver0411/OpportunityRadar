#!/usr/bin/env python3
"""dedupe.py - 对已结构化的 Opportunity 记录做确定性去重。

确定性部分（URL / 标题 / 机构 / 周期 / 截止日）由本脚本负责；
模糊判断留 `maybe_pairs` 交给模型复核，不自动合并。

三个刻意的保守设计（都来自真实误合并风险）：
  1. **周期守卫**：同一官方 URL 常年复用很常见（Program 2026 / Program 2027）。
     当两边都能确认周期且周期不同时，**不合并**，只列入 cycle_variants 供人工确认。
  2. **URL 大小写安全**：只把 host 转小写，path 保留大小写（很多服务器路径大小写敏感）。
     只删除明确属于投放追踪的参数（utm_* 等），`ref`/`source`/`from` 这类可能承载
     路由语义的参数一律保留。
  3. **聚类一致性**：Union-Find 是单链合并，A~B、B~C 会把 A、C 并到一起。
     因此合并前做一次锚点一致性检查，把与 canonical 不相似的成员剔出。

用法：
  python3 dedupe.py --input opps.json
  python3 dedupe.py --input .opportunity-radar/last-run.json --output deduped.json
  python3 dedupe.py --input opps.json --format text
  python3 dedupe.py --input opps.json --threshold 0.80 --maybe-threshold 0.60
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    canonical_url, core_title, cycle_parts, cycles_conflict, extract_cycle,
    load_records, norm_org, slugify,
)

TRUST_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, None: 4}

#: 冲突检测关注的字段（顺序即报告顺序）
CONFLICT_FIELDS = (
    "deadline", "application_open", "event_start", "event_end", "cost", "compensation",
    "education_level", "student_year", "graduation_window", "country", "city",
    "language_requirement", "GPA_requirement", "official_url",
)

#: 用于"完整度"计分的字段
COMPLETENESS_FIELDS = (
    "title", "organization", "summary", "country", "remote", "education_level",
    "student_year", "major_requirement", "skills_required", "language_requirement",
    "deadline", "cost", "compensation", "official_url", "time_commitment", "tags",
)

#: 周期冲突时的分数上限：低于 maybe-threshold，因此不会被当成"疑似重复"，
#: 而是进入独立的 cycle_variants 通道（默认视为不同机会）
CYCLE_CONFLICT_SCORE = 0.30


# ------------------------------------------------------------------ 归一化

def norm_title(text):
    """标题比较用核心串：去掉年份、季节、通用项目词与括号内容。"""
    return core_title(text) or slugify(text, 64).replace("-", " ")


def tokens(text):
    return set(t for t in (text or "").split() if t)


def sim(a, b):
    import difflib
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
    v = v.strip()
    if field.endswith("url"):
        return canonical_url(v)
    return " ".join(v.lower().split())


# ------------------------------------------------------------------ 相似度

def pair_score(a, b, score_floor=0.56):
    """返回 (score, detail)。score 越高越像同一条机会（同一周期内）。

    流程：先算基础相似度；只有在基础相似度已经达到"候选重复"水平时，
    才用周期守卫去**否决**这次合并。这样既避免了同 URL 跨年误合并，
    也不会把无关项目两两列成"周期冲突"。
    """
    detail = {}
    ua, ub = canonical_url(a.get("official_url")), canonical_url(b.get("official_url"))
    cyc_a, cyc_b = extract_cycle(a), extract_cycle(b)
    detail["cycles"] = [cyc_a, cyc_b]

    if ua and ub and ua == ub:
        base, detail0 = 1.0, {"reason": "same_canonical_url", "url": ua}
    else:
        title_a, title_b = norm_title(a.get("title")), norm_title(b.get("title"))
        org_a, org_b = norm_org(a.get("organization")), norm_org(b.get("organization"))
        t_sim = sim(title_a, title_b)
        o_sim = sim(org_a, org_b)
        base = 0.45 * t_sim + 0.30 * o_sim
        detail0 = {"title_sim": round(t_sim, 3), "org_sim": round(o_sim, 3)}

        # 跨字段信号：一方标题里出现了另一方的机构名，且双方年份一致。
        # 这是"官方页标题不含公司名、聚合站标题含公司名"的常见情形
        # （如 "2027 Summer Internship Program" ↔ "Nagi Robotics 2027 Internship"），
        # 仅比对 title↔title、org↔org 会漏掉它。
        years_a, _ = cycle_parts(a)
        years_b, _ = cycle_parts(b)
        same_year = bool(years_a and years_b and years_a[0] == years_b[0])
        if same_year and len(org_a) >= 4 and len(org_b) >= 4 and (org_a in title_b or org_b in title_a):
            base += 0.20
            detail0["org_in_title"] = True

        dl_a = norm_compare_value("deadline", a.get("deadline"))
        dl_b = norm_compare_value("deadline", b.get("deadline"))
        if dl_a and dl_a == dl_b:
            base += 0.12
            detail0["same_deadline"] = True
        if a.get("country") and a.get("country") == b.get("country"):
            base += 0.05
        if a.get("primary_category") and a.get("primary_category") == b.get("primary_category"):
            base += 0.04
        if a.get("event_start") and a.get("event_start") == b.get("event_start"):
            base += 0.04

        # 保护：机构名差异大时不自动合并（业务主体不同 → 不是同一条）
        if o_sim < 0.55:
            base = min(base, 0.60)
            detail0["org_mismatch_cap"] = True
        if t_sim < 0.35 and o_sim < 0.35:
            base = min(base, 0.50)
            detail0["weak_both"] = True

        # 标题高度一致 + 同类别 + 同国家，但机构名不同 → 可能是同一活动的不同署名/转载，
        # 不足以自动合并，但值得交模型判断，因此抬到"疑似重复"区间（仍低于自动合并阈值）。
        same_cat = bool(a.get("primary_category")) and a.get("primary_category") == b.get("primary_category")
        same_country = bool(a.get("country")) and a.get("country") == b.get("country")
        if t_sim >= 0.60 and same_cat and same_country and base < score_floor:
            base = score_floor
            detail0["org_variant_review"] = True

    base = min(base, 1.0)
    detail.update(detail0)

    # 周期守卫：只对"本来会被判定为重复候选"的对子生效
    if base >= min(score_floor, 0.55):
        conflict, why = cycles_conflict(a, b)
        if conflict:
            detail["reason"] = "different_cycle"
            detail["cycle_conflict"] = why
            detail["hint"] = "周期不同，默认视为不同机会；仅当确认是同一轮时才合并"
            return CYCLE_CONFLICT_SCORE, detail

    return base, detail


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


def enforce_coherence(groups, threshold, score_floor):
    """消除 Union-Find 的单链误合并：把与 canonical 不相似的成员剔出。

    返回 (coherent_groups, ejected)。ejected 中的记录会各自成为独立簇。
    """
    coherent, ejected = [], []
    for members in groups:
        if len(members) < 3:
            coherent.append(members)
            continue
        current = list(members)
        changed = True
        while changed and len(current) >= 3:
            changed = False
            anchor = pick_canonical(current)
            keep = [anchor]
            for m in current:
                if m is anchor:
                    continue
                sc, _ = pair_score(anchor, m, score_floor)
                if sc >= threshold:
                    keep.append(m)
                else:
                    ejected.append(m)
                    changed = True
            current = keep
        coherent.append(current)
    return coherent, ejected


def merge_cluster(members):
    canonical = pick_canonical(members)
    merged = dict(canonical)
    for field in COMPLETENESS_FIELDS + CONFLICT_FIELDS:
        if field == "official_url":
            continue
        if merged.get(field) in (None, "", [], {}):
            for m in sorted(members, key=lambda r: TRUST_RANK.get(r.get("trust_tier"), 4)):
                if m is canonical:
                    continue
                if m.get(field) not in (None, "", [], {}):
                    merged[field] = m[field]
                    merged.setdefault("_merged_fields", {})[field] = m.get("id")
                    break

    conflicts = []
    for field in CONFLICT_FIELDS:
        values = {}
        for m in members:
            v = norm_compare_value(field, m.get(field))
            if v is None:
                continue
            values.setdefault(v, []).append(m)
        if len(values) > 1:
            conflicts.append({
                "field": field,
                "variants": [
                    {"value": v, "ids": [m.get("id") for m in ms],
                     "tiers": [m.get("trust_tier") for m in ms]}
                    for v, ms in values.items()
                ],
                "resolved_by": canonical.get("id"),
                "resolution": "以 trust_tier 最高者的值为准；差异需在输出中说明",
            })

    alt = [{"id": m.get("id"),
            "url": m.get("official_url") or m.get("discovery_url"),
            "tier": m.get("trust_tier"),
            "note": "同一机会的其它来源"}
           for m in members if m.get("id") != canonical.get("id")]
    if alt:
        merged["alternate_sources"] = (merged.get("alternate_sources") or []) + alt

    return merged, canonical, conflicts, alt


def dedupe(records, threshold=0.72, maybe_threshold=0.55):
    records = [r for r in records if isinstance(r, dict)]
    n = len(records)
    if n > 1000:
        print(f"[warn] 记录数 {n} 较大，两两比较约 {n * (n - 1) // 2} 次；"
              "建议先按类别分桶再运行", file=sys.stderr)
    uf = UnionFind(n)
    maybe, auto_pairs, cycle_variants = [], [], []
    score_floor = min(maybe_threshold + 0.01, threshold - 0.01)

    for i, j in combinations(range(n), 2):
        score, detail = pair_score(records[i], records[j], score_floor=score_floor)
        if detail.get("reason") == "different_cycle":
            cycle_variants.append({"a": records[i].get("id"), "b": records[j].get("id"),
                                   "cycles": detail.get("cycles"), "score": round(score, 3),
                                   "hint": detail.get("hint")})
            continue
        if score >= threshold:
            uf.union(i, j)
            auto_pairs.append({"a": records[i].get("id"), "b": records[j].get("id"),
                               "score": round(score, 3), **detail})
        elif score >= maybe_threshold:
            maybe.append({
                "a": records[i].get("id"), "b": records[j].get("id"),
                "score": round(score, 3), **detail,
                "hint": "模糊重复，交模型判断：是否为同一机会？",
            })

    groups = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(records[i])

    coherent, ejected = enforce_coherence(list(groups.values()), threshold, score_floor)
    for m in ejected:
        coherent.append([m])

    clusters = []
    for idx, members in enumerate(sorted(coherent, key=lambda g: -len(g))):
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
        "cycle_variants": cycle_variants,
        "ejected_by_coherence": [m.get("id") for m in ejected],
        "params": {"threshold": threshold, "maybe_threshold": maybe_threshold},
    }


def render_text(res):
    out = [f"input={res['input_count']}  clusters={res['cluster_count']}  removed={res['duplicates_removed']}"]
    for c in res["clusters"]:
        out.append(f"\n[{c['cluster_id']}] size={c['size']} canonical={c['canonical_id']}")
        out.append(f"  title: {c['merged'].get('title')}")
        out.append(f"  org  : {c['merged'].get('organization')}")
        for m in c["member_ids"]:
            if m != c["canonical_id"]:
                out.append(f"  - merged in: {m}")
        for cf in c["conflicts"]:
            vals = " vs ".join(f"{v['value']}({','.join(str(t) for t in v['tiers'])})" for v in cf["variants"])
            out.append(f"  ! conflict {cf['field']}: {vals}")
    if res.get("ejected_by_coherence"):
        out.append("\ncoherence 剔出（原被链式误合并，已拆为独立机会）:")
        for i in res["ejected_by_coherence"]:
            out.append(f"  ~ {i}")
    if res.get("cycle_variants"):
        out.append("\n不同周期（默认视为不同机会，仅在同一轮时才合并）:")
        for p in res["cycle_variants"]:
            out.append(f"  * {p['a']} <> {p['b']}  cycles={p['cycles']}")
    if res["maybe_pairs"]:
        out.append("\n疑似重复（交模型复核）:")
        for p in res["maybe_pairs"]:
            out.append(f"  ? {p['a']} <-> {p['b']}  score={p['score']}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Opportunity 记录确定性去重")
    ap.add_argument("--input", required=True, help="机会 JSON（数组 / {opportunities:[...]} / last-run.json / dedupe 输出）")
    ap.add_argument("--output", help="输出文件；省略则打印到 stdout")
    ap.add_argument("--threshold", type=float, default=0.72, help="自动合并阈值")
    ap.add_argument("--maybe-threshold", type=float, default=0.55, help="疑似重复（交模型复核）阈值")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args(argv)

    records = load_records(args.input)
    res = dedupe(records, args.threshold, args.maybe_threshold)
    payload = render_text(res) if args.format == "text" else json.dumps(res, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + ("" if payload.endswith("\n") else "\n"))
        print(f"写入 {args.output}（input={res['input_count']} → clusters={res['cluster_count']}）", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
