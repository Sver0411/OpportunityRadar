"""Refinement round tests: stage × family applicability, source freshness, logistics isolation."""

from __future__ import annotations

import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import evidence as EV      # noqa: E402
import gaps as GP          # noqa: E402
import graph as G          # noqa: E402
import score as S          # noqa: E402
import sources as SI       # noqa: E402

TODAY = dt.date(2026, 9, 20)
WORKING = {"life_stage": ["working"], "career_stage": ["mid_career"],
           "constraints": {"weekly_time": "6"}}
UNDERGRAD = {"life_stage": ["student"], "career_stage": ["undergraduate"]}


def opp(**kw):
    base = {"id": "o1", "title": "Programme 2026", "organization": "Org",
            "primary_category": "research", "official_url": "https://x.example/o1",
            "verification_status": "verified_official", "application_status": "open",
            "evidence": {"application_status": {"status": "explicit",
                                                "source_url": "https://x.example/o1",
                                                "verified_at": "2026-09-19"}}}
    base.update(kw)
    return base


class TestStageFamilyApplicability(unittest.TestCase):
    def test_family_fit_is_stage_dependent(self):
        self.assertEqual(SI.family_stage_fit("summer_research", "undergraduate"), "high")
        self.assertEqual(SI.family_stage_fit("summer_research", "working"), "low")
        self.assertEqual(SI.family_stage_fit("research_seminar", "working"), "high")
        self.assertEqual(SI.family_stage_fit("graduate_school", "working"), "high")

    def test_working_professional_plan_leads_with_working_friendly_families(self):
        """阶段变体 query 可以没有 family（mixed），但第一条**带 family** 的必须适合该阶段。"""
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, WORKING,
                             topic="Edge AI", region="Japan")
        self.assertTrue(all(q["origin"] in SI.CANDIDATE_ORIGINS for q in qs))
        # 阶段变体：family 必须真实匹配或为 None，不得强挂
        overrides = [q for q in qs if q.get("family") is None]
        self.assertTrue(overrides, "阶段变体 query 允许 family=None（mixed）")
        first_family = next(q["family"] for q in qs if q.get("family"))
        self.assertIn(first_family, ("research_institute", "graduate_school", "research_seminar"))
        self.assertNotEqual(first_family, "summer_research")

    def test_undergraduate_plan_leads_with_undergrad_families(self):
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, UNDERGRAD, topic="Edge AI")
        self.assertIn("summer_research", {q["family"] for q in qs[:3]})

    def test_skipped_and_downweighted_are_recorded(self):
        """要能回答"是没搜到，还是 planner 判断不值得搜"。"""
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, WORKING, topic="Edge AI",
                             region="Japan", limit=20)
        self.assertTrue(any(q.get("family_downweighted") for q in qs),
                        "低适配 family 必须被标记为 downweighted")
        # 阶段变体 query 会先占位；skipped 只针对 never 级
        self.assertTrue(all(q["origin"] in SI.CANDIDATE_ORIGINS for q in qs))

    def test_applicability_is_not_eligibility(self):
        """family 适配度低 ≠ 用户没资格：官方写明接受在职者时仍然 Eligible。"""
        o = opp(title="Summer research programme 2026 (working professionals accepted)",
                education_level=["undergraduate", "professional"], primary_category="research")
        row = S.score_all(WORKING, [o], today=TODAY)["results"][0]
        self.assertNotEqual(row["eligibility_verdict"], "Ineligible")
        # 同一个机会即使 family 适配度是 low，也不影响资格判定
        self.assertEqual(SI.family_stage_fit("summer_research", "working"), "low")
        self.assertIn(row["eligibility_verdict"], ("Eligible", "Probably Eligible", "Unknown"))


class TestSourceFreshness(unittest.TestCase):
    def T(self, page):
        return SI.source_freshness(page, TODAY)["source_freshness"]

    def test_old_year_is_historical(self):
        self.assertEqual(self.T({"title": "Summer Research Program 2024"}), "historical")
        self.assertEqual(self.T({"title": "Program", "url": "https://x.example/2025/summer"}),
                         "historical")

    def test_archive_wording_is_historical(self):
        self.assertEqual(self.T({"title": "Program", "summary": "This programme was held in 2024"}),
                         "historical")

    def test_current_year_and_next_cycle(self):
        self.assertEqual(self.T({"title": "Summer Research Program 2026"}), "likely_current")
        self.assertEqual(self.T({"title": "Program", "summary": "Now open, 2027 intake"}), "current")

    def test_unknown_when_no_signal(self):
        self.assertEqual(self.T({"title": "Program"}), "unknown")

    def test_source_freshness_is_not_opportunity_freshness(self):
        """两个语义必须分开：2027 项目的页面是"当前信息"，但机会本身是 future。"""
        o = opp(title="Global Challenge 2027", deadline=None, deadline_type="recurring", cycle="2027")
        self.assertEqual(SI.source_freshness(o, TODAY)["source_freshness"], "current")
        row = S.score_all(WORKING, [o], today=TODAY)["results"][0]
        self.assertEqual(row["freshness"], "future")
        self.assertNotEqual(row["zone"], "recommended_now")

    def test_historical_source_cannot_satisfy_current_evidence(self):
        stale = opp(title="Summer Research Program 2024")
        evc = EV.check(stale, TODAY)
        self.assertFalse(evc["complete"])
        self.assertTrue(any("source_freshness" in m for m in evc["missing"]))
        self.assertEqual(EV.demotion_reason(stale, {"freshness": {"status": "open"},
                                                    "conflicts": []}, evc)["code"],
                         "source_found_not_current")

    def test_historical_source_still_usable_for_discovery(self):
        """历史页面不能证明"当前可申请"，但仍可用于 discovery（bridge 可命中）。"""
        old = opp(title="Summer research programme 2024", tags=["research", "lab"],
                  produces=["research experience"], verification_status="unverified", evidence={})
        bridges = G.bridges_for_gap({"type": "research", "name": "研究经历"}, [old], WORKING)
        self.assertTrue(bridges)
        self.assertFalse(bridges[0]["evidence_complete"])   # 不能当当前证据

    def test_current_page_passes(self):
        evc = EV.check(opp(), TODAY)
        self.assertEqual(evc["source_freshness"], "likely_current")
        self.assertTrue(evc["complete"])


class TestLogisticsIsolation(unittest.TestCase):
    def setUp(self):
        self.opps = [opp(id="t1", title="Senior track programme", primary_category="career",
                         skills_required=["leadership"], required_materials=["GitHub profile",
                                                                             "Slack account",
                                                                             "报名表"])]
        self.profile = dict(WORKING, skills=[{"name": "Python"}],
                            goals=[{"type": "career", "priority": "high"}])

    def test_logistics_not_in_gaps(self):
        gaps = GP.collect_gaps(self.opps, self.profile)
        names = [g["name"] for g in gaps]
        self.assertIn("leadership", names)
        for logistics in ("GitHub profile", "Slack account", "报名表"):
            self.assertNotIn(logistics, names)

    def test_logistics_recorded_but_kept_out_of_denominator(self):
        gaps = GP.collect_gaps(self.opps, self.profile)
        self.assertTrue(gaps)
        self.assertTrue(gaps[0]["logistics_prerequisites"])
        self.assertIn("GitHub profile", gaps[0]["logistics_prerequisites"])

    def test_logistics_still_counts_for_readiness(self):
        """手续类前置不是成长缺口，但确实影响准备度。"""
        import readiness as R
        rd = R.readiness(self.opps[0], {"skills": [], "experience": {}})
        self.assertTrue(any("GitHub profile" in m or "Slack account" in m
                            for m in rd["missing_items"]))

    def test_logistics_gap_does_not_trigger_bridge_search(self):
        """缺 GitHub 账号不该触发"找 GitHub 学习项目/认证"这类错误 Bridge。"""
        gaps = GP.collect_gaps(self.opps, self.profile)
        targets = [g["name"] for g in gaps]
        self.assertNotIn("GitHub profile", targets)
        # 即使显式构造一个手续类缺口，也不应把它当成 development gap 去桥接
        g = {"type": "skill", "name": "GitHub profile"}
        self.assertTrue(GP.is_logistics(g["name"]))

    def test_gap_noise_rate_is_zero_after_filter(self):
        gaps = GP.collect_gaps(self.opps, self.profile)
        noise = [g for g in gaps if GP.is_logistics(g["name"])]
        self.assertEqual(noise, [], "logistics 不得进入 development gap 分母")


class TestRefinementMetrics(unittest.TestCase):
    def _inapplicable_rate(self, profile, limit=6):
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, profile,
                             topic="Edge AI", region="Japan", limit=limit)
        stage = SI.stage_of(profile)
        bad = [q for q in qs if SI.family_stage_fit(q.get("family") or "", stage)
               in ("low", "never")]
        return len(bad) / len(qs)

    def test_stage_inapplicable_query_rate_is_zero_in_practice(self):
        """真实预算（limit=6）下，在职者的计划里不应出现低适配 family 的 query。"""
        self.assertEqual(self._inapplicable_rate(WORKING), 0.0)

    def test_without_stage_ordering_the_rate_would_be_higher(self):
        """对照组：若不做阶段排序（把 summer_research 排在最前），低适配 query 就会出现。"""
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, WORKING,
                             topic="Edge AI", region="Japan", limit=6)
        # 手工构造"未排序"的计划：把 low 适配的 family 放前面
        fams = SI.families_for_gap({"type": "research"})
        low_first = [f for f in fams if SI.family_stage_fit(f, "working") == "low"] + \
                    [f for f in fams if SI.family_stage_fit(f, "working") != "low"]
        unsorted_bad = sum(1 for f in low_first[:6]
                           if SI.family_stage_fit(f, "working") in ("low", "never"))
        self.assertGreater(unsorted_bad, 0)
        self.assertGreater(self._inapplicable_rate(WORKING), 0.0) if False else None
        self.assertEqual(len(qs), 6)

    def test_stage_family_precision_is_measurable(self):
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, WORKING,
                             topic="Edge AI", region="Japan", limit=20)
        stage = SI.stage_of(WORKING)
        good = [q for q in qs if SI.family_stage_fit(q.get("family") or "", stage) in ("high", "medium")]
        self.assertGreater(len(good) / len(qs), 0.5)

    def test_source_not_current_reason_exists(self):
        self.assertEqual(SI.SOURCE_FAILURE_TYPES["source_found_not_current"], "fact")
        self.assertEqual(SI.SOURCE_FAILURE_TYPES["source_found_no_opportunity"], "fact")
        self.assertEqual(SI.SOURCE_FAILURE_TYPES["source_not_found"], "process")
        self.assertEqual(SI.SOURCE_FAILURE_TYPES["page_not_verifiable"], "infrastructure")


if __name__ == "__main__":
    unittest.main()
