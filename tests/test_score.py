"""score.py 的测试。

覆盖：Evidence Gate、空资格信息、硬条件权威性、画像缺失策略、毕业窗口按月比较、
GPA 同体系、语言 string/object 一致性、技能同族、parse_hours、地区/学校匹配、
profile provenance 隔离。
"""

from __future__ import annotations

import datetime as dt
import unittest

import _helpers

import score as S
from common import canonical_country

TODAY = dt.date(2026, 9, 14)


def profile(**kw):
    """中性基础画像：地区与专业不预设。

    刻意不用任何特定国家/专业当默认 —— 泛化回归测试会盯着这一点（见 test_locale.py）。
    """
    p = {
        "education": {"degree": "undergraduate", "major": "Computer Science",
                      "current_year": 3, "expected_graduation": "2028-06", "GPA": None},
        "skills": [{"name": "Python"}, {"name": "Linux"}, {"name": "Git"}],
        "languages": [{"language": "English", "exam": None, "score": None, "level": "native"}],
        "interests": ["security", "open_source"],
        "goals": [{"type": "internship", "priority": "high"}],
        "constraints": {"preferred_country": ["United States"], "remote": True},
    }
    p.update(kw)
    return p


def opp(**kw):
    o = {"id": "t-2026", "title": "Test Opportunity 2026", "organization": "Org",
         "primary_category": "career"}
    o.update(kw)
    return o


def explicit(*fields):
    return {"evidence": {f: {"status": "explicit"} for f in fields}}


def inferred(*fields):
    return {"evidence": {f: {"status": "inferred"} for f in fields}}


def verdict(o, p=None):
    return S.eligibility_component(o, p or profile(), TODAY)[1]


class TestEmptyEligibility(unittest.TestCase):
    def test_no_eligibility_info_is_unknown(self):
        """页面没写任何资格条件 → Unknown（不是 Probably Eligible）。"""
        _, v, reasons, _, _, kind, _ = S.eligibility_component(opp(), profile(), TODAY)
        self.assertEqual(v, "Unknown")
        self.assertEqual(kind, "missing_source")
        self.assertTrue(any("没写要求不等于大概率符合" in r for r in reasons))

    def test_semantic_condition_satisfied_gives_probably_eligible(self):
        o = opp(**explicit("major_requirement"), major_requirement="Electrical Engineering or related field")
        self.assertEqual(verdict(o), "Probably Eligible")


class TestEvidenceGate(unittest.TestCase):
    def test_inferred_language_cannot_hard_fail(self):
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"},
                **inferred("language_requirement"))
        p = profile(languages=[{"language": "Japanese", "exam": "JLPT", "score": "N4"}])
        _, v, _, _, _, _, warns = S.eligibility_component(o, p, TODAY)
        self.assertNotEqual(v, "Probably Ineligible", "inferred 字段不得用于硬性淘汰")
        self.assertEqual(v, "Unknown")
        self.assertTrue(any("不能作为硬性淘汰依据" in w for w in warns))

    def test_inferred_education_cannot_hard_conflict(self):
        o = opp(education_level=["phd"], **inferred("education_level"))
        self.assertNotEqual(verdict(o), "Ineligible")
        self.assertEqual(verdict(o), "Unknown")

    def test_explicit_education_can_fail(self):
        o = opp(education_level=["phd"], **explicit("education_level"))
        self.assertEqual(verdict(o), "Ineligible")

    def test_missing_entry_cannot_reject(self):
        """有 evidence 结构但没追踪该字段 → 同样不能淘汰。"""
        o = opp(education_level=["phd"], evidence={"deadline": {"status": "explicit"}})
        self.assertEqual(verdict(o), "Unknown")

    def test_unknown_status_cannot_reject(self):
        o = opp(education_level=["phd"], evidence={"education_level": {"status": "unknown"}})
        self.assertEqual(verdict(o), "Unknown")

    def test_legacy_record_caps_positive_verdict(self):
        """旧格式（完全没有 evidence）：硬条件可用，但不给最乐观结论。"""
        o = opp(deadline="2026-12-01", education_level=["undergraduate"])
        _, v, _, _, _, _, warns = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(v, "Probably Eligible")
        self.assertTrue(any("provenance" in w.lower() or "evidence" in w.lower() for w in warns))

    def test_explicit_evidence_allows_eligible(self):
        o = opp(deadline="2026-12-01", education_level=["undergraduate"],
                **explicit("deadline", "education_level"))
        self.assertEqual(verdict(o), "Eligible")

    def test_status_helper_values(self):
        self.assertEqual(S.evidence_status(opp(), "deadline"), "legacy")
        self.assertEqual(S.evidence_status(opp(**explicit("deadline")), "deadline"), "explicit")
        self.assertEqual(S.evidence_status(opp(**explicit("deadline")), "education_level"), "missing")
        self.assertTrue(S.is_hard_evidence(opp(), "deadline"))
        self.assertFalse(S.is_hard_evidence(opp(**inferred("deadline")), "deadline"))


class TestHardConstraintAuthority(unittest.TestCase):
    def test_expired_deadline_is_ineligible(self):
        self.assertEqual(verdict(opp(deadline="2026-09-01")), "Ineligible")

    def test_hard_education_mismatch_beats_agent_verdict(self):
        o = opp(education_level=["phd"], eligibility={"verdict": "Eligible"})
        _, v, reasons, _, source, _, _ = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(v, "Ineligible")
        self.assertEqual(source, "hard_constraint")
        self.assertTrue(any("覆盖" in r for r in reasons))

    def test_agent_may_downgrade_but_source_is_recorded(self):
        o = opp(education_level=["undergraduate"], eligibility={"verdict": "Ineligible"})
        _, v, _, _, source, _, _ = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(v, "Ineligible")
        self.assertEqual(source, "agent_downgrade")

    def test_agent_cannot_upgrade_past_page_missing_info(self):
        o = opp(graduation_window="某年某月毕业", eligibility={"verdict": "Eligible"})
        _, v, _, _, _, kind, _ = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(kind, "incomparable")
        self.assertEqual(v, "Probably Eligible")

    def test_missing_profile_allows_agent_verdict(self):
        o = opp(education_level=["phd"], **explicit("education_level"),
                eligibility={"verdict": "Unknown"})
        _, v, _, _, _, kind, _ = S.eligibility_component(
            o, profile(education={"degree": None}), TODAY)
        self.assertEqual(kind, "missing_profile")
        self.assertEqual(v, "Unknown")

    def test_student_year_mismatch(self):
        self.assertEqual(verdict(opp(student_year=[1, 2], **explicit("student_year"))), "Ineligible")
        self.assertEqual(verdict(opp(student_year=[3], **explicit("student_year"))), "Eligible")


class TestMissingIsNotQualifiedAsNo(unittest.TestCase):
    def test_language_not_recorded_is_unknown(self):
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"},
                **explicit("language_requirement"))
        _, v, _, _, _, kind, _ = S.eligibility_component(o, profile(), TODAY)
        self.assertEqual(v, "Unknown", "画像没有日语记录 ≠ 不会日语")
        self.assertEqual(kind, "missing_profile")

    def test_language_recorded_without_score_is_unknown(self):
        p = profile(languages=[{"language": "Japanese", "exam": "JLPT", "score": None, "level": None}])
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"},
                **explicit("language_requirement"))
        _, v, reasons, _, _, _, _ = S.eligibility_component(o, p, TODAY)
        self.assertEqual(v, "Unknown")
        self.assertTrue(any("不是不满足" in r for r in reasons))

    def test_explicit_none_marker_is_ineligible(self):
        p = profile(languages=[{"language": "Japanese", "exam": "JLPT", "level": "none"}])
        o = opp(language_requirement={"language": "Japanese", "exam": "JLPT", "min_level": "N2"})
        self.assertEqual(verdict(o, p), "Probably Ineligible")

    def test_gpa_missing_is_unknown(self):
        self.assertEqual(verdict(opp(GPA_requirement="3.0/4.0")), "Unknown")

    def test_nationality_missing_is_unknown(self):
        self.assertEqual(verdict(opp(nationality_requirement="Japanese citizens only")), "Unknown")

    def test_school_missing_is_unknown(self):
        self.assertEqual(verdict(opp(school_requirement="Enrolled at Kagura University")), "Unknown")


class TestLanguageParsing(unittest.TestCase):
    def user(self, language, exam, level):
        return profile(languages=[{"language": language, "exam": exam, "score": level, "level": level}])

    def test_string_forms_are_normalized(self):
        for text in ["Japanese JLPT N2", "JLPT N2", "Japanese N2"]:
            with self.subTest(text=text):
                req = S.normalize_language_requirement(text)
                self.assertEqual(req["language"], "japanese")
                self.assertEqual(req["exam"], "JLPT")
                self.assertTrue(req["quantifiable"])
                self.assertEqual(req["levels"], {"jlpt": 4.0})

    def test_object_form_matches_string_form(self):
        a = S.normalize_language_requirement("Japanese JLPT N2")
        b = S.normalize_language_requirement({"language": "Japanese", "exam": "JLPT", "min_level": "N2"})
        self.assertEqual(a["levels"], b["levels"])
        self.assertEqual(a["language"], b["language"])

    def test_numeric_exams(self):
        for text, exam, value in [("TOEIC 800", "TOEIC", 800.0),
                                  ("English TOEIC 800", "TOEIC", 800.0),
                                  ("IELTS 6.5", "IELTS", 6.5)]:
            with self.subTest(text=text):
                req = S.normalize_language_requirement(text)
                self.assertEqual(req["exam"], exam)
                self.assertEqual(req["levels"].get(exam), value)

    def test_string_requirement_end_to_end(self):
        o = opp(language_requirement="Japanese JLPT N2", **explicit("language_requirement"))
        self.assertEqual(verdict(o, self.user("Japanese", "JLPT", "N1")),
                         "Eligible", "N1 应满足 N2（string 形态也要一致）")
        self.assertEqual(verdict(o, self.user("Japanese", "JLPT", "N4")), "Probably Ineligible")

    def test_toeic_string_requirement(self):
        o = opp(language_requirement="TOEIC 800", **explicit("language_requirement"))
        self.assertEqual(verdict(o, self.user("English", "TOEIC", "900")), "Eligible")
        self.assertEqual(verdict(o, self.user("English", "TOEIC", "600")), "Probably Ineligible")

    def test_qualitative_requirement_is_not_mapped(self):
        """business-level 这类表述不得硬转成 JLPT N2 之类的等级。"""
        req = S.normalize_language_requirement("business-level Japanese")
        self.assertFalse(req["quantifiable"])
        self.assertTrue(req["qualitative"])
        o = opp(language_requirement="business-level Japanese", **explicit("language_requirement"))
        v = verdict(o, self.user("Japanese", "JLPT", "N3"))
        self.assertEqual(v, "Unknown", "自然语言要求交语义判断，不做硬性判定")
        self.assertNotEqual(v, "Probably Ineligible")

    def test_cross_scale_is_not_converted(self):
        """JLPT N2 要求 + 画像只有 CEFR B2 → 不换算，判 Unknown。"""
        o = opp(language_requirement="JLPT N2", **explicit("language_requirement"))
        p = profile(languages=[{"language": "Japanese", "exam": None, "score": None, "level": "B2"}])
        self.assertEqual(verdict(o, p), "Unknown")

    def test_cet_level_not_confused_with_score(self):
        """CET-6 是等级、550 是分数，分属不同单位，不得混为一谈。"""
        self.assertEqual(S.parse_levels("CET-6"), {"cet_level": 3.0})
        self.assertEqual(S.parse_levels("CET-4 550", default_unit="CET"),
                         {"cet_level": 2.0, "CET": 550.0})

    def test_cet_level_requirement_compares_by_level(self):
        o = opp(language_requirement="CET-6", **explicit("language_requirement"))
        cet4 = profile(languages=[{"language": "Chinese", "exam": "CET", "score": "550",
                                   "level": "CET-4"}])
        self.assertEqual(verdict(o, cet4), "Probably Ineligible", "CET-4 不满足 CET-6")


class TestNationality(unittest.TestCase):
    def test_explicit_conflict(self):
        p = profile(nationality="Chinese")
        self.assertEqual(verdict(opp(nationality_requirement="Japanese citizens only"), p),
                         "Probably Ineligible")

    def test_match(self):
        p = profile(nationality="Japanese")
        self.assertEqual(verdict(opp(nationality_requirement="Japanese citizens only",
                                     **explicit("nationality_requirement")), p), "Eligible")

    def test_open_signal(self):
        self.assertEqual(verdict(opp(nationality_requirement="Open to all nationalities",
                                     **explicit("nationality_requirement"))), "Eligible")

    def test_unrecognised_restriction_is_unknown_not_ok(self):
        """解析器读不懂的限制绝不默认"没有限制"。"""
        for text in ["EEA/Swiss nationals only", "EU right-to-work required",
                     "resident of GCC countries", "must hold a valid work permit"]:
            with self.subTest(text=text):
                p = profile(nationality="Chinese", constraints={"visa": "none"})
                _, v, _, _, _, _, _ = S.eligibility_component(
                    opp(nationality_requirement=text), p, TODAY)
                self.assertNotEqual(v, "Eligible", f"{text} 不得被判为 Eligible")
                self.assertEqual(v, "Unknown")

    def test_no_sponsorship_vs_need(self):
        p = profile(constraints={"visa": "need_sponsorship_us"})
        self.assertEqual(verdict(opp(nationality_requirement="sponsorship not provided"), p),
                         "Probably Ineligible")


class TestSkillMatching(unittest.TestCase):
    def test_generic_token_does_not_hit(self):
        self.assertFalse(S.skill_hit("data engineering", ["data analysis"]))

    def test_cpp_is_not_c(self):
        self.assertFalse(S.skill_hit("C++", ["C"]))
        self.assertTrue(S.skill_hit("C", ["C/C++"]))

    def test_rtos_family_hits(self):
        self.assertTrue(S.skill_hit("RTOS", ["FreeRTOS"]), "RTOS ↔ FreeRTOS 属高确定性同族")
        self.assertTrue(S.skill_hit("FreeRTOS", ["RTOS"]))
        self.assertTrue(S.skill_hit("RTOS experience", ["FreeRTOS", "Zephyr"]))

    def test_other_families(self):
        self.assertTrue(S.skill_hit("ESP32", ["ESP32-S3"]))
        self.assertTrue(S.skill_hit("javascript", ["Node.js"]))
        self.assertTrue(S.skill_hit("c++", ["cpp"]))

    def test_families_stay_conservative(self):
        """不做概念扩张。"""
        for req, have in [("Docker", ["Kubernetes"]), ("Python", ["Machine Learning"]),
                          ("React", ["Frontend"]), ("C++", ["C"])]:
            with self.subTest(req=req, have=have):
                self.assertFalse(S.skill_hit(req, have))

    def test_unrelated(self):
        self.assertFalse(S.skill_hit("Kubernetes", ["Docker"]))

    def test_version_variant_hits(self):
        self.assertTrue(S.skill_hit("python", ["Python3"]))

    def test_component_rewards_real_overlap(self):
        strong, _ = S.skill_component(opp(skills_required=["Python", "Git", "Linux"]), profile())
        weak, _ = S.skill_component(opp(skills_required=["Kubernetes", "Terraform"]), profile())
        self.assertGreater(strong, weak)


class TestGraduationWindow(unittest.TestCase):
    def test_month_level_window(self):
        w = S.parse_grad_window("2027-09 ~ 2028-06")
        self.assertEqual(S.in_grad_window((2027, 6), w)[0], False)
        self.assertEqual(S.in_grad_window((2028, 3), w)[0], True)

    def test_japanese_march_cohort(self):
        w = S.parse_grad_window("2028 年 3 月卒業見込")
        self.assertEqual(S.in_grad_window((2028, 3), w)[0], True)
        self.assertEqual(S.in_grad_window((2028, 6), w)[0], False, "同一年不同届 → 不在窗口")

    def test_english_window(self):
        w = S.parse_grad_window("Graduating between Sep 2027 and Jun 2028")
        self.assertEqual(S.in_grad_window((2028, 6), w)[0], True)
        self.assertEqual(S.in_grad_window((2028, 7), w)[0], False)

    def test_year_only_lower_confidence(self):
        w = S.parse_grad_window("2027")
        self.assertTrue(w[2])

    def test_unparseable(self):
        self.assertIsNone(S.parse_grad_window("soon"))

    def test_end_to_end_verdict(self):
        o = opp(graduation_window="2027-09 ~ 2028-06", **explicit("graduation_window"))
        p = profile(education={"degree": "undergraduate", "expected_graduation": "2027-06"})
        self.assertEqual(verdict(o, p), "Ineligible", "枚举/日期类无歧义冲突 → Ineligible")
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


class TestDeadlineType(unittest.TestCase):
    def info(self, **kw):
        return S.deadline_info(opp(**kw), TODAY)

    def test_structured_type_is_preserved(self):
        for dtype in ["rolling", "asap", "flexible", "tbd"]:
            with self.subTest(dtype=dtype):
                i = self.info(deadline=None, deadline_type=dtype)
                self.assertEqual(i["type"], dtype, "结构化 deadline_type 不得被重新推断覆盖")
                self.assertIsNone(i["days"], "非日期型不应计算具体天数")

    def test_rolling_is_not_expired_and_flagged_rolling(self):
        res = S.score_all(profile(), [opp(id="r", deadline=None, deadline_type="rolling")], today=TODAY)
        row = res["results"][0]
        self.assertEqual(row["deadline_type"], "rolling")
        self.assertIn("rolling", row["flags"])
        self.assertNotIn("no_deadline", row["flags"])
        self.assertIsNone(row["urgency"])

    def test_tbd_stays_tbd(self):
        res = S.score_all(profile(), [opp(id="t", deadline=None, deadline_type="tbd")], today=TODAY)
        self.assertEqual(res["results"][0]["deadline_type"], "tbd")
        self.assertIn("tbd", res["results"][0]["flags"])

    def test_asap_has_no_fake_urgency(self):
        res = S.score_all(profile(), [opp(id="a", deadline=None, deadline_type="asap")], today=TODAY)
        self.assertIsNone(res["results"][0]["urgency"])
        self.assertIn("asap", res["results"][0]["flags"])

    def test_fixed_parses_dates(self):
        i = self.info(deadline="2026-09-20", deadline_type="fixed")
        self.assertEqual(i["type"], "fixed")
        self.assertEqual(i["days"], 6)

    def test_range_uses_endpoint(self):
        i = self.info(deadline="2026-09-20 ~ 2026-10-05", deadline_type="range")
        self.assertEqual(i["days"], 21)

    def test_raw_fallback_when_field_absent(self):
        i = self.info(deadline="2026-09-20")
        self.assertEqual(i["type"], "fixed")
        self.assertEqual(i["days"], 6)

    def test_expired_is_excluded_regardless_of_evidence(self):
        """Freshness Gate：过期项一律排除；Evidence Gate 只约束资格判定（F01/F02）。"""
        for opp_kw in (inferred("deadline"), explicit("deadline"), {}):
            o = opp(id="g", deadline="2026-01-01", **opp_kw)
            res = S.score_all(profile(), [o], today=TODAY)
            with self.subTest(evidence=opp_kw.get("evidence")):
                self.assertEqual(res["scored"], 0)
                self.assertTrue(res["excluded"])


class TestHours(unittest.TestCase):
    def test_explicit_hour_forms(self):
        for text, expect in [("20h/week", 20.0), ("20 hours per week", 20.0),
                             ("每周 15 小时", 15.0), ("週20時間", 20.0),
                             ("10 h/week", 10.0), ("20 hours", 20.0)]:
            with self.subTest(text=text):
                self.assertEqual(S.parse_hours(text), expect)

    def test_non_hour_forms_return_none(self):
        for text in ["3 months full-time", "part-time", "full-time", "2 days/week",
                     "40 hours/month", "6 ヶ月"]:
            with self.subTest(text=text):
                self.assertIsNone(S.parse_hours(text), f"{text!r} 不得被当成每周小时数")

    def test_no_false_heavy_load(self):
        p = profile(constraints={"weekly_time": 15})
        row = S.score_all(p, [opp(id="x", time_commitment="3 months full-time")], today=TODAY)
        self.assertNotIn("heavy_load", row["results"][0]["flags"])


class TestSchoolAndLocation(unittest.TestCase):
    def test_school_word_boundary(self):
        self.assertFalse(S.school_match("MIT", "Open to admitted students only"),
                         "MIT 不应命中 admitted 内部的 mit")
        self.assertTrue(S.school_match("MIT", "Enrolled at MIT"))
        self.assertTrue(S.school_match("Kagura University", "Enrolled at Kagura University"))
        self.assertTrue(S.school_match("清华大学", "仅限清华大学在读学生"))

    def test_school_check_states(self):
        self.assertEqual(S.school_check(opp(school_requirement="Enrolled at MIT"), profile())[0],
                         "unknown_missing")
        p = profile(education={"school": "Kagura University"})
        self.assertEqual(S.school_check(opp(school_requirement="Kagura University students"), p)[0], "ok")
        q = profile(education={"school": "Alpha University"})
        self.assertEqual(S.school_check(opp(school_requirement="Kagura University students"), q)[0],
                         "unknown_low_info", "无法确认时不得推断为不符合")

    def test_country_canonicalization(self):
        for text in ["US", "USA", "United States", "united states of america", "美国"]:
            with self.subTest(text=text):
                self.assertEqual(canonical_country(text), "us")
        self.assertEqual(canonical_country("UK"), "uk")
        self.assertEqual(canonical_country("Japan"), "japan")
        self.assertIsNone(canonical_country("Belarus"))
        self.assertIsNone(canonical_country(""))

    def test_short_country_does_not_substring_match(self):
        p = profile(constraints={"preferred_country": ["United States"], "remote": False})
        score, note = S.location_component(opp(country="Belarus"), p)
        self.assertNotEqual(score, 95.0, "Belarus 不得因为包含 us 而被判为美国")
        self.assertIn("无法与偏好列表比对", note)

    def test_mismatched_country_scores_low(self):
        p = profile(constraints={"preferred_country": ["United States"], "remote": False})
        score, note = S.location_component(opp(country="Japan"), p)
        self.assertEqual(score, 25.0)
        self.assertIn("不在偏好列表", note)

    def test_country_match(self):
        p = profile(constraints={"preferred_country": ["Japan"]})
        self.assertEqual(S.location_component(opp(country="JP"), p)[0], 95.0)

    def test_unrecognised_country_is_neutral(self):
        p = profile(constraints={"preferred_country": ["Japan"], "remote": False})
        self.assertEqual(S.location_component(opp(country="Someplace"), p)[0], 55.0)


class TestProvenanceIsolation(unittest.TestCase):
    def test_inferred_pending_fields_do_not_affect_eligibility(self):
        p = profile(nationality="Chinese",
                    **{"_provenance": {"education.expected_graduation": "inferred_pending",
                                       "education.current_year": "inferred_pending",
                                       "nationality": "inferred_pending"}})
        o = opp(graduation_window="2028-03", **explicit("graduation_window"))
        safe, stripped = S.filter_profile_for_eligibility(p)
        self.assertIn("education.expected_graduation", stripped)
        self.assertIn("nationality", stripped)
        _, v, _, _, _, _, warns = S.eligibility_component(o, safe, TODAY, stripped)
        self.assertEqual(v, "Unknown", "推断出来的毕业时间不得导致淘汰")
        self.assertTrue(any("inferred_pending" in w for w in warns))

    def test_user_stated_fields_still_work(self):
        p = profile(education={"degree": "undergraduate", "expected_graduation": "2027-06"},
                    **{"_provenance": {"education.expected_graduation": "user_confirmed"}})
        o = opp(graduation_window="2027-09 ~ 2028-06", **explicit("graduation_window"))
        safe, stripped = S.filter_profile_for_eligibility(p)
        self.assertEqual(stripped, [])
        self.assertEqual(S.eligibility_component(o, safe, TODAY, stripped)[1], "Ineligible")

    def test_top_level_source_applies_to_all(self):
        p = profile(**{"_source": "inferred_pending"})
        _, stripped = S.filter_profile_for_eligibility(p)
        self.assertIn("education.degree", stripped)

    def test_scoring_components_still_use_full_profile(self):
        """排序/兴趣类分项可以继续使用推断信息。"""
        p = profile(interests=["security"], **{"_source": "inferred_pending"})
        res = S.score_all(p, [opp(id="s", tags=["security", "open_source"])], today=TODAY)
        self.assertGreater(res["scored"], 0)
        self.assertGreater(res["results"][0]["components"]["interest_fit"], 55)


class TestScoringPipeline(unittest.TestCase):
    def test_priority_uses_deadline_endpoint(self):
        near = S.score_all(profile(), [opp(id="n", deadline="2026-09-20 ~ 2026-10-05")], today=TODAY)
        far = S.score_all(profile(), [opp(id="f", deadline="2027-09-20 ~ 2027-10-05")], today=TODAY)
        self.assertGreater(near["results"][0]["priority_score"], far["results"][0]["priority_score"])
        self.assertEqual(near["results"][0]["days_remaining"], 21)

    def test_expired_excluded(self):
        res = S.score_all(profile(), [opp(id="e", deadline="2026-01-01")], today=TODAY)
        self.assertEqual(res["scored"], 0)
        self.assertEqual(len(res["excluded"]), 1)

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
        prof = json.load(open(_helpers.path("examples", "profiles", "cs-student.example.json"),
                              encoding="utf-8"))
        opps = json.load(open(_helpers.path("examples", "opportunity.batch.example.json"),
                              encoding="utf-8"))["opportunities"]
        res = S.score_all(prof, opps, today=TODAY)
        self.assertGreater(res["scored"], 0)
        self.assertEqual(res["contract_issues"], [])
        verdicts = {r["eligibility_verdict"] for r in res["results"]}
        self.assertTrue(verdicts <= set(S.VERDICT_SCORE), verdicts)


class TestEvidenceGaps(unittest.TestCase):
    def test_gaps_reported(self):
        o = opp(evidence={"deadline": {"status": "unknown"},
                          "language_requirement": {"status": "inferred"},
                          "major_requirement": {"status": "explicit"}})
        gaps = S.evidence_gaps(o)
        self.assertTrue(any("deadline" in g for g in gaps))
        self.assertTrue(any("language_requirement" in g for g in gaps))
        self.assertTrue(any("major_requirement" in g for g in gaps), "explicit 但缺 source_url 也应提示")


class TestEvidencePrecondition(unittest.TestCase):
    """P0：证据不完整时，任何 Match/Utility 都不能让它进主推荐。"""

    def _run(self, **extra):
        base = {"id": "e", "deadline": "2026-10-03", "official_url": "https://a.example",
                "education_level": ["undergraduate"]}
        base.update(extra)
        return S.score_all(profile(), [opp(**base)], today=dt.date(2026, 9, 14))["results"][0]

    def test_without_application_status_evidence(self):
        row = self._run(verification_status="verified_official")
        self.assertEqual(row["zone"], "worth_verifying")
        self.assertIn("evidence_incomplete", row["flags"])
        self.assertEqual(row["demotion"]["code"], "missing_evidence_structure")

    def test_stale_evidence_is_incomplete(self):
        row = self._run(verification_status="verified_official", application_status="open",
                        evidence={"application_status": {"status": "explicit",
                                                         "source_url": "https://a.example",
                                                         "verified_at": "2026-01-01"}})
        self.assertFalse(row["evidence_complete"])
        self.assertEqual(row["zone"], "worth_verifying")

    def test_complete_evidence_can_recommend(self):
        row = self._run(verification_status="verified_official", application_status="open",
                        evidence={"application_status": {"status": "explicit",
                                                         "source_url": "https://a.example",
                                                         "verified_at": "2026-09-13"}})
        self.assertTrue(row["evidence_complete"])
        self.assertTrue(row["actionable"])
        self.assertEqual(row["zone"], "recommended_now")

    def test_evergreen_needs_participation_evidence(self):
        """evergreen ≠ verified open：没有当前参与证据时不得进主推荐。"""
        row = self._run(deadline=None, deadline_type="evergreen")
        self.assertEqual(row["freshness"], "evergreen")
        self.assertFalse(row["actionable"])
        self.assertEqual(row["zone"], "worth_verifying")


class TestFreshnessGate(unittest.TestCase):
    """F01/F02：已结束的机会不得因为 deadline=null 或赛季未解析而进入推荐。"""

    def T(self, o, today=dt.date(2026, 9, 14)):
        return S.score_all(profile(), [o], today=today)

    def test_deadline_in_future_is_open(self):
        r = self.T(opp(id="a", deadline="2026-10-03", official_url="https://x.example"))
        self.assertEqual(r["results"][0]["freshness"], "open")

    def test_deadline_past_is_excluded(self):
        r = self.T(opp(id="b", deadline="2026-04-20", official_url="https://x.example"))
        self.assertEqual(r["scored"], 0)
        self.assertIn("expired", r["excluded"][0]["reason"])

    def test_past_season_without_deadline_is_excluded(self):
        """2026 赛季 + 当前 9 月 + 无 deadline → closed（F01）。"""
        r = self.T(opp(id="c", title="Summer 2026 Research Program", deadline=None,
                       official_url="https://x.example"))
        self.assertEqual(r["scored"], 0)
        self.assertIn("closed", r["excluded"][0]["reason"])

    def test_event_end_passed_is_excluded(self):
        r = self.T(opp(id="d", title="Conference", event_end="2026-07-01",
                       official_url="https://x.example"))
        self.assertEqual(r["scored"], 0)

    def test_unknown_freshness_is_not_recommended_now(self):
        r = self.T(opp(id="e", title="Some program", deadline=None,
                       official_url="https://x.example"))
        row = r["results"][0]
        self.assertEqual(row["freshness"], "unknown")
        self.assertEqual(row["zone"], "worth_verifying")

    def test_future_cycle_is_not_recommended_now(self):
        r = self.T(opp(id="f", title="Global Game Jam 2027", deadline=None,
                       official_url="https://x.example"))
        self.assertEqual(r["results"][0]["zone"], "worth_verifying")

    def test_rolling_is_likely_open(self):
        r = self.T(opp(id="g", deadline=None, deadline_type="rolling",
                       official_url="https://x.example"))
        self.assertEqual(r["results"][0]["freshness"], "likely_open")


class TestCanonicalSourceGate(unittest.TestCase):
    """F03/F04：没有官方来源的结果不得进入 Recommended now。"""

    def T(self, o):
        return S.score_all(profile(), [o], today=dt.date(2026, 9, 14))

    def verified(self, o):
        """官方已核实 + 当前状态证据（V3 起：只有 deadline 证据不够）。"""
        o["verification_status"] = "verified_official"
        o["application_status"] = "open"
        o["last_verified"] = "2026-09-14"
        o["evidence"] = {"deadline": {"status": "explicit", "source_url": o["official_url"],
                                      "verified_at": "2026-09-14"},
                         "application_status": {"status": "explicit",
                                                "source_url": o["official_url"],
                                                "verified_at": "2026-09-14"}}
        return o

    def test_official_url_present_can_be_recommended(self):
        r = self.T(self.verified(opp(id="a", deadline="2026-10-03", official_url="https://official.example/jobs",
                                     education_level=["undergraduate"])))
        self.assertNotIn("no_canonical_source", r["results"][0]["flags"])
        self.assertEqual(r["results"][0]["zone"], "recommended_now")

    def test_aggregator_only_goes_to_worth_verifying(self):
        r = self.T(opp(id="b", deadline="2026-10-03", official_url=None,
                       discovery_url="https://aggregator.example/p/1",
                       education_level=["undergraduate"]))
        row = r["results"][0]
        self.assertIn("no_canonical_source", row["flags"])
        self.assertEqual(row["zone"], "worth_verifying")
        self.assertTrue(any("官方来源" in w for w in row["warnings"]))

    def test_no_expired_and_no_unverified_leakage_into_recommendations(self):
        """两个 hard quality gate：expired leakage = 0，unverified leakage = 0。"""
        opps = [self.verified(opp(id="ok", deadline="2026-10-03", official_url="https://a.example")),
                opp(id="exp", deadline="2026-04-01", official_url="https://b.example"),
                opp(id="agg", deadline="2026-10-03", official_url=None)]
        r = S.score_all(profile(), opps, today=dt.date(2026, 9, 14))
        recs = [x for x in r["results"] if x["zone"] == "recommended_now"]
        self.assertTrue(recs)
        self.assertEqual([x for x in recs if x["freshness"] in ("closed", "expired")], [])
        self.assertEqual([x for x in recs if "no_canonical_source" in x["flags"]], [])

    def test_zone_filter(self):
        r = S.score_all(profile(), [self.verified(opp(id="ok", deadline="2026-10-03",
                                                      official_url="https://a.example")),
                                    opp(id="agg", deadline="2026-10-03", official_url=None)],
                        today=dt.date(2026, 9, 14))
        self.assertEqual(r["zones"]["recommended_now"] >= 1, True)
        self.assertEqual(r["zones"]["worth_verifying"] >= 1, True)


if __name__ == "__main__":
    unittest.main()
