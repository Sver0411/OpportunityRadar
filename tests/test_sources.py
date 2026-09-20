"""Minimal source-intelligence tests: gap → bridge intent → source family → queries."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import sources as SI  # noqa: E402

WORKING = {"life_stage": ["working"], "career_stage": ["mid_career"],
           "constraints": {"preferred_country": ["Japan"]}}
UNDERGRAD = {"life_stage": ["student"], "career_stage": ["undergraduate"]}


class TestGapToFamily(unittest.TestCase):
    def test_gap_types_map_to_different_families(self):
        research = SI.families_for_gap({"type": "research", "name": "研究经历"})
        network = SI.families_for_gap({"type": "network", "name": "教授接触"})
        language = SI.families_for_gap({"type": "language", "name": "JLPT N2"})
        portfolio = SI.families_for_gap({"type": "portfolio", "name": "公开产出"})
        self.assertTrue({"summer_research", "research_institute"} & set(research))
        self.assertIn("research_seminar", network)
        self.assertIn("official_exam_body", language)
        self.assertIn("contributor_guide", portfolio)
        # 四类缺口不应共用同一组 family
        self.assertNotEqual(set(research), set(network))
        self.assertNotEqual(set(network), set(language))

    def test_gap_never_maps_directly_to_a_query_string(self):
        """必须经过 Bridge Intent 层，否则 Source Intelligence 没发挥作用。"""
        for gap_type in ("research", "language", "portfolio", "leadership"):
            with self.subTest(gap_type=gap_type):
                intent = SI.bridge_intent_for({"type": gap_type})
                self.assertIn(intent, SI.GAP_TO_BRIDGE_INTENT.values())
                self.assertTrue(SI.INTENT_TO_FAMILIES.get(intent))


class TestStageAwareness(unittest.TestCase):
    def test_working_professional_gets_non_student_queries(self):
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, WORKING, topic="Edge AI",
                             region="Japan")
        joined = " ".join(q["query"].lower() for q in qs)
        self.assertTrue(any(k in joined for k in ("working professionals", "part-time",
                                                  "industry-academia", "社会人")))
        self.assertNotIn("undergraduate", joined)

    def test_undergraduate_gets_student_queries(self):
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, UNDERGRAD, topic="Edge AI")
        joined = " ".join(q["query"].lower() for q in qs)
        self.assertTrue(any(k in joined for k in ("undergraduate", "summer research")))

    def test_stage_detection(self):
        self.assertEqual(SI.stage_of(WORKING), "working")
        self.assertEqual(SI.stage_of(UNDERGRAD), "undergraduate")
        self.assertEqual(SI.stage_of({}), "unknown")


class TestNoWhitelist(unittest.TestCase):
    def test_every_planned_query_has_provenance(self):
        qs = SI.plan_queries({"type": "portfolio", "name": "公开产出"}, WORKING, topic="Zephyr")
        self.assertTrue(qs)
        for q in qs:
            self.assertIn(q["origin"], SI.CANDIDATE_ORIGINS)

    def test_unknown_gap_falls_back_to_general_search(self):
        """registry 没有对应 family 时，仍然给出 general search（不是白名单）。"""
        qs = SI.plan_queries({"type": "skill", "name": "量子纺织"}, WORKING)
        self.assertTrue(qs)
        self.assertTrue(any(q["origin"] in ("general_search", "source_family_query") for q in qs))

    def test_registry_reports_itself_as_seed_only(self):
        cov = SI.registry_coverage()
        self.assertGreater(cov["families"], 0)
        self.assertIn("不会被排除", cov["note"])

    def test_ecosystem_is_domain_driven_not_hardcoded(self):
        """同一个 family 用不同 topic 生成不同 query（不写死 CNCF 之类）。"""
        a = SI.plan_queries({"type": "portfolio", "name": "x"}, WORKING, topic="Zephyr (RTOS)")[0]["query"]
        b = SI.plan_queries({"type": "portfolio", "name": "x"}, WORKING, topic="OpenSSF")[0]["query"]
        self.assertNotEqual(a, b)


class TestYieldState(unittest.TestCase):
    def test_record_yield_is_lightweight_and_local(self):
        with tempfile.TemporaryDirectory() as d:
            e1 = SI.record_yield(d, "https://lab.example", category="research", region="Japan",
                                 outcome="actionable")
            e2 = SI.record_yield(d, "https://jobboard.example", category="career",
                                 failure_type="source_found_no_opportunity")
            self.assertEqual(e1["historical_yield"], 1)
            self.assertEqual(e2["historical_yield"], 0)
            self.assertEqual(e2["failure_type"], "source_found_no_opportunity")
            data = json.load(open(os.path.join(d, "sources.json"), encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 2)
            # 只存轻量元数据，不存内容
            self.assertNotIn("content", json.dumps(data))

    def test_failure_types_map_to_three_kinds(self):
        for name, kind in SI.SOURCE_FAILURE_TYPES.items():
            with self.subTest(failure=name):
                self.assertIn(kind, ("process", "fact", "infrastructure"))


if __name__ == "__main__":
    unittest.main()
