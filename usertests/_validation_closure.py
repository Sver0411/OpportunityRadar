#!/usr/bin/env python3
"""Validation closure：E 空画像 discovery 的链路 + Query Provenance Audit（§1-§3）。

只做验证与定位，**不修改任何核心逻辑**。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gaps as GP             # noqa: E402
import graph as G             # noqa: E402
import portfolio as PF        # noqa: E402
import presentation as P      # noqa: E402
import score as SC            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output-ux", "case-e-unknown")
TODAY = dt.date(2026, 9, 21)

#: 判定一条候选"是否技术类"——用于 technical_share
TECH_CATS = {"skill_development", "open_source", "project", "research", "competition"}
TECH_KEYS = ("programming", "coding", "software", "github", "python", "algorithm", "data science",
             "machine learning", "ai ", "cloud", "kubernetes", "security", "ctf", "ctf",
             "编程", "代码", "开发", "算法", "数据科学", "机器学习")


def is_technical(o) -> dict:
    """技术判定给**理由**，不用单一类别一刀切。"""
    blob = " ".join([str(o.get("title") or ""), str(o.get("summary") or ""),
                     " ".join(str(t) for t in (o.get("tags") or [])),
                     " ".join(str(s) for s in (o.get("skills_required") or []))]).lower()
    kw = [k for k in TECH_KEYS if k in blob]
    cat = str(o.get("primary_category") or "")
    cat_says = cat in TECH_CATS
    # 只有"关键词命中"或"类别+关键词都指向技术"才算技术；纯类别不单独作数
    return {"technical": bool(kw) or (cat_says and bool(o.get("skills_required"))),
            "by_category": cat_says, "by_keyword": kw}


def main():
    prof = json.load(open(os.path.join(OUT, "profile.json"), encoding="utf-8"))
    batch = json.load(open(os.path.join(OUT, "opportunities.json"), encoding="utf-8"))
    opps = batch["opportunities"]
    queries = batch.get("queries_used") or []

    res = SC.score_all(prof, opps, today=TODAY)
    rows = list(res.get("results") or []) + [{**e, "zone": "excluded"}
                                             for e in (res.get("excluded") or [])]
    by_id = {o["id"]: o for o in opps}

    gaps = GP.collect_gaps(opps, prof)
    bridges = G.gap_to_bridge_report(gaps, opps, prof)
    flat = [dict(b, gap=e["gap"]["name"]) for e in bridges for b in e["bridges"]]
    pf = PF.build_portfolio(rows, prof, bridges=flat)
    ans = P.render_answer(prof, rows, gaps, flat, portfolio=pf, mode="E")
    ans["self_directed"] = [P.self_directed_fallback(e["gap"]) for e in bridges
                            if not e["bridges"]
                            and (e["gap"].get("relevance") or {}).get("relevance")
                            in ("core_gap", "supporting_gap")]
    ans["leakage"] = P.context_leakage(prof)

    json.dump({"zones": res.get("zones"), "results": rows},
              open(os.path.join(OUT, "scored.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(gaps, open(os.path.join(OUT, "gaps.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(flat, open(os.path.join(OUT, "bridges.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(pf, open(os.path.join(OUT, "portfolio.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(ans, open(os.path.join(OUT, "answer.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    presented_ids = [c["opportunity_id"] for c in ans["main"] + ans["worth_verifying"]]
    tech = [i for i in presented_ids if is_technical(by_id.get(i, {}))["technical"]]
    axes = (ans.get("explore") or {}).get("axes") or []

    # ---- provenance audit（§3）----
    audit = []
    for oid in presented_ids:
        o = by_id.get(oid, {})
        r = next((x for x in rows if x.get("id") == oid), {})
        row = {x["opportunity_id"]: x for x in ans["main"] + ans["worth_verifying"]}.get(oid, {})
        q = next((x for x in queries if x.get("intended_axis")), {})
        audit.append({
            "opportunity_id": oid,
            "title": o.get("title"),
            "zone": r.get("zone"),
            "category": o.get("primary_category"),
            "explore_axis": P.explore_axes_of(o),
            "origin": o.get("provenance"),
            "source_family": o.get("source_family"),
            "query": q.get("query"),
            "verification_status": o.get("verification_status"),
            "technical": is_technical(o),
            "why_discovered": "空画像 → 无个性化 query；该候选来自上面那条 general_search",
        })

    report = {
        "profile_is_blank": {k: prof.get(k) for k in ("life_stage", "education", "skills",
                                                      "interests", "goals", "constraints")},
        "zones": res.get("zones"),
        "decision_confidence": ans["confidence"]["level"],
        "confidence_unknown": ans["confidence"]["unknown"],
        "explore_axes": axes,
        "explore_axis_count": len(axes),
        "technical_items": tech,
        "presented_count": len(presented_ids),
        "technical_share": round(len(tech) / len(presented_ids), 3) if presented_ids else None,
        "verified_rate": round(sum(1 for o in opps
                                   if o.get("verification_status") == "verified_official")
                               / len(opps), 3),
        "actionable_rate": round(sum(1 for r in rows if r.get("actionable")) / len(rows), 3),
        "field_presence": {
            k: round(sum(1 for o in opps if o.get(k) not in (None, [], {})) / len(opps), 3)
            for k in ("skills_required", "produces", "effort")},
        "violations": ans["violations"],
        "audit": audit,
    }
    json.dump(report, open(os.path.join(OUT, "validation_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print("zones:", res.get("zones"))
    print("confidence:", ans["confidence"]["level"], "| unknown:", ans["confidence"]["unknown"])
    print("axes:", axes, "count:", len(axes))
    print("technical_share:", report["technical_share"], "| technical:", tech)
    print("verified_rate:", report["verified_rate"], "| actionable_rate:", report["actionable_rate"])
    print("field_presence:", report["field_presence"])
    print("violations:", ans["violations"])
    print()
    print("主推荐 / 需确认：")
    for c in ans["main"]:
        print(f"  ★ [{c['participation']['label']}] {c['title'][:52]} | {c.get('effort')}")
    for c in ans["worth_verifying"]:
        print(f"    [{c['participation']['label']}] {c['title'][:52]}")
    print()
    print("— provenance audit —")
    for a in audit:
        print(f"  {str(a['category']):<16} axis={str(a['explore_axis']):<28} "
              f"axis_tech={a['technical']['technical']}  {str(a['title'])[:40]}")


if __name__ == "__main__":
    main()
