"""score.py 的测试：硬条件优先、画像缺失≠不满足、毕业窗口按月、GPA 同体系、技能匹配。"""

from __future__ import annotations

import datetime as dt
import unittest

import _helpers

import score as S

TODAY = dt.date(2026, 9, 14)


def profile(**kw):
    p = {
        "education": {"degree": "undergraduate", "major": "IoT Engineering",
                      "current_year": 3, "expected_graduation": "2028-06", "GPA": None},
        "skills": [{"name": "C"}, {"name": "Python"}, {"name": "ESP32"}],
        "languages": [{"language": "English", "exam": "CET", "score": None, "level": None}],
        "interests": ["Embedded"],
        "goals": [{"type": "internship", "priority": "high"}],
        "constraints": {"preferred_country": ["Japan"], "remote": True},
    }
    p.update(kw)
    return p


def opp(**kw):
    o = {"id": "t-2026", "title": "Test Opportunity 2026", "organization": "Org",
         "primary_category": "career"}
    o.update(kw)
    return o


def verdict(o, p=None):
    return S.eligibility_component(o, p or profile(), TODAY)[1]


class TestHardConstraintAuthority(unittest.TestCase):
    def test_expired_deadline_is_ineligible(self):
        self.assertEqual(verdict(opp(deadline="2026-09-01")), "Ineligible")

    def test_hard_education_mismatch_beats_agent_verdict(self):
        """页面写 PhD only + 画像本科 → 模型 verdict(Eligible) 不得推翻。"""
        o = opp(education_level=["phd"], eligibility={"verdict": "Eligible"})
        score, v, reasons, _, source, kind = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(v, "Probably Ineligible")
        self.assertEqual(source, "hard_constraint")
        self.assertTrue(any("覆盖" in r for r in reasons))

    def test_agent_may_downgrade_but_source_is_recorded(self):
        """模型可以更保守（它可能知道页面之外的语义条件），但要标明来源。"""
        o = opp(education_level=["undergraduate"], eligibility={"verdict": "Ineligible"})
        _, v, _, _, source, _ = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(v, "Ineligible")
        self.assertEqual(source, "agent_downgrade")

    def test_agent_cannot_upgrade_past_page_missing_info(self):
        """页面信息不可比时，模型最多给到 Probably Eligible，不能给 Eligible。"""
        o = opp(graduation_window="某年某月毕业", eligibility={"verdict": "Eligible"})
        _, v, _, _, source, kind = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(kind, "incomparable")
        self.assertEqual(v, "Probably Eligible")

    def test_missing_profile_allows_agent_verdict(self):
        """画像缺信息（Unknown）时，模型可依据对话中获得的信息判断。"""
        o = opp(education_level=["phd"], eligibility={"verdict": "Unknown"})
        _, v, _, _, source, kind = S.eligibility_component(o, profile(education={"degree": None}), TODAY)
        self.assertEqual(kind, "missing_profile")
        self.assertEqual(v, "Unknown")

    def test_student_year_mismatch(self):
        self.assertEqual(verdict(opp(student_year=[1, 2])), "Probably Ineligible")
        self.assertEqual(verdict(opp(student_year=[3])), "Eligible")


class TestMissingIsNotQualifiedAsNo(unittest.TestCase):
    def test_language_not_recorded_is_unknown(self):
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"})
        _, v, reasons, _, _, kind = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(v, "Unknown", "画像没有日语记录 ≠ 不会日语")
        self.assertEqual(kind, "missing_profile")

    def test_language_recorded_without_score_is_unknown(self):
        p = profile(languages=[{"language": "Japanese", "exam": "JLPT", "score": None, "level": None}])
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"})
        _, v, reasons, _, _, _ = S.eligibility_component(o, p, TODAY)
        self.assertEqual(v, "Unknown")
        self.assertTrue(any("不是不满足" in r for r in reasons))

    def test_explicit_none_marker_is_ineligible(self):
        p = profile(languages=[{"language": "Japanese", "exam": "JLPT", "level": "none"}])
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"})
        self.assertEqual(verdict(o, p), "Probably Ineligible")

    def test_language_meets_requirement(self):
        p = profile(languages=[{"language": "Japanese", "exam": "JLPT", "score": "N1", "level": None}])
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"})
        self.assertEqual(verdict(o, p), "Eligible")

    def test_language_below_requirement(self):
        p = profile(languages=[{"language": "English", "exam": "TOEIC", "score": "600"}])
        o = opp(language_requirement={"language": "English", "exam": "TOEIC", "min_level": "800"})
        self.assertEqual(verdict(o, p), "Probably Ineligible")

    def test_gpa_missing_is_unknown(self):
        self.assertEqual(verdict(opp(GPA_requirement="3.0/4.0")), "Unknown")

    def test_nationality_missing_is_unknown(self):
        self.assertEqual(verdict(opp(nationality_requirement="Japanese citizens only")), "Unknown")

    def test_school_missing_is_unknown(self):
        self.assertEqual(verdict(opp(school_requirement="Enrolled at Kagura University")), "Unknown")


class TestGraduationWindow(unittest.TestCase):
    def test_month_level_window(self):
        w = S.parse_grad_window("2027-09 ~ 2028-06")
        self.assertIsNotNone(w)
        self.assertEqual(S.in_grad_window((2027, 6), w)[0], False, "2027-06 不在窗口内")
        self.assertEqual(S.in_grad_window((2028, 3), w)[0], True, "2028-03 在窗口内")

    def test_japanese_march_cohort(self):
        w = S.parse_grad_window("2028 年 3 月卒業見込")
        self.assertEqual(S.in_grad_window((2028, 3), w)[0], True)
        self.assertEqual(S.in_grad_window((2028, 6), w)[0], False, "同一年但不同届 → 不在窗口")

    def test_english_window(self):
        w = S.parse_grad_window("Graduating between Sep 2027 and Jun 2028")
        self.assertEqual(S.in_grad_window((2027, 9), w)[0], True)
        self.assertEqual(S.in_grad_window((2028, 6), w)[0], True)
        self.assertEqual(S.in_grad_window((2028, 7), w)[0], False)

    def test_year_only_lower_confidence(self):
        w = S.parse_grad_window("2027")
        self.assertTrue(w[2], "只有年份精度时应标记 year_only")
        self.assertEqual(S.in_grad_window((2027, 6), w)[0], True)

    def test_unparseable(self):
        self.assertIsNone(S.parse_grad_window("soon"))

    def test_end_to_end_verdict(self):
        o = opp(graduation_window="2027-09 ~ 2028-06")
        p = profile(education={"degree": "undergraduate", "expected_graduation": "2027-06"})
        self.assertEqual(verdict(o, p), "Probably Ineligible")
        p2 = profile(education={"degree": "undergraduate", "expected_graduation": "2028-03"})
        self.assertEqual(verdict(o, p2), "Eligible")


class TestGpa(unittest.TestCase):
    def test_same_scale_pass_and_fail(self):
        self.assertEqual(S.gpa_check("3.0/4.0", "3.5/4.0")[0], "ok")
        self.assertEqual(S.gpa_check("3.5/4.0", "3.0/4.0")[0], "fail")

    def test_different_scale_is_incomparable(self):
        self.assertEqual(S.gpa_check("3.0/4.0", "85/100")[0], "unknown_incomparable")

    def test_missing(self):
        self.assertEqual(S.gpa_check("3.0/4.0", None)[0], "unknown_missing")


class TestNationality(unittest.TestCase):
    def test_explicit_conflict(self):
        p = profile(nationality="Chinese")
        self.assertEqual(verdict(opp(nationality_requirement="Japanese citizens only"), p),
                         "Probably Ineligible")

    def test_match(self):
        p = profile(nationality="Japanese")
        self.assertEqual(verdict(opp(nationality_requirement="Japanese citizens only"), p), "Eligible")

    def test_open_signal(self):
        self.assertEqual(verdict(opp(nationality_requirement="Open to all nationalities")), "Eligible")

    def test_no_sponsorship_vs_need(self):
        p = profile(constraints={"visa": "need_sponsorship_us"})
        self.assertEqual(verdict(opp(nationality_requirement="sponsorship not provided"), p),
                         "Probably Ineligible")


class TestSkillMatching(unittest.TestCase):
    def test_generic_token_does_not_hit(self):
        self.assertFalse(S.skill_hit("data engineering", ["data analysis"]),
                         "仅共享通用词 data 不能算命中")

    def test_cpp_is_not_c(self):
        self.assertFalse(S.skill_hit("C++", ["C"]))
        self.assertTrue(S.skill_hit("C", ["C/C++"]))

    def test_version_variant_hits(self):
        self.assertTrue(S.skill_hit("ESP32", ["ESP32-S3"]))
        self.assertTrue(S.skill_hit("python", ["Python3"]))

    def test_enum_style_alias(self):
        self.assertTrue(S.skill_hit("PyTorch", ["pytorch"]))

    def test_unrelated(self):
        self.assertFalse(S.skill_hit("RTOS", ["FreeRTOS"]))
        self.assertFalse(S.skill_hit("Kubernetes", ["Docker"]))

    def test_component_rewards_real_overlap(self):
        strong, _ = S.skill_component(opp(skills_required=["C", "Python", "Git"]), profile())
        weak, _ = S.skill_component(opp(skills_required=["Kubernetes", "Terraform"]), profile())
        self.assertGreater(strong, weak)


class TestScoringPipeline(unittest.TestCase):
    def test_priority_uses_deadline_endpoint(self):
        """区间截止：紧迫度取端点，Priority 必须相应更高。"""
        near = S.score_all(profile(), [opp(id="n", deadline="2026-09-20 ~ 2026-10-05")], today=TODAY)
        far = S.score_all(profile(), [opp(id="f", deadline="2027-09-20 ~ 2027-10-05")], today=TODAY)
        self.assertGreater(near["results"][0]["priority_score"], far["results"][0]["priority_score"])
        self.assertEqual(near["results"][0]["days_remaining"], 21)

    def test_expired_excluded(self):
        res = S.score_all(profile(), [opp(id="e", deadline="2026-01-01")], today=TODAY)
        self.assertEqual(res["scored"], 0)
        self.assertEqual(len(res["excluded"]), 1)

    def test_rolling_has_no_urgency_penalty(self):
        res = S.score_all(profile(), [opp(id="r", deadline=None)], today=TODAY)
        self.assertIn("no_deadline", res["results"][0]["flags"])
        self.assertIsNone(res["results"][0]["urgency"])

    def test_scoring_is_deterministic(self):
        o = opp(id="s", deadline="2026-12-01")
        a = S.score_all(profile(), [o], today=TODAY)["results"][0]
        b = S.score_all(profile(), [dict(o)], today=TODAY)["results"][0]
        self.assertEqual(a["match_score"], b["match_score"])
        self.assertEqual(a["priority_score"], b["priority_score"])

    def test_contract_issues_surface(self):
        res = S.score_all(profile(), [opp(id="bad id with spaces")], today=TODAY)
        self.assertTrue(res["contract_issues"])

    def test_example_files_run(self):
        import json
        prof = json.load(open(_helpers.path("examples", "profile.example.json"), encoding="utf-8"))
        opps = json.load(open(_helpers.path("examples", "opportunity.batch.example.json"),
                              encoding="utf-8"))["opportunities"]
        res = S.score_all(prof, opps, today=TODAY)
        self.assertGreater(res["scored"], 0)
        self.assertEqual(res["contract_issues"], [])


class TestEvidenceGaps(unittest.TestCase):
    def test_gaps_reported(self):
        o = opp(evidence={"deadline": {"status": "unknown"},
                          "language_requirement": {"status": "inferred"},
                          "major_requirement": {"status": "explicit"}})
        gaps = S.evidence_gaps(o)
        self.assertTrue(any("deadline" in g for g in gaps))
        self.assertTrue(any("language_requirement" in g for g in gaps))
        self.assertTrue(any("major_requirement" in g for g in gaps), "explicit 但缺 source_url 也应提示")


if __name__ == "__main__":
    unittest.main()
