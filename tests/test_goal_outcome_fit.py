"""P1-1 修复的验收测试（§6）：Goal × Outcome Facets 必须"修好跨类别价值，又不误抬无关机会"。

背景（独立验证复现）：`score.goal_component` 的 outcome 分支拿 **GOAL_TO_CATEGORY 的类别名**
当 facet 名去查 `outcomes`，目标 `career` 只会读 `outcomes["career"]` —— 于是治理席位 / 技术委员会
这类"升 Senior 最该做的机会"永远拿 15 分地板，match 卡在 55 门槛下方。
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import common as C      # noqa: E402
import presentation as P  # noqa: E402
import score as S       # noqa: E402

TODAY = dt.date(2026, 9, 21)
FLOOR = 15.0            # "与声明的目标不重合"地板

PROMO = {"life_stage": ["working"], "career_stage": ["early_career"],
         "skills": [], "interests": [],
         "constraints": {"weekly_time": "5"},
         "career_state": {"promotion_target": "Senior", "switch_intent": "low"},
         "goals": [{"type": "career", "priority": "high"}]}

D_PROFILE = {"life_stage": ["working"], "constraints": {"weekly_time": "6"},
             "goals": [{"type": "skill", "priority": "high"}]}

B_PROFILE = {"life_stage": ["working"], "constraints": {"preferred_country": ["Japan"]},
             "goals": [{"type": "education", "priority": "high"}]}


def opp(**kw):
    base = {"id": "o", "title": "t", "organization": "org", "trust_tier": "A",
            "primary_category": "networking", "verification_status": "verified_official",
            "official_url": "https://example.org/x", "application_status": "rolling",
            "evidence": {"application_status": {"status": "explicit",
                                                "source_url": "https://example.org/x",
                                                "verified_at": "2026-09-21"}}}
    base.update(kw)
    return base


class TestPositiveCases(unittest.TestCase):
    def test_technical_committee_reaches_promotion_fit(self):
        """正例 1：技术委员会（reputation/network/management 高）→ goal_fit 明显提高。"""
        row = opp(primary_category="networking",
                  outcomes={"reputation": "high", "network": "high", "management": "high",
                            "career": "medium"})
        gf, note = S.goal_component(row, PROMO)
        self.assertGreater(gf, FLOOR * 2, f"应显著高于地板，实际 {gf}")
        self.assertNotIn("不重合", note)

    def test_maintainer_path_becomes_a_mainline_candidate(self):
        """正例 2：maintainer 路径 + 公开声誉/ownership → 应能达到主推荐门槛（match ≥ 55）。"""
        row = opp(id="m", primary_category="open_source",
                  outcomes={"reputation": "high", "portfolio": "high", "management": "high"},
                  deadline_type="rolling", produces=["public PR", "review record"],
                  effort={"weekly_commitment": "2 h"})
        res = S.score_all(PROMO, [row], today=TODAY)
        scored = res["results"][0]
        self.assertGreaterEqual(scored["match_score"], 55,
                                f"match={scored['match_score']} components={scored['components']}")
        self.assertEqual(scored["zone"], "recommended_now")
        self.assertGreater(scored["components"]["goal_fit"], FLOOR)

    def test_outcome_leg_does_not_need_a_category_alias(self):
        """修复必须走 outcome facet，而不是给 career 加 open_source/event 类别别名。"""
        self.assertEqual(C.GOAL_TO_CATEGORY["career"], ["career"])
        self.assertIn("career", C.GOAL_OUTCOME_PROFILE)
        self.assertIn("reputation", C.GOAL_OUTCOME_PROFILE["career"])


class TestNegativeCases(unittest.TestCase):
    def test_beginner_open_source_issue_is_not_boosted(self):
        """反例 1：随机 beginner good-first-issue 不能因为 category=open_source 就高分。"""
        row = opp(primary_category="open_source",
                  outcomes={"skill": "medium", "portfolio": "low", "reputation": "low"})
        gf, _ = S.goal_component(row, PROMO)
        self.assertLess(gf, FLOOR * 1.5, f"应贴近地板，实际 {gf}")

    def test_entertainment_event_gets_no_boost(self):
        """反例 2：普通娱乐 event 不得因为 category=event 自动匹配职业目标。"""
        row = opp(primary_category="event", outcomes={"interest": "high", "exposure": "medium"})
        gf, note = S.goal_component(row, PROMO)
        self.assertEqual(gf, FLOOR)
        self.assertIn("不重合", note)

    def test_single_generic_facet_cannot_max_out(self):
        """只声明一个泛 facet 的机会拿不到高分（分母是"目标想要的全部"）。"""
        row = opp(primary_category="event", outcomes={"skill": "high"})
        gf, _ = S.goal_component(row, PROMO)
        self.assertLess(gf, 25, f"单泛 facet 不应高分，实际 {gf}")

    def test_unrelated_event_does_not_become_recommended(self):
        row = opp(id="e", primary_category="event",
                  outcomes={"interest": "high", "exposure": "high"}, deadline_type="rolling")
        res = S.score_all(PROMO, [row], today=TODAY)
        self.assertNotEqual(res["results"][0]["zone"], "recommended_now")


class TestRegressions(unittest.TestCase):
    def test_d_backend_to_ai_is_not_broken(self):
        """D（后端→AI）：生产平台类机会必须被认出来（≥60），且泛化不得让噪声顶上来。

        注意：类别本就对齐的入门课程在**类别腿**上拿高分是合法的（不属回归）；
        这里守的是"生产平台机会不被压到地板"与"无关机会不被抬高"。
        """
        bridge = opp(id="vllm", primary_category="open_source",
                     title="Contribute to vLLM inference serving",
                     outcomes={"skill": "high", "portfolio": "high", "career": "medium"},
                     deadline_type="rolling")
        noise = opp(id="noise", primary_category="event",
                    outcomes={"interest": "high", "exposure": "high"}, deadline_type="rolling")
        bridge_gf, _ = S.goal_component(bridge, D_PROFILE)
        noise_gf, _ = S.goal_component(noise, D_PROFILE)
        self.assertGreaterEqual(bridge_gf, 60, f"生产平台机会应被认出，实际 {bridge_gf}")
        self.assertLess(noise_gf, 30, f"无关机会不得被抬高，实际 {noise_gf}")

    def test_b_japan_masters_keeps_research_research_and_drops_noise(self):
        """B（日本修士）：研究型机会应高，无关社区活动不得顶上来。"""
        lab = opp(id="lab", primary_category="research",
                  outcomes={"research": "high", "admission": "high", "network": "high"},
                  deadline_type="rolling")
        noise = opp(id="noise", primary_category="networking",
                    outcomes={"exposure": "high", "interest": "high"},
                    deadline_type="rolling")
        lab_gf, _ = S.goal_component(lab, B_PROFILE)
        noise_gf, _ = S.goal_component(noise, B_PROFILE)
        self.assertGreater(lab_gf, 60, f"研究型机会应高，实际 {lab_gf}")
        self.assertLess(noise_gf, 30, f"无关社区活动不应上来，实际 {noise_gf}")

    def test_string_goals_are_normalised_not_silently_dropped(self):
        """真实运行里 goals 出现字符串 → 以前会静默退化成"没有目标"(15 分)。"""
        row = opp(primary_category="career", outcomes={"career": "high"})
        gf, _ = S.goal_component(row, {"goals": ["career"]})
        self.assertGreater(gf, FLOOR, "字符串目标必须被识别")

    def test_no_goal_still_neutral(self):
        gf, note = S.goal_component(opp(), {"goals": []})
        self.assertEqual(gf, 60.0)
        self.assertIn("中性", note)


class TestAllocationNeverFakesPrecision(unittest.TestCase):
    """D 独立跑暴露的假精度：渲染出"合计约 0.0h/周，与你给出的每周可用时间对齐"。"""

    PROF = {"constraints": {"weekly_time": "6"}}

    def test_unknown_hours_never_produce_a_total(self):
        out = P.format_allocation(self.PROF, [{"id": "a", "title": "X"}])
        self.assertEqual(out["mode"], "qualitative")
        self.assertNotIn("total_hours", out)
        self.assertIn("不做时间加总", out["note"])

    def test_months_are_not_hours(self):
        self.assertIsNone(P._parse_hours("2-6 个月"))
        self.assertIsNone(P._parse_hours("3-6 months"))
        self.assertIsNone(P._parse_hours("12 週間"))

    def test_real_hours_are_summed_and_unknowns_declared(self):
        out = P.format_allocation(self.PROF, [
            {"id": "a", "title": "X", "effort": {"weekly_commitment": "3 h"}},
            {"id": "b", "title": "Y", "effort": {"weekly_commitment": "2-6 个月"}}])
        self.assertEqual(out["mode"], "quantitative")
        self.assertEqual(out["total_hours"], 3.0)
        self.assertEqual(out["items_with_unknown_hours"], 1)
        self.assertNotIn("0.0h/周", out["note"])


if __name__ == "__main__":
    unittest.main()
