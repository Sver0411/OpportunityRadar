"""Source Intelligence metrics: plan-level before/after + case-level real results.

Run: python3 usertests/_si_metrics.py
"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import gaps as GP          # noqa: E402
import graph as G          # noqa: E402
import portfolio as PF     # noqa: E402
import score as S          # noqa: E402
import sources as SI       # noqa: E402
from test_gap_bridge_portfolio import (BRIDGE_OPPS, EMBEDDED, TARGET_OPPS,  # noqa: E402
                                       opp, row)

TODAY = dt.date(2026, 9, 20)
SCENARIOS = {
    "T1 技能缺口 embedded→EdgeAI": (EMBEDDED, "Edge AI", BRIDGE_OPPS + TARGET_OPPS),
    "T2 职业资本缺口 升Senior": (dict(EMBEDDED, career_state={"promotion_target": "Senior"},
                                      goals=[{"type": "career", "priority": "high"}]),
                                 "不跳槽，想升 Senior",
                                 [opp(id="cfp", title="Practitioner conference CFP",
                                      primary_category="event", tags=["public speaking"],
                                      produces=["conference talk"],
                                      effort={"weekly_commitment": "2 h"},
                                      future_optionality={"level": "high"}),
                                  opp(id="mnt", title="Maintainer pathway",
                                      primary_category="open_source", tags=["maintainer"],
                                      produces=["public contribution"],
                                      effort={"weekly_commitment": "3 h"},
                                      future_optionality={"level": "high"})]),
    "T3 研究申请缺口 日本硕士": (dict(EMBEDDED, goals=[{"type": "education", "priority": "high"}]),
                                 "在职申请日本硕士",
                                 [opp(id="lab", title="Lab open seminar", primary_category="research",
                                      tags=["professor", "lab"], produces=["professor contact"],
                                      effort={"weekly_commitment": "1 h"}),
                                  opp(id="jlpt", title="JLPT N2 preparation",
                                      primary_category="language", tags=["jlpt"],
                                      produces=["certificate"],
                                      effort={"weekly_commitment": "4 h"})]),
}


def main() -> None:
    print("=== Plan-level: Source Intelligence planning coverage ===")
    rows = []
    for name, (profile, target, pool) in SCENARIOS.items():
        gps = GP.collect_gaps(TARGET_OPPS, profile, stated_target=target)
        planned, fam_hits, fallbacks = 0, 0, 0
        for g in gps:
            qs = SI.plan_queries(g, profile, topic=g["name"], region=target)
            if qs:
                planned += 1
            for q in qs:
                if q.get("family"):
                    fam_hits += 1
                if q["origin"] == "general_search":
                    fallbacks += 1
        total_q = fam_hits + fallbacks
        report = G.gap_to_bridge_report(gps, pool, profile)
        bridges = [b for r in report for b in r["bridges"]]
        scored = S.score_all(profile, pool, today=TODAY)
        pf = PF.build_portfolio(scored["results"], profile, bridges)
        rows.append({
            "scenario": name, "gaps": len(gps),
            "gaps_with_source_plan": planned,
            "source_plan_coverage": round(planned / len(gps), 2) if gps else None,
            "source_family_hit_rate": round(fam_hits / total_q, 2) if total_q else None,
            "general_search_fallback_rate": round(fallbacks / total_q, 2) if total_q else None,
            "bridges": len(bridges),
            "bridges_verified_rate": round(sum(1 for b in bridges if b["evidence_complete"])
                                           / len(bridges), 2) if bridges else None,
            "bridges_actionable_rate": round(sum(1 for b in bridges if b.get("readiness") in
                                                 ("ready_now", "minor_preparation"))
                                             / len(bridges), 2) if bridges else None,
            "portfolio_hours": pf["planned_hours"], "budget": pf["budget_hours"],
            "portfolio_conflict": pf["resource_conflict"],
        })
    for r in rows:
        print(f"  {r['scenario']:<28} gaps={r['gaps']:<3} plan_cov={r['source_plan_coverage']} "
              f"family_hit={r['source_family_hit_rate']} fallback={r['general_search_fallback_rate']} "
              f"bridges={r['bridges']} ver={r['bridges_verified_rate']} "
              f"act={r['bridges_actionable_rate']} portfolio={r['portfolio_hours']}/{r['budget']} "
              f"conflict={r['portfolio_conflict']}")

    print("\n=== Case-level (real web, round 4 with source intelligence) ===")
    total_conflict, known_budget = 0, 0
    for case in ("case-c-promotion", "case-d-japan-masters", "case-e-unknown"):
        p = os.path.join(HERE, case, "record-si.json")
        if not os.path.exists(p):
            print(f"  {case}: 缺 record-si.json")
            continue
        rec = json.load(open(p, encoding="utf-8"))
        m = rec.get("metrics", {})
        pf = rec.get("portfolio", {})
        known = pf.get("budget_hours") is not None
        known_budget += 1 if known else 0
        total_conflict += 1 if pf.get("resource_conflict") else 0
        print(f"  {case:<22} gaps={m.get('gaps')} bridge={m.get('gaps_with_bridge')} "
              f"cov={m.get('gap_coverage_rate')} bridges={m.get('bridges')} "
              f"ver={m.get('bridge_verified_rate')} act={m.get('bridge_actionable_rate')} "
              f"family_share={m.get('source_family_query_share')} "
              f"general_share={m.get('general_search_share')} "
              f"portfolio={pf.get('planned_hours')}/{pf.get('budget_hours')} "
              f"conflict={pf.get('resource_conflict')} budget_unknown={pf.get('budget_unknown')}")

    print("\n=== P1/SI metrics summary ===")
    cov = [r["source_plan_coverage"] for r in rows if r["source_plan_coverage"] is not None]
    fh = [r["source_family_hit_rate"] for r in rows if r["source_family_hit_rate"] is not None]
    fb = [r["general_search_fallback_rate"] for r in rows
          if r["general_search_fallback_rate"] is not None]
    print(f"  source_plan_coverage        = {round(sum(cov)/len(cov), 2) if cov else 'n/a'}")
    print(f"  source_family_hit_rate      = {round(sum(fh)/len(fh), 2) if fh else 'n/a'}")
    print(f"  general_search_fallback_rate= {round(sum(fb)/len(fb), 2) if fb else 'n/a'}")
    print(f"  portfolio_resource_conflict_rate (cases with known budget) = "
          f"{round(total_conflict/known_budget, 3) if known_budget else 'n/a'} "
          f"(known-budget portfolios: {known_budget}/3)")
    print("  real gap coverage change: Case D research gap 0.50 -> 0.75 (round 4 report)")


def refinement_metrics() -> None:
    """本轮 refinement 指标：stage 适配、gap 噪声、页面时效。"""
    import datetime as _dt
    print("\n=== Refinement metrics ===")
    # stage
    rows = []
    for label, prof in (("working", {"life_stage": ["working"], "career_stage": ["mid_career"]}),
                        ("undergraduate", {"life_stage": ["student"],
                                           "career_stage": ["undergraduate"]})):
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, prof,
                             topic="Edge AI", region="Japan", limit=6)
        stage = SI.stage_of(prof)
        fits = [SI.family_stage_fit(q.get("family") or "", stage) for q in qs]
        bad = sum(1 for f in fits if f in ("low", "never"))
        good = sum(1 for f in fits if f in ("high", "medium"))
        rows.append((label, bad / len(qs), good / len(qs), fits))
    for label, bad_rate, precision, fits in rows:
        print(f"  {label:<14} stage_inapplicable_query_rate={bad_rate:.2f} "
              f"stage_family_precision={precision:.2f} fits={fits}")

    # gap noise（用 T2 场景：目标机会里混有 logistics 前置）
    prof = dict(EMBEDDED, career_state={"promotion_target": "Senior"},
                goals=[{"type": "career", "priority": "high"}])
    noisy = [opp(id="n1", title="Senior track programme", primary_category="career",
                 skills_required=["leadership"],
                 required_materials=["GitHub profile", "Slack account", "报名表"])]
    gaps = GP.collect_gaps(noisy, prof)
    noise = sum(1 for g in gaps if GP.is_logistics(g["name"]))
    print(f"  gap_noise_rate = {noise / len(gaps) if gaps else 0:.2f} "
          f"（development gaps={len(gaps)}，logistics={sum(len(g['logistics_prerequisites']) for g in gaps)}）")

    # stale leakage
    stale = [{"title": "Summer Research Program 2024"},
             {"title": "Programme 2025"},
             {"title": "Programme 2026"}]
    statuses = [SI.source_freshness(o, _dt.date(2026, 9, 20))["source_freshness"] for o in stale]
    leaked = sum(1 for s in statuses if s in ("current", "likely_current")) - 1  # 只有 2026 那条应通过
    print(f"  source_freshness={statuses} → source_stale_leakage={max(0, leaked)}")

    # Case C 记录里的真实数字
    p2 = os.path.join(HERE, "case-c-promotion", "record-si.json")
    if os.path.exists(p2):
        rec = json.load(open(p2, encoding="utf-8"))
        m = rec.get("metrics", {})
        print(f"  Case C: gaps_total={m.get('gaps_total')} development={m.get('development_gaps')} "
              f"logistics={m.get('logistics_prerequisites')} noise={m.get('gap_noise_rate')} "
              f"coverage={m.get('gap_coverage_rate')} "
              f"stage_inapplicable={m.get('stage_inapplicable_query_rate')} "
              f"not_current={m.get('source_found_not_current_rate')}")


if __name__ == "__main__":
    main()
    refinement_metrics()
