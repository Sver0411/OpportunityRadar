"""P1 ①②：Gap → Bridge Opportunity → Portfolio。

5 个必测 case（技能缺口 / 职业资本缺口 / 研究申请缺口 / 资源冲突 / 目标模糊）
+ P1 指标（portfolio_resource_conflict_rate 必须为 0）。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import gaps as GP       # noqa: E402
import graph as G       # noqa: E402
import portfolio as PF  # noqa: E402
import score as S       # noqa: E402

TODAY = dt.date(2026, 9, 20)


def opp(**kw):
    base = {"id": "o1", "title": "Opportunity", "organization": "Org",
            "primary_category": "project", "official_url": "https://x.example/o1",
            "verification_status": "verified_official", "remote": True,
            "application_status": "open",
            "evidence": {"application_status": {"status": "explicit",
                                                "source_url": "https://x.example/o1",
                                                "verified_at": "2026-09-19"}}}
    base.update(kw)
    return base


def row(**kw):
    base = {"id": "r1", "title": "Row", "primary_category": "project",
            "zone": "recommended_now", "utility": "medium", "match_score": 70,
            "official_url": "https://x.example/r1"}
    base.update(kw)
    return base


EMBEDDED = {
    "life_stage": ["working"], "career_stage": ["early_career", "career_switcher"],
    "employment": {"status": "full_time", "function": "engineering", "years_of_experience": 3},
    "career_state": {"target_role": "Edge AI engineer", "switch_intent": "high"},
    "skills": [{"name": "C"}, {"name": "ESP32"}, {"name": "Python"}],
    "interests": ["embedded", "ai"],
    "goals": [{"type": "skill", "priority": "high"}, {"type": "career", "priority": "medium"}],
    "constraints": {"preferred_country": ["Japan"], "remote": True, "weekly_time": "6"},
}

# 目标机会：反复要求 RTOS / TinyML（Gap 的真实来源）
TARGET_OPPS = [
    opp(id="t1", title="Embedded AI internship", primary_category="career",
        skills_required=["RTOS", "TinyML"], country="Japan"),
    opp(id="t2", title="Edge AI research programme", primary_category="research",
        skills_required=["RTOS"], language_requirement={"language": "Japanese", "min_level": "N2"}),
    opp(id="t3", title="TinyML build challenge", primary_category="competition",
        skills_required=["TinyML"], required_materials=["demo video"]),
]

# 真实 Bridge 机会（有 canonical source + 可展示产出）
BRIDGE_OPPS = [
    opp(id="b1", title="FreeRTOS scheduler issue (good first issue)", primary_category="open_source",
        tags=["rtos", "freertos"], produces=["GitHub PR", "public contribution"],
        unlocks=[{"type": "embedded_internship"}], effort={"weekly_commitment": "4-6 h"},
        future_optionality={"level": "high", "reason": "公开 PR → 实习/研究通道"}),
    opp(id="b2", title="TinyML deployment challenge", primary_category="competition",
        tags=["tinyml", "edge ai"], produces=["demo", "technical writeup"],
        unlocks=[{"type": "research_opportunity"}], effort={"weekly_commitment": "5 h"},
        future_optionality={"level": "high"}),
    opp(id="c1", title="Intro to RTOS (online course)", primary_category="skill_development",
        tags=["rtos"], produces=["certificate"], effort={"weekly_commitment": "3 h"}),
]


class TestGapModel(unittest.TestCase):
    def test_gap_comes_from_real_requirements_with_sample(self):
        gaps = GP.collect_gaps(TARGET_OPPS, EMBEDDED)
        names = {g["name"] for g in gaps}
        self.assertIn("RTOS", names)
        rtos = next(g for g in gaps if g["name"] == "RTOS")
        self.assertEqual(rtos["type"], "skill")
        self.assertIn("本轮 3 个目标机会中 2 个要求", rtos["sample"])
        self.assertEqual(rtos["source"], "requirements")
        self.assertTrue(rtos["opportunity_ids"])

    def test_gap_is_not_always_skill(self):
        """缺公开影响力 ≠ 技能不足；缺教授接触 ≠ 技术能力不足。"""
        prof = dict(EMBEDDED,
                    career_state={"promotion_target": "Senior engineer"},
                    goals=[{"type": "career", "priority": "high"}])
        gaps = GP.collect_gaps([], prof, stated_target="升 Senior")
        types = {g["type"] for g in gaps}
        self.assertIn("public_reputation", types)
        self.assertIn("leadership", types)
        self.assertNotIn("skill", types)

    def test_research_gaps_are_typed_separately(self):
        prof = dict(EMBEDDED, goals=[{"type": "education", "priority": "high"},
                                     {"type": "research", "priority": "medium"}])
        gaps = GP.collect_gaps([], prof, stated_target="申请日本硕士")
        by_type = {g["type"]: g for g in gaps}
        for t in ("research", "network", "language"):
            self.assertIn(t, by_type, f"缺少 {t} 类型缺口")
        self.assertNotEqual(by_type["research"]["name"], by_type["network"]["name"])

    def test_no_gap_without_target_or_requirements(self):
        """目标模糊时不得凭空造 Gap。"""
        gaps = GP.collect_gaps([], {"skills": [{"name": "Python"}]})
        self.assertEqual(gaps, [])


class TestBridgeOpportunity(unittest.TestCase):
    def setUp(self):
        self.gaps = GP.collect_gaps(TARGET_OPPS, EMBEDDED)
        self.rtos = next(g for g in self.gaps if g["name"] == "RTOS")

    def test_real_bridge_found_not_just_a_course(self):
        bridges = G.bridges_for_gap(self.rtos, BRIDGE_OPPS, EMBEDDED)
        self.assertTrue(bridges)
        self.assertEqual(bridges[0]["opportunity_id"], "b1")          # 公开 PR 优先
        self.assertTrue(bridges[0]["official_url"])
        cats = {b["category"] for b in bridges}
        self.assertTrue(cats & {"open_source", "competition"})

    def test_time_to_evidence_distinguishes_certificate_from_pr(self):
        pr = G.time_to_evidence(BRIDGE_OPPS[0])
        cert = G.time_to_evidence(BRIDGE_OPPS[2])
        self.assertEqual(pr["strength"], "strong")
        self.assertEqual(cert["strength"], "medium")
        self.assertIn("GitHub PR", pr["public_evidence"])

    def test_bridge_respects_same_gates(self):
        """Bridge 不降低真实性门槛：未核实/无证据的 bridge 标记 evidence_complete=False。"""
        unverified = opp(id="u1", title="FreeRTOS fork contribution", tags=["rtos"],
                         produces=["GitHub PR"], verification_status="unverified", evidence={})
        bridges = G.bridges_for_gap(self.rtos, [unverified], EMBEDDED)
        self.assertFalse(bridges[0]["evidence_complete"])

    def test_no_bridge_is_reported_honestly(self):
        report = G.gap_to_bridge_report([self.rtos], [opp(id="x", title="Nothing relevant")],
                                        EMBEDDED)
        self.assertEqual(report[0]["bridges"], [])
        self.assertEqual(report[0]["source_gap"]["reason"], "no_real_bridge_found")

    def test_bridge_graph_links_gap_to_evidence_to_goal(self):
        graph = G.bridge_graph(self.gaps, BRIDGE_OPPS, EMBEDDED, goal="Japan Embedded AI")
        kinds = {n["kind"] for n in graph["nodes"]}
        self.assertTrue({"gap", "bridge", "evidence", "goal"} <= kinds)
        self.assertTrue(graph["connected"])
        self.assertTrue(any(e["type"] == "contributes_to" for e in graph["edges"]))


class TestPortfolio(unittest.TestCase):
    def _rows(self, hours, budget="6"):
        prof = {"constraints": {"weekly_time": budget}}
        rows = [row(id=f"p{i}", title=f"P{i}", primary_category="open_source",
                    effort={"weekly_commitment": f"{h} h"}, future_optionality={"level": "high"},
                    time_to_value="months", utility="medium")
                for i, h in enumerate(hours)]
        return prof, rows

    def test_portfolio_never_exceeds_weekly_budget(self):
        prof, rows = self._rows([4, 3, 2, 1], budget="5")
        p = PF.build_portfolio(rows, prof)
        self.assertFalse(p["resource_conflict"])
        self.assertLessEqual(p["planned_hours"], 5.0)
        self.assertTrue(p["dropped"], "超出预算的项必须被丢弃并记录")

    def test_metrics_resource_conflict_rate_is_zero(self):
        prof, rows = self._rows([4, 3, 2], budget="5")
        ps = [PF.build_portfolio(rows, prof) for _ in range(3)]
        self.assertEqual(PF.metrics(ps)["portfolio_resource_conflict_rate"], 0.0)

    def test_roles_are_earned_not_padded(self):
        """只有低投入项时不得凭空空出 high_upside/bridge 栏目。"""
        prof = {"constraints": {"weekly_time": "5"}}
        rows = [row(id="tiny", title="Tiny", effort={"weekly_commitment": "1 h"},
                    primary_category="event", time_to_value="immediate")]
        p = PF.build_portfolio(rows, prof, bridges=[])
        self.assertIn("low_cost", p["roles_present"])
        self.assertNotIn("bridge", p["roles_present"])
        self.assertNotIn("high_upside", p["roles_present"])

    def test_bridge_role_comes_from_gap_bridge_result(self):
        prof = {"constraints": {"weekly_time": "6"}}
        rows = [row(id="b1", title="FreeRTOS issue", effort={"weekly_commitment": "4 h"},
                    primary_category="open_source", time_to_value="months")]
        p = PF.build_portfolio(rows, prof, bridges=[{"opportunity_id": "b1"}])
        self.assertIn("bridge", p["roles_present"])
        self.assertEqual(p["items"][0]["primary_role"], "bridge")

    def test_alternatives_而不是替用户做决定(self):
        prof, rows = self._rows([4, 3, 1, 2], budget="10")
        p = PF.build_portfolio(rows, prof)
        self.assertTrue(p["alternatives"])
        self.assertTrue(all(a["if_priority"] for a in p["alternatives"]))


class TestCaseLevelScenarios(unittest.TestCase):
    """对应需求里的 5 个测试场景。"""

    def test_case1_skill_gap_embedded_to_edge_ai(self):
        gaps = GP.collect_gaps(TARGET_OPPS, EMBEDDED)
        report = G.gap_to_bridge_report(gaps, BRIDGE_OPPS, EMBEDDED)
        covered = [r for r in report if r["bridges"]]
        self.assertTrue(covered, "技能缺口必须能找到真实 Bridge，而不是只输出课程")
        best = covered[0]["bridges"][0]
        self.assertIn(best["category"], ("open_source", "competition", "project", "research"))
        # 缺口覆盖率：技能类缺口必须有真实 Bridge（语言/材料类可能本轮找不到，如实记录）
        rate = len(covered) / len(report)
        self.assertGreaterEqual(rate, 0.5)
        skill_gaps = [r for r in report if r["gap"]["type"] == "skill"]
        self.assertTrue(skill_gaps)
        self.assertTrue(all(r["bridges"] for r in skill_gaps),
                        "技能缺口必须能找到真实 Bridge")

    def test_case2_career_capital_gap_prefers_public_roles(self):
        prof = dict(EMBEDDED, career_state={"promotion_target": "Senior", "management_intent": "low"},
                    goals=[{"type": "career", "priority": "high"}])
        gaps = GP.collect_gaps([], prof, stated_target="不跳槽，想升 Senior")
        self.assertTrue({"public_reputation", "leadership"} & {g["type"] for g in gaps})
        bridges = [opp(id="cfp", title="Conference CFP for practitioners",
                       primary_category="event", tags=["public speaking"],
                       produces=["conference talk"], effort={"weekly_commitment": "2 h"},
                       future_optionality={"level": "high"}),
                   opp(id="mnt", title="Open source maintainer pathway",
                       primary_category="open_source", tags=["maintainer"],
                       produces=["public contribution"], effort={"weekly_commitment": "3 h"})]
        out = G.bridges_for_gap(gaps[0], bridges, prof)
        self.assertTrue(out)
        self.assertTrue({b["category"] for b in out} & {"event", "open_source"})

    def test_case3_research_gap_bridges_are_different(self):
        prof = dict(EMBEDDED, goals=[{"type": "education", "priority": "high"}])
        gaps = GP.collect_gaps([], prof, stated_target="在职申请日本硕士")
        types = {g["type"] for g in gaps}
        self.assertTrue({"research", "network", "language"} <= types)
        # 不同缺口 → 不同 bridge（不应都指向同一个机会）
        pool = [opp(id="lab", title="Lab open seminar", tags=["日语", "research"],
                    primary_category="event", produces=["professor contact"]),
                opp(id="jlpt", title="JLPT preparation course", tags=["日语", "language"],
                    primary_category="language", produces=["certificate"])]
        r1 = {b["opportunity_id"] for b in G.bridges_for_gap(
            next(g for g in gaps if g["type"] == "research"), pool, prof)}
        r2 = {b["opportunity_id"] for b in G.bridges_for_gap(
            next(g for g in gaps if g["type"] == "language"), pool, prof)}
        self.assertNotEqual(r1, r2)

    def test_case4_resource_conflict_with_5h_budget(self):
        prof = {"constraints": {"weekly_time": "5"}}
        rows = [row(id="a", effort={"weekly_commitment": "5 h"}, utility="high"),
                row(id="b", effort={"weekly_commitment": "4 h"}, utility="medium"),
                row(id="c", effort={"weekly_commitment": "3 h"}, utility="low")]
        p = PF.build_portfolio(rows, prof)
        self.assertLessEqual(p["planned_hours"], 5.0)
        self.assertFalse(p["resource_conflict"])

    def test_case5_vague_goal_no_fake_goal(self):
        prof = {"skills": [{"name": "Python"}], "constraints": {"remote": True}}
        gaps = GP.collect_gaps([], prof)
        self.assertEqual(gaps, [], "目标模糊时不得伪造 Goal/Gap")
        rows = [row(id="lc", effort={"weekly_commitment": "1 h"}, time_to_value="immediate"),
                row(id="ex", layer="explore", novelty=85, effort={"weekly_commitment": "2 h"}),
                row(id="hu", future_optionality={"level": "high"},
                    effort={"weekly_commitment": "3 h"})]
        p = PF.build_portfolio(rows, prof)
        self.assertTrue(p["roles_present"])
        self.assertNotIn("bridge", p["roles_present"])   # 没有 gap 就没有 bridge 角色
        self.assertTrue({"low_cost", "explore"} & set(p["roles_present"]))

    def test_case_end_to_end_embedded_to_edge_ai(self):
        """端到端：Gap → Bridge → Portfolio（受 6h/周约束）。"""
        gaps = GP.collect_gaps(TARGET_OPPS, EMBEDDED)
        report = G.gap_to_bridge_report(gaps, BRIDGE_OPPS, EMBEDDED)
        bridges = [b for r in report for b in r["bridges"]]
        self.assertTrue(bridges)
        scored = S.score_all(EMBEDDED, BRIDGE_OPPS, today=TODAY)
        p = PF.build_portfolio(scored["results"], EMBEDDED, bridges)
        self.assertFalse(p["resource_conflict"])
        self.assertLessEqual(p["planned_hours"], 6.0)
        self.assertIn("bridge", p["roles_present"])
        # 指标
        m = PF.metrics([p])
        self.assertEqual(m["portfolio_resource_conflict_rate"], 0.0)
        self.assertGreaterEqual(m["portfolio_diversity_avg_roles"], 1)


if __name__ == "__main__":
    unittest.main()
