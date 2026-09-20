"""Compute the P1 metrics over the five required scenarios.

Run: python3 usertests/_p1_metrics.py
"""
import datetime as dt
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
from test_gap_bridge_portfolio import (BRIDGE_OPPS, EMBEDDED, TARGET_OPPS,  # noqa: E402
                                       opp, row)

TODAY = dt.date(2026, 9, 20)


def run_scenario(name, profile, target, pool, budget_hours=None, rows=None):
    gps = GP.collect_gaps(TARGET_OPPS, profile, stated_target=target) if target else \
        GP.collect_gaps([], profile)
    report = G.gap_to_bridge_report(gps, pool, profile)
    bridges = [b for r in report for b in r["bridges"]]
    scored = S.score_all(profile, pool, today=TODAY)
    portfolio = PF.build_portfolio(scored["results"] if rows is None else rows,
                                   profile, bridges, budget_hours)
    graph = G.bridge_graph(gps, pool, profile, goal=target)
    gaps_with_bridge = [r for r in report if r["bridges"]]
    return {
        "scenario": name,
        "gaps": len(gps),
        "gaps_with_bridge": len(gaps_with_bridge),
        "gap_coverage_rate": round(len(gaps_with_bridge) / len(report), 2) if report else None,
        "bridges": len(bridges),
        "bridges_verified": sum(1 for b in bridges if b["evidence_complete"]),
        "bridge_verified_rate": round(sum(1 for b in bridges if b["evidence_complete"])
                                      / len(bridges), 2) if bridges else None,
        "bridges_actionable": sum(1 for b in bridges if b.get("readiness") in
                                  ("ready_now", "minor_preparation")),
        "bridge_actionable_rate": round(sum(1 for b in bridges if b.get("readiness") in
                                            ("ready_now", "minor_preparation")) / len(bridges), 2)
                                  if bridges else None,
        "graph_connected": graph["connected"],
        "portfolio": {"roles": portfolio["roles_present"],
                      "planned_hours": portfolio["planned_hours"],
                      "budget_hours": portfolio["budget_hours"],
                      "conflict": portfolio["resource_conflict"],
                      "diversity": portfolio["diversity"],
                      "dropped": len(portfolio["dropped"])},
    }


def main() -> None:
    results = []

    # Test 1：技能缺口（3 年嵌入式 → Edge AI，6h/周）
    results.append(run_scenario("T1 技能缺口 embedded→EdgeAI", EMBEDDED, "Edge AI",
                                BRIDGE_OPPS + TARGET_OPPS))

    # Test 2：职业资本缺口（不跳槽升 Senior）
    prof2 = dict(EMBEDDED, career_state={"promotion_target": "Senior"},
                 goals=[{"type": "career", "priority": "high"}])
    pool2 = [opp(id="cfp", title="Practitioner conference CFP", primary_category="event",
                 tags=["public speaking"], produces=["conference talk"],
                 effort={"weekly_commitment": "2 h"}, future_optionality={"level": "high"},
                 application_status="open",
                 evidence={"application_status": {"status": "explicit",
                                                  "source_url": "https://x.example/cfp",
                                                  "verified_at": "2026-09-19"}}),
             opp(id="mnt", title="Maintainer pathway", primary_category="open_source",
                 tags=["maintainer"], produces=["public contribution"],
                 effort={"weekly_commitment": "3 h"}, future_optionality={"level": "high"})]
    results.append(run_scenario("T2 职业资本缺口 升Senior", prof2, "不跳槽，想升 Senior", pool2))

    # Test 3：研究申请缺口（在职申请日本硕士）
    prof3 = dict(EMBEDDED, goals=[{"type": "education", "priority": "high"}])
    pool3 = [opp(id="lab", title="Lab open seminar", primary_category="research",
                 tags=["professor", "lab"], produces=["professor contact"],
                 effort={"weekly_commitment": "1 h"}),
             opp(id="jlpt", title="JLPT N2 preparation", primary_category="language",
                 tags=["jlpt"], produces=["certificate"], effort={"weekly_commitment": "4 h"})]
    results.append(run_scenario("T3 研究申请缺口 日本硕士", prof3, "在职申请日本硕士", pool3))

    # Test 4：资源冲突（每周 5h）
    rows4 = [row(id="a", effort={"weekly_commitment": "5 h"}, utility="high"),
             row(id="b", effort={"weekly_commitment": "4 h"}, utility="medium"),
             row(id="c", effort={"weekly_commitment": "3 h"}, utility="low")]
    results.append(run_scenario("T4 资源冲突 5h/周",
                                {"constraints": {"weekly_time": "5"}}, None, [], rows=rows4))

    # Test 5：目标模糊
    prof5 = {"skills": [{"name": "Python"}], "constraints": {"remote": True, "weekly_time": "5"}}
    rows5 = [row(id="lc", effort={"weekly_commitment": "1 h"}, time_to_value="immediate"),
             row(id="ex", layer="explore", novelty=85, effort={"weekly_commitment": "2 h"}),
             row(id="hu", future_optionality={"level": "high"},
                 effort={"weekly_commitment": "3 h"})]
    results.append(run_scenario("T5 目标模糊", prof5, None, [], rows=rows5))

    conflicts = [r for r in results if r["portfolio"]["conflict"]]
    print(f"{'scenario':<34} {'gaps':>4} {'cov':>5} {'bridges':>7} {'ver':>5} {'act':>5} "
          f"{'graph':>5} {'hours':>6}/{'-':<4} {'conflict':>8}")
    for r in results:
        p = r["portfolio"]
        print(f"{r['scenario']:<34} {r['gaps']:>4} {str(r['gap_coverage_rate']):>5} "
              f"{r['bridges']:>7} {str(r['bridge_verified_rate']):>5} "
              f"{str(r['bridge_actionable_rate']):>5} {str(r['graph_connected']):>5} "
              f"{p['planned_hours']:>6}/{str(p['budget_hours']):<4} {str(p['conflict']):>8}")
        print(f"{'':<34} roles={p['roles']} diversity={p['diversity']} dropped={p['dropped']}")

    cov = [r["gap_coverage_rate"] for r in results if r["gap_coverage_rate"] is not None]
    ver = [r["bridge_verified_rate"] for r in results if r["bridge_verified_rate"] is not None]
    act = [r["bridge_actionable_rate"] for r in results if r["bridge_actionable_rate"] is not None]
    print("\n=== P1 metrics ===")
    print(f"  gap_coverage_rate            = {round(sum(cov)/len(cov), 2) if cov else 'n/a'}")
    print(f"  bridge_verified_rate         = {round(sum(ver)/len(ver), 2) if ver else 'n/a'}")
    print(f"  bridge_actionable_rate       = {round(sum(act)/len(act), 2) if act else 'n/a'}")
    print(f"  portfolio_resource_conflict_rate = {round(len(conflicts)/len(results), 2)}")
    print(f"  portfolio_diversity (roles/categories) = "
          f"{[ (r['portfolio']['diversity']['roles'], r['portfolio']['diversity']['categories']) for r in results ]}")
    print(f"  graph_connected_rate         = "
          f"{round(sum(1 for r in results if r['graph_connected'])/len(results), 2)}")


if __name__ == "__main__":
    main()
