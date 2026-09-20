"""Gap 相关性判据：先判相关度，再决定要不要为它花 Bridge 搜索预算。"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import gaps as GP    # noqa: E402
import graph as G    # noqa: E402

PROMOTION = {"life_stage": ["working"], "career_stage": ["mid_career"],
             "career_state": {"promotion_target": "Senior backend engineer"},
             "goals": [{"type": "career", "priority": "high"}]}
SWITCH = {"life_stage": ["working"], "career_state": {"target_role": "Edge AI engineer",
                                                      "switch_intent": "high"},
          "goals": [{"type": "skill", "priority": "high"}]}
VAGUE = {"life_stage": ["working"]}


def gaps_for(profile, opps):
    return GP.collect_gaps(opps, profile)


class TestGapRelevance(unittest.TestCase):
    def test_direction_is_derived_from_goal_and_career_state(self):
        self.assertEqual(GP.career_direction(PROMOTION), "promotion")
        self.assertEqual(GP.career_direction(SWITCH), "switch")
        self.assertEqual(GP.career_direction(VAGUE), "explore")

    def test_academic_gap_is_contextual_for_a_promotion_goal(self):
        """后端工程师想升 Senior：research / 教授接触不得成为 core_gap。"""
        opps = [{"id": "t1", "title": "Senior track", "primary_category": "career",
                 "skills_required": ["research", "professor contact", "ownership"]}]
        gaps = gaps_for(PROMOTION, opps)
        by_name = {g["name"]: g["relevance"]["relevance"] for g in gaps}
        self.assertEqual(by_name.get("research"), "contextual_gap")
        self.assertEqual(by_name.get("professor contact"), "contextual_gap")
        self.assertIn(by_name.get("ownership"), ("supporting_gap", "core_gap"))

    def test_skill_gap_is_core_when_repeated_and_hard(self):
        """Embedded → Edge AI：多个目标机会都硬性要求 TinyML → core_gap。"""
        opps = [{"id": "t1", "title": "Edge AI internship", "primary_category": "career",
                 "skills_required": ["TinyML"]},
                {"id": "t2", "title": "Edge AI project", "primary_category": "project",
                 "skills_required": ["TinyML"]}]
        gaps = gaps_for(SWITCH, opps)
        tiny = next(g for g in gaps if g["name"] == "TinyML")
        self.assertEqual(tiny["relevance"]["relevance"], "core_gap")
        self.assertEqual(tiny["relevance"]["direction"], "switch")
        self.assertIn("硬要求", tiny["relevance"]["reason"])

    def test_vague_goal_never_produces_core_gap(self):
        opps = [{"id": "t1", "title": "Anything", "primary_category": "career",
                 "skills_required": ["leadership", "research", "TinyML"]},
                {"id": "t2", "title": "Anything 2", "primary_category": "career",
                 "skills_required": ["leadership", "research", "TinyML"]}]
        gaps = gaps_for(VAGUE, opps)
        self.assertTrue(gaps)
        self.assertTrue(all(g["relevance"]["relevance"] == "contextual_gap" for g in gaps))
        self.assertEqual(GP.development_gaps(gaps), [])

    def test_bridge_search_skips_contextual_by_default(self):
        opps = [{"id": "t1", "title": "Senior track", "primary_category": "career",
                 "skills_required": ["research", "ownership"]}]
        gaps = gaps_for(PROMOTION, opps)
        report = G.gap_to_bridge_report(gaps, [{"id": "lab", "title": "Research lab seminar",
                                                "primary_category": "research",
                                                "tags": ["research", "professor"]}], PROMOTION)
        # contextual 的 research 缺口默认不进入 Bridge 搜索
        self.assertNotIn("research", [r["gap"]["name"] for r in report])
        included = G.gap_to_bridge_report(gaps, [{"id": "lab", "title": "Research lab seminar",
                                                  "primary_category": "research"}], PROMOTION,
                                          include_contextual=True)
        self.assertIn("research", [r["gap"]["name"] for r in included])

    def test_summary_reports_relevance_split(self):
        opps = [{"id": "t1", "title": "Senior track", "primary_category": "career",
                 "skills_required": ["research", "ownership"]}]
        summary = GP.gap_summary(gaps_for(PROMOTION, opps))
        self.assertIn("by_relevance", summary)
        self.assertIn("development_gaps", summary)
        self.assertEqual(sum(summary["by_relevance"].values()), summary["total"])


if __name__ == "__main__":
    unittest.main()
