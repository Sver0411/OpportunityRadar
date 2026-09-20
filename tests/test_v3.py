"""V3 P0 模块测试：readiness / graph / coverage / utility。

原则：这些是**确定性**逻辑，必须可回归；语义判断（扩词、机会关系推断）仍交给模型。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import readiness as R      # noqa: E402
import graph as G          # noqa: E402
import coverage as COV     # noqa: E402
import utility as U        # noqa: E402
from common import (CAREER_STAGES, LIFE_STAGES, OUTCOME_FACETS,  # noqa: E402
                    READINESS_STATUSES, CAPITAL_DIMS, INTENTS)


PRO_WORKER = {
    "life_stage": ["working"],
    "career_stage": ["early_career", "career_switcher"],
    "employment": {"status": "full_time", "function": "engineering", "years_of_experience": 3},
    "career_state": {"target_role": "Edge AI engineer", "switch_intent": "high"},
    "decision_preferences": {"prefer_public_output": "high", "prefer_low_commitment": "high"},
    "dealbreakers": ["无薪长期实习", "每周超过 15 小时"],
    "green_lights": ["有公开作品"],
    "skills": [{"name": "C"}, {"name": "Embedded C"}],
    "constraints": {"preferred_country": ["Japan"], "remote": True, "weekly_time": "6"},
    "goals": [{"type": "skill", "priority": "high"}],
}


def opp(**kw):
    base = {"id": "o1", "title": "Edge AI open-source programme",
            "primary_category": "open_source", "official_url": "https://oss.example"}
    base.update(kw)
    return base


class TestReadiness(unittest.TestCase):
    def test_ready_when_prereq_matches_skills(self):
        o = opp(prerequisites=["C"], required_materials=[])
        r = R.readiness(o, PRO_WORKER)
        self.assertEqual(r["status"], "ready_now")
        self.assertTrue(any("C" in x for x in r["ready_items"]))

    def test_missing_prereq_creates_preparation(self):
        o = opp(prerequisites=["Git"], required_materials=["motivation letter"])
        r = R.readiness(o, PRO_WORKER)
        self.assertIn(r["status"], ("minor_preparation", "short_preparation"))
        self.assertEqual(r["blockers"], [])

    def test_weekly_time_conflict_is_blocker_not_ineligible(self):
        """时间冲突 → blocker（不是 Ineligible），且标记为 heavy commitment conflict。"""
        o = opp(effort={"weekly_commitment": "20 h/week"})
        r = R.readiness(o, PRO_WORKER)
        self.assertEqual(r["status"], "blocked")
        self.assertTrue(any("时间冲突" in b for b in r["blockers"]))

    def test_dealbreaker_marks_blocker(self):
        o = opp(summary="无薪长期实习，需要全程参与")
        r = R.readiness(o, PRO_WORKER)
        self.assertEqual(r["status"], "blocked")
        self.assertTrue(any("dealbreaker" in b for b in r["blockers"]))

    def test_unknown_when_nothing_to_compare(self):
        r = R.readiness(opp(), {})
        self.assertEqual(r["status"], "unknown")

    def test_status_values_are_from_enum(self):
        r = R.readiness(opp(), PRO_WORKER)
        self.assertIn(r["status"], READINESS_STATUSES)


class TestGraph(unittest.TestCase):
    def test_nodes_carry_produces_and_unlocks(self):
        o = opp(produces=["GitHub PR"], unlocks=[{"type": "edge_ai_role", "label": "Edge AI 岗位"}])
        g = G.build_graph([o])
        node = g["nodes"][0]
        self.assertEqual(node["produces"], ["GitHub PR"])
        self.assertEqual(node["unlocks"][0]["type"], "edge_ai_role")

    def test_no_fabricated_opportunity_id(self):
        """未发现的后续机会：opportunity_id 必须为 null，不得编造。"""
        o = opp(unlocks=[{"type": "unknown_future_thing"}])
        g = G.build_graph([o])
        self.assertIsNone(g["nodes"][0]["unlocks"][0]["opportunity_id"])

    def test_links_real_opportunity_when_present(self):
        a = opp(id="a", unlocks=[{"type": "career", "opportunity_id": "b"}])
        b = opp(id="b", primary_category="career", title="Edge AI role")
        g = G.build_graph([a, b])
        self.assertTrue(any(e["from"] == "a" and e["to"] == "b" for e in g["edges"]))

    def test_gap_to_bridge_prefers_low_commitment_public_output(self):
        bridge = opp(id="bridge", title="Edge AI contribution",
                     produces=["GitHub PR"],
                     unlocks=[{"type": "edge_ai_role"}],
                     effort={"weekly_commitment": "4-6 h"})
        heavy = opp(id="heavy", title="Edge AI bootcamp",
                    produces=["certificate"],
                    unlocks=[{"type": "course"}],
                    effort={"weekly_commitment": "25 h/week"})
        res = G.bridges_for_gap("Edge AI", [heavy, bridge])
        self.assertTrue(res)
        self.assertEqual(res[0]["id"], "bridge")
        self.assertTrue(res[0]["public_output"])

    def test_gap_without_bridge_is_honest(self):
        report = G.gap_to_bridge_report(["Quantum knitting"], [opp()])
        self.assertEqual(report[0]["bridges"], [])


class TestCoverage(unittest.TestCase):
    def setUp(self):
        self.cov = COV.Coverage()
        self.cov.record("Japan", "ja", "research", None, 4, 9, 3)
        self.cov.record("Japan", "ja", "career", None, 1, 2, 0)

    def test_depth_classification(self):
        self.assertEqual(COV.Coverage.depth(4), "deep")
        self.assertEqual(COV.Coverage.depth(2), "medium")
        self.assertEqual(COV.Coverage.depth(1), "shallow")

    def test_totals_and_regions(self):
        self.assertEqual(self.cov.totals()["queries"], 5)
        self.assertIn("Japan", self.cov.by_region())

    def test_statement_does_not_claim_complete_scan(self):
        s = self.cov.natural_language()
        self.assertIn("不是全互联网完整扫描", s)
        self.assertNotIn("搜遍", s)

    def test_empty_coverage_is_honest(self):
        self.assertIn("没有记录", COV.Coverage().natural_language())


class TestUtility(unittest.TestCase):
    def test_output_is_band_not_score(self):
        o = opp(outcomes={"portfolio": "high", "skill": "high"},
                prerequisites=["C"], effort={"weekly_commitment": "4-6 h"},
                time_to_value="months",
                future_optionality={"level": "high"})
        u = U.personal_utility(o, PRO_WORKER)
        self.assertIn(u["band"], ("high", "medium", "low", "unknown"))
        self.assertTrue(u["reasons"])

    def test_ineligible_or_blocked_is_low(self):
        o = opp(effort={"weekly_commitment": "20 h/week"})
        u = U.personal_utility(o, PRO_WORKER)
        self.assertEqual(u["band"], "low")

    def test_unknown_when_no_outcomes_and_no_verdict(self):
        u = U.personal_utility(opp(), {})
        self.assertEqual(u["band"], "unknown")

    def test_utility_differs_from_match_concept(self):
        """同一个机会：高 Match 但投入过大 → Utility 不应为 high（概念必须分离）。"""
        o = opp(outcomes={"skill": "high"}, prerequisites=["C"],
                effort={"weekly_commitment": "20 h/week"})
        u = U.personal_utility(o, PRO_WORKER)
        self.assertNotEqual(u["band"], "high")
        self.assertIn(("heavy_commitment_conflict" if False else "blocked"), [u["readiness"]["status"]])

    def test_no_probability_language(self):
        o = opp(outcomes={"career": "high"})
        u = U.personal_utility(o, PRO_WORKER)
        blob = json.dumps(u, ensure_ascii=False).lower()
        for banned in ("录取率", "录取概率", "admission rate", "acceptance rate"):
            self.assertNotIn(banned, blob)


class TestV3Enums(unittest.TestCase):
    def test_new_enums_available(self):
        self.assertIn("early_career", CAREER_STAGES)
        self.assertIn("career_switcher", CAREER_STAGES)
        self.assertIn("studying_and_working", LIFE_STAGES)
        self.assertEqual(len(OUTCOME_FACETS), 13)
        self.assertEqual(len(CAPITAL_DIMS), 8)
        self.assertIn("unknown_unknowns", INTENTS)

    def test_old_profile_json_still_valid(self):
        """兼容性：老 profile（无 V3 字段）必须仍能跑 readiness/utility。"""
        old = {"skills": [{"name": "Python"}], "constraints": {"remote": True}}
        r = R.readiness(opp(), old)
        u = U.personal_utility(opp(), old)
        self.assertIn(r["status"], READINESS_STATUSES)
        self.assertIn(u["band"], ("high", "medium", "low", "unknown"))



class TestP0FixesFromCDE(unittest.TestCase):
    """C/D/E 验收发现的 P0 缺陷回归（修复于 V3 P0 收尾）。"""

    def test_outcome_facet_lifts_goal_fit_across_categories(self):
        """CFP 属 event，但产出 network=high 命中 networking 目标 → 不得判为"不重合"。"""
        import score as S
        prof = {"goals": [{"type": "networking", "priority": "high"}]}
        cfp = opp(primary_category="event",
                  outcomes={"network": "high", "reputation": "high"})
        score, note = S.goal_component(cfp, prof)
        self.assertGreaterEqual(score, 60)
        self.assertIn("network", note)
        plain_event = opp(primary_category="event")          # 没有 outcomes → 仍然不重合
        self.assertLess(S.goal_component(plain_event, prof)[0], 60)

    def test_professional_interest_aliases_exist(self):
        """验收发现 open_source / networking / public_speaking 完全缺失，导致 CFP/开源匹配为 0。"""
        from common import INTEREST_ALIASES
        for key in ("open_source", "networking", "public_speaking"):
            with self.subTest(key=key):
                self.assertIn(key, INTEREST_ALIASES)

    def test_utility_can_qualify_recommendation(self):
        """渐进式画像下 match 可能 < 55；Utility=high 时仍可进主推荐（否则主推荐区不可达）。"""
        import score as S
        row = {"freshness": {"status": "open"}, "official_url": "https://x.example",
               "verdict": "Eligible", "match": 48, "utility": "high",
               "verification_status": "verified_official",
               "application_status_evidence": True,
               "evidence_complete": True, "actionable": True}
        self.assertEqual(S.recommendation_zone(row), "recommended_now")
        row["utility"] = "medium"
        self.assertEqual(S.recommendation_zone(row), "worth_verifying")

    def test_recommended_now_requires_evidence_structure(self):
        """P0：verified_official 但缺 evidence.application_status → 不能被认证为可申请。"""
        import score as S
        base = opp(verification_status="verified_official", deadline="2026-11-15",
                   official_url="https://x.example")
        self.assertFalse(S.actionable_evidence(base, dt.date(2026, 9, 20)))
        base["evidence"] = {"application_status": {"status": "explicit",
                                                   "source_url": "https://x.example",
                                                   "verified_at": "2026-09-20"}}
        self.assertTrue(S.actionable_evidence(base, dt.date(2026, 9, 20)))

    def test_effort_and_cost_accept_both_shapes(self):
        """真实验收里 effort/cost 既可能是对象也可能是字符串。"""
        import readiness as R
        import utility as U
        self.assertEqual(R.effort_of({"effort": "6-8 h/week"}), {"weekly_commitment": "6-8 h/week"})
        self.assertEqual(R.effort_of({"effort": {"weekly_commitment": "4 h"}}),
                         {"weekly_commitment": "4 h"})
        u = U.personal_utility(opp(cost="free", outcomes={"skill": "high"}), PRO_WORKER)
        self.assertIn(u["band"], ("high", "medium", "low", "unknown"))



class TestDemotionClassification(unittest.TestCase):
    """区分三类失败：漏记证据(process) / 页面无法确认或没去核实(process) / 官网打不开(infrastructure)。"""

    def _reason(self, opp_kw, row=None, evc=None):
        import evidence as EV
        base = opp(**opp_kw)
        evc = evc or EV.check(base, dt.date(2026, 9, 20))
        row = row or {"freshness": {"status": "open"}, "conflicts": []}
        return EV.demotion_reason(base, row, evc)

    def test_missing_official_source_is_process(self):
        r = self._reason({"official_url": None}, evc={"missing": ["official_url"]})
        self.assertEqual(r["code"], "no_canonical_source")
        self.assertEqual(r["kind"], "process")

    def test_not_attempted_vs_blocked(self):
        not_tried = self._reason({"official_url": "https://x.example",
                                  "verification_status": "unverified"})
        self.assertEqual(not_tried["code"], "verification_not_attempted")
        self.assertEqual(not_tried["kind"], "process")
        blocked = self._reason({"official_url": "https://x.example",
                                "verification_status": "unverified",
                                "notes": "fetch blocked (403 / captcha)"})
        self.assertEqual(blocked["code"], "page_not_verifiable")
        self.assertEqual(blocked["kind"], "infrastructure")

    def test_page_cannot_confirm_is_fact(self):
        import evidence as EV
        # 已核实过官方页、但页面本身不写当前状态 → fact
        o = opp(deadline=None, title="Some programme", verification_status="verified_official")
        evc = EV.check(o, dt.date(2026, 9, 20))
        r = EV.demotion_reason(o, {"freshness": {"status": "unknown"}, "conflicts": []}, evc)
        self.assertEqual(r["code"], "page_cannot_confirm")
        self.assertEqual(r["kind"], "fact")


if __name__ == "__main__":
    unittest.main()
