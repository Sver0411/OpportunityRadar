"""P1 Output & Decision UX 的回归测试（表达层，不改判断逻辑）。

覆盖：Decision Confidence 控语气、伪精确防护（按依据判定）、category-aware 参与措辞、
行动措辞、Explore 维度（不凑数）、self-directed 与真实机会分离、回答骨架与长度控制、
8 个输出指标、跨会话 context leakage。
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import presentation as P    # noqa: E402

# 三个画像：依据全无 / 只有时间预算 / 目标+资源都清楚
NO_BASIS = {"life_stage": ["working"], "goals": []}
TIME_ONLY = {"life_stage": ["working"], "career_stage": ["early_career"],
             "education": {"school_country": "China"}, "skills": [{"name": "Python"}],
             "interests": [{"name": "ai"}], "constraints": {"weekly_time": "6"},
             "goals": [{"type": "skill", "priority": "high"}]}
FULL = {**TIME_ONLY,
        "constraints": {"weekly_time": "6", "available_period": "2026-10 ~ 2027-03",
                        "budget": "low"}}

REAL_ROW = {"id": "r1", "title": "开源之夏", "organization": "中科院软件所",
            "primary_category": "open_source", "zone": "recommended_now",
            "eligibility_verdict": "Probably Eligible", "evidence_complete": True,
            "actionable": True, "participation_open": True, "freshness": "likely_open",
            "effort": {"weekly_commitment": "5 h"}, "produces": ["GitHub PR", "结项证书"],
            "future_optionality": {"level": "high", "reason": "以后申请相关岗位时有工程证据"},
            "components": {"interest_fit": 70, "skill_fit": 80},
            "official_url": "https://summer.ospp.ac.cn/"}

EXPLORE_ROWS = [
    {"id": "e1", "title": "社区开源贡献", "primary_category": "open_source",
     "zone": "recommended_now", "eligibility_verdict": "Probably Eligible",
     "evidence_complete": True, "actionable": True, "participation_open": True,
     "freshness": "likely_open", "effort": {"weekly_commitment": "5 h"},
     "produces": ["GitHub PR"]},
    {"id": "e2", "title": "国际志愿者项目", "primary_category": "networking",
     "zone": "worth_verifying", "eligibility_verdict": "Unknown",
     "evidence_complete": False, "freshness": "unknown", "produces": ["志愿服务证明"]},
    {"id": "e3", "title": "内容创作（播客）计划", "primary_category": "hobby",
     "zone": "worth_verifying", "eligibility_verdict": "Eligible", "evidence_complete": True,
     "actionable": True, "participation_open": True, "freshness": "open",
     "effort": {"weekly_commitment": "3 h"}, "produces": ["公开作品集"]},
]


class TestDecisionConfidence(unittest.TestCase):
    def test_no_goal_no_basis_is_low(self):
        d = P.decision_confidence(NO_BASIS, [], [])
        self.assertEqual(d["level"], "low")
        self.assertIn("goal_clarity", d["unknown"])

    def test_clear_goal_but_unknown_resources_is_medium(self):
        d = P.decision_confidence(TIME_ONLY, [REAL_ROW], [])
        self.assertEqual(d["level"], "medium")

    def test_full_basis_can_reach_high(self):
        d = P.decision_confidence(FULL, [REAL_ROW], [])
        self.assertEqual(d["level"], "high")

    def test_critical_unknown_never_yields_high(self):
        p = {**FULL}
        p["constraints"] = {"available_period": "2026-10 ~ 2027-03"}   # 缺 weekly_time
        d = P.decision_confidence(p, [REAL_ROW], [])
        self.assertNotEqual(d["level"], "high")

    def test_level_is_not_a_ranking_score(self):
        """置信度只控制表达强度：不得出现在候选行里，也不得改变排序字段。"""
        d = P.decision_confidence(FULL, [REAL_ROW], [])
        self.assertNotIn("score", d)
        self.assertNotIn("match", d)

    def test_forbidden_wording_lists_are_non_empty(self):
        for lvl in P.CONFIDENCE_LEVELS:
            with self.subTest(level=lvl):
                self.assertTrue(P.CLAIM_WORDING[lvl]["forbidden"])


class TestPrecisionGuard(unittest.TestCase):
    PERCENT = "本月建议：60% / 25% / 15% 分配"
    DAILY = "每天 1.5 小时"
    SUM = "每周 3h + 1h + 1h = 5h"

    def test_percentage_needs_both_bases(self):
        self.assertTrue(P.scan_unsupported_precision(self.PERCENT, NO_BASIS))
        self.assertTrue(P.scan_unsupported_precision(self.PERCENT, TIME_ONLY))
        self.assertEqual(P.scan_unsupported_precision(self.PERCENT, FULL), [])

    def test_daily_hours_needs_weekly_time(self):
        self.assertTrue(P.scan_unsupported_precision(self.DAILY, NO_BASIS))
        self.assertEqual(P.scan_unsupported_precision(self.DAILY, TIME_ONLY), [])

    def test_hours_sum_needs_weekly_time(self):
        """用户没给预算时，"3h+1h+1h=5h" 里的 5h 是系统凭空造的。"""
        self.assertTrue(P.scan_unsupported_precision(self.SUM, NO_BASIS))
        self.assertEqual(P.scan_unsupported_precision(self.SUM, TIME_ONLY), [])

    def test_no_duplicate_hits(self):
        hits = P.scan_unsupported_precision(self.PERCENT + "；" + self.PERCENT, NO_BASIS)
        seen = [(h["kind"], h["text"]) for h in hits]
        self.assertEqual(len(seen), len(set(seen)))

    def test_allocation_style_follows_basis(self):
        self.assertEqual(P.allocation_style(NO_BASIS)["mode"], "qualitative")
        self.assertEqual(P.allocation_style(TIME_ONLY)["mode"], "quantitative")

    def test_qualitative_allocation_states_the_unknown(self):
        out = P.format_allocation(NO_BASIS, [REAL_ROW])
        self.assertEqual(out["mode"], "qualitative")
        self.assertEqual(out["note"], P.BUDGET_UNKNOWN_NOTE)
        self.assertEqual([i["level"] for i in out["items"]], ["主线"])


class TestParticipationWording(unittest.TestCase):
    def test_oss_speaks_in_contribution_terms(self):
        self.assertEqual(P.participation_wording("open_source", "Eligible")["label"],
                         "Open participation")
        self.assertEqual(P.participation_wording("open_source", "Unknown")["label"],
                         "Contribution prerequisites")
        self.assertEqual(P.participation_wording("open_source", "Ineligible")["label"],
                         "Restricted")

    def test_event_speaks_in_registration_terms(self):
        self.assertEqual(P.participation_wording("competition", "Eligible")["label"],
                         "Registration open")
        self.assertEqual(P.participation_wording("event", "Unknown")["label"],
                         "Eligibility needs confirmation")

    def test_community_speaks_in_membership_terms(self):
        self.assertEqual(P.participation_wording("networking", "Eligible")["label"],
                         "Open to join")
        self.assertEqual(P.participation_wording("networking", "Probably Eligible")["label"],
                         "Prerequisites apply")
        self.assertEqual(P.participation_wording("networking", "Ineligible")["label"],
                         "Invitation / selection required")

    def test_jobs_keep_the_eligibility_vocabulary(self):
        self.assertEqual(P.participation_wording("career", "Probably Eligible")["label"],
                         "Probably Eligible")

    def test_closed_freshness_overrides_every_family(self):
        for cat in ("open_source", "competition", "networking", "career"):
            with self.subTest(category=cat):
                w = P.participation_wording(cat, "Eligible", freshness="closed")
                self.assertEqual(w["label"], "Not currently open")

    def test_underlying_verdict_is_preserved(self):
        """只做措辞适配，不改底层判定。"""
        self.assertEqual(P.participation_wording("open_source", "Unknown")["verdict"],
                         "Unknown")


class TestActionLabel(unittest.TestCase):
    def test_all_clear_means_action_now(self):
        d = P.action_label(REAL_ROW, {"level": "high", "signals": {"time_budget_known": True}})
        self.assertEqual(d["label"], "现在可以行动")

    def test_missing_evidence_downgrades(self):
        row = {**REAL_ROW, "evidence_complete": False}
        self.assertEqual(P.action_label(row, {"level": "medium"})["label"], "值得进一步核实")

    def test_unconfirmed_participation_is_only_worth_understanding(self):
        row = {**REAL_ROW, "participation_open": False}
        self.assertEqual(P.action_label(row, {"level": "medium"})["label"], "值得先了解")

    def test_low_confidence_only_offers_direction_experiments(self):
        d = P.action_label(REAL_ROW, {"level": "low"})
        self.assertEqual(d["label"], "值得拿来试方向")

    def test_unknown_time_budget_prevents_action_now(self):
        d = P.action_label(REAL_ROW, {"level": "high", "signals": {"time_budget_known": False}})
        self.assertNotEqual(d["label"], "现在可以行动")


class TestExploreDiversity(unittest.TestCase):
    def test_only_used_when_direction_is_explore(self):
        self.assertTrue(P.explore_focus(NO_BASIS)["enabled"])
        self.assertFalse(P.explore_focus(TIME_ONLY)["enabled"])

    def test_axes_cover_more_than_technical(self):
        cov = P.explore_coverage(EXPLORE_ROWS)
        self.assertGreaterEqual(cov["axis_count"], 3)
        for axis in ("volunteer", "creative", "community"):
            with self.subTest(axis=axis):
                self.assertIn(axis, cov["axes"])

    def test_coverage_never_pads(self):
        """只找到两类就只报两类，缺的维度如实写在 missing_axes。"""
        cov = P.explore_coverage([EXPLORE_ROWS[0]])
        self.assertEqual(cov["axis_count"], len(cov["axes"]))
        self.assertIn("volunteer", cov["missing_axes"])
        self.assertEqual([a for a in cov["axes"] if a not in P.EXPLORE_AXES], [])

    def test_technical_share_is_reported(self):
        share = P.technical_share(EXPLORE_ROWS)
        self.assertEqual(share["total"], 3)
        self.assertLess(share["share"], 1.0)

    def test_axes_are_not_a_new_taxonomy(self):
        """探索维度只是表达轴：只引用已有 category，且不新建类别枚举。

        注意 `research` / `entrepreneurship` 同时是 category 与轴名（在这里含义一致），
        所以不要求两者互斥 —— 要求的是"没有引入新的类别"。
        """
        import common as C
        self.assertEqual(set(P.AXIS_BY_CATEGORY) - set(C.CATEGORIES), set())
        self.assertFalse(hasattr(P, "CATEGORIES"), "模块不得另立 category 枚举")
        self.assertNotEqual(set(P.EXPLORE_AXES), set(C.CATEGORIES))
        for cat in P.AXIS_BY_CATEGORY:
            with self.subTest(category=cat):
                self.assertIn(cat, C.CATEGORIES)


class TestSelfDirectedSeparation(unittest.TestCase):
    def test_fallback_is_never_an_opportunity(self):
        fb = P.self_directed_fallback({"name": "公开协作经历"})
        self.assertEqual(fb["kind"], "self_directed")
        self.assertTrue(fb["not_an_opportunity"])
        self.assertNotIn("zone", fb)

    def test_split_keeps_them_apart(self):
        fb = P.self_directed_fallback({"name": "公开协作经历"})
        fb["zone"] = "recommended_now"          # 就算被误标，也要被识别为混入
        sp = P.split_recommendations(EXPLORE_ROWS + [fb])
        self.assertEqual(len(sp["self_directed"]), 1)
        self.assertTrue(sp["mixed"])

    def test_answer_puts_fallbacks_in_their_own_block(self):
        fb = P.self_directed_fallback({"name": "公开协作经历"})
        ans = P.render_answer(TIME_ONLY, EXPLORE_ROWS + [fb], mode="A")
        main_ids = [c["opportunity_id"] for c in ans["main"]]
        self.assertNotIn(fb.get("gap"), main_ids)
        self.assertEqual(len(ans["self_directed"]), 1)


class TestAnswerSkeleton(unittest.TestCase):
    def test_length_is_capped(self):
        rows = [{**REAL_ROW, "id": f"r{i}"} for i in range(9)]
        ans = P.render_answer(FULL, rows, max_main=3)
        self.assertLessEqual(len(ans["main"]), 3)
        self.assertEqual(ans["length_budget"]["limit"], 3)

    def test_cards_use_user_readable_fields_only(self):
        ans = P.render_answer(FULL, [REAL_ROW])
        card = ans["main"][0]
        for field in P.CARD_FIELDS:
            self.assertIn(field, card)
        self.assertNotIn("components", card["present_fields"])
        text = P.render_card(card)
        self.assertNotIn("match_score", text)
        self.assertNotIn("components", text)

    def test_gap_bridge_is_visible_in_the_card(self):
        gaps = [{"id": "g1", "name": "公开协作经历", "type": "portfolio",
                 "relevance": {"relevance": "supporting_gap"}}]
        bridges = [{"opportunity_id": "r1", "gap": "公开协作经历", "score": 88}]
        card = P.recommendation_card(REAL_ROW, FULL, gaps, bridges)
        self.assertEqual(card["gap_filled"]["gap"], "公开协作经历")
        self.assertIn("你现在缺", P.render_card(card))

    def test_card_unknowns_are_listed(self):
        row = {**REAL_ROW, "evidence_complete": False,
               "evidence_missing": ["evidence.application_status"]}
        card = P.recommendation_card(row, FULL)
        self.assertTrue(card["needs_confirmation"])

    def test_audit_catches_unsupported_precision(self):
        bad = P.render_answer(NO_BASIS, [REAL_ROW])
        bad["violations"] = P.audit_answer("建议 60% / 25% / 15%", NO_BASIS)
        self.assertTrue(bad["violations"])
        self.assertEqual(bad["violations"][0]["kind"], "unsupported_precision")

    def test_audit_catches_strong_claims_under_low_confidence(self):
        conf = P.decision_confidence(NO_BASIS, [], [])
        hits = P.audit_answer("这是你的最优路线，你现在必须选它", NO_BASIS, conf)
        kinds = {h["kind"] for h in hits}
        self.assertIn("strong_claim", kinds)

    def test_clean_answer_has_no_violations(self):
        ans = P.render_answer(FULL, [REAL_ROW])
        self.assertEqual(ans["violations"], [])
        self.assertTrue(ans["ok"])


class TestOutputMetrics(unittest.TestCase):
    def test_compliant_answers_score_zero_on_the_hard_requirements(self):
        answers = [P.render_answer(FULL, [REAL_ROW]),
                   P.render_answer(NO_BASIS, EXPLORE_ROWS, mode="E")]
        m = P.output_metrics(answers)
        self.assertEqual(m["unsupported_precision_count"], 0)
        self.assertEqual(m["strong_claim_with_low_confidence_count"], 0)
        self.assertEqual(m["self_directed_mixed_with_real_opportunity_count"], 0)
        self.assertEqual(m["persona_context_leakage_count"], 0)

    def test_all_eight_metrics_are_reported(self):
        m = P.output_metrics([P.render_answer(FULL, [REAL_ROW])])
        for key in P.OUTPUT_METRICS:
            self.assertIn(key, m)

    def test_explore_axis_count_reflects_the_answer(self):
        m = P.output_metrics([P.render_answer(NO_BASIS, EXPLORE_ROWS, mode="E")])
        self.assertGreaterEqual(m["explore_axis_count"], 3)


class TestContextLeakage(unittest.TestCase):
    def test_clean_profile_reports_no_leak(self):
        self.assertEqual(P.context_leakage(FULL), [])

    def test_inherited_profile_is_detected(self):
        p = {**FULL, "_inherited_from": "前一个 session 的 CS 学生画像"}
        self.assertTrue(P.context_leakage(p))

    def test_inherited_field_is_detected(self):
        p = {**FULL, "skills": {"_inherited_from": "previous session"}}
        self.assertTrue(P.context_leakage(p))


if __name__ == "__main__":
    unittest.main()


class TestEffortFieldShapes(unittest.TestCase):
    """真实存档记录里 `effort` 既有 dict 也有字符串 —— 两种都要能渲染。"""

    def test_string_effort_is_rendered(self):
        row = {**REAL_ROW, "effort": "3h/week"}
        card = P.recommendation_card(row, FULL)
        self.assertEqual(card["effort"], "每周约 3h/week")
        self.assertNotIn("每周投入未写明", card["needs_confirmation"])

    def test_dict_effort_is_rendered(self):
        card = P.recommendation_card(REAL_ROW, FULL)
        self.assertEqual(card["effort"], "每周约 5 h")

    def test_missing_effort_is_honest(self):
        row = {k: v for k, v in REAL_ROW.items() if k != "effort"}
        card = P.recommendation_card(row, FULL)
        self.assertIn("未写明", card["effort"])
        self.assertIn("每周投入未写明", card["needs_confirmation"])

    def test_time_commitment_is_used_as_fallback(self):
        row = {k: v for k, v in REAL_ROW.items() if k != "effort"}
        row["time_commitment"] = "开发周期 2-4 个月"
        self.assertIn("2-4 个月", P.recommendation_card(row, FULL)["effort"])


class TestUnverifiedNeverSoundsAffirmative(unittest.TestCase):
    """实测缺陷：官方页自相矛盾（verification_status=conflicting）的机会被写成
    "Registration open" —— 未核实清楚时不许给肯定式说法。"""

    def test_conflicting_event_does_not_say_registration_open(self):
        w = P.participation_wording("competition", "Eligible", "open", "conflicting")
        self.assertEqual(w["label"], "Eligibility needs confirmation")
        self.assertIn("conflicting", " ".join(P.UNCONFIRMED_VERIFICATION) + w["note"])

    def test_unverified_open_source_does_not_say_open_participation(self):
        w = P.participation_wording("open_source", "Eligible", "open", "unverified")
        self.assertEqual(w["label"], "Contribution prerequisites")

    def test_verified_official_still_affirmative(self):
        w = P.participation_wording("competition", "Eligible", "open", "verified_official")
        self.assertEqual(w["label"], "Registration open")

    def test_closed_overrides_verification(self):
        w = P.participation_wording("competition", "Eligible", "closed", "conflicting")
        self.assertEqual(w["label"], "Not currently open")

    def test_card_passes_verification_status(self):
        row = {**REAL_ROW, "verification_status": "conflicting"}
        card = P.recommendation_card(row, FULL)
        self.assertNotEqual(card["participation"]["label"], "Open participation")


class TestWhyFitIsUserFacing(unittest.TestCase):
    """实测缺陷：推荐理由里混进内部推理原文，并在用户没说过偏好时断言"与你的偏好相符"。"""

    NO_PREFS = {"life_stage": ["working"], "goals": []}

    def test_no_fabricated_location_fit(self):
        """E 类用户从没说过地点偏好 → 不能写"地点/远程方式与你的偏好相符"。"""
        row = {**REAL_ROW, "components": {"location_fit": 95, "goal_fit": 90, "interest_fit": 80}}
        card = P.recommendation_card(row, self.NO_PREFS)
        self.assertNotIn("偏好相符", card["why_fit"])
        self.assertNotIn("与你的目标直接相关", card["why_fit"])

    def test_only_stated_signals_become_reasons(self):
        row = {**REAL_ROW, "components": {"location_fit": 95, "interest_fit": 80}}
        p = {"life_stage": ["working"], "interests": [{"name": "ai"}], "goals": []}
        card = P.recommendation_card(row, p)
        self.assertIn("兴趣", card["why_fit"])
        self.assertNotIn("偏好相符", card["why_fit"])

    def test_internal_uncertainty_text_goes_to_needs_confirmation(self):
        row = {**REAL_ROW, "eligibility_reasons": [
            "页面限定学历 ['undergraduate']，画像未提供学历 → 无法判断",
            "滚动招募，无固定截止日"]}
        card = P.recommendation_card(row, FULL)
        self.assertNotIn("未提供学历", card["why_fit"])
        self.assertNotIn("['undergraduate']", card["why_fit"])
        self.assertTrue(any("无法判断" in x for x in card["needs_confirmation"]))
        self.assertIn("滚动招募", card["why_fit"])

    def test_non_numeric_effort_is_phrased_honestly(self):
        card = P.recommendation_card({**REAL_ROW, "effort": "self-paced"}, FULL)
        self.assertIn("未给出小时数", card["effort"])

    def test_card_render_has_no_internal_brackets(self):
        row = {**REAL_ROW, "eligibility_reasons": ["页面限定学历 ['master']，画像未提供学历 → 无法判断"]}
        card = P.recommendation_card(row, FULL)
        text = P.render_card(card)
        for junk in ("['master']", '"master"', "→", "画像"):
            with self.subTest(junk=junk):
                self.assertNotIn(junk, text, "展示文本不得含内部语法/术语")
        # 人话版本仍要保留原意，且结构化原文另存
        self.assertTrue(any("master" in x for x in card["needs_confirmation"]))
        self.assertTrue(card["needs_confirmation_details"]["uncertain_reasons_raw"])
