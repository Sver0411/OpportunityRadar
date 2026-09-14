"""common.py 的测试：URL 规范化、ID 契约、周期冲突、轻量 contract 校验。"""

from __future__ import annotations

import unittest

import _helpers

from common import (
    CATEGORIES, canonical_url, cycle_parts, cycles_conflict, derive_id, ensure_id,
    extract_cycle, is_same_url, validate_opportunity, validate_profile,
)


class TestCanonicalUrl(unittest.TestCase):
    def test_host_lowercased_path_case_preserved(self):
        self.assertEqual(canonical_url("https://WWW.Example.COM/Path/To/Page"),
                         "example.com/Path/To/Page")

    def test_case_sensitive_paths_stay_distinct(self):
        a = canonical_url("https://x.example/docs/API")
        b = canonical_url("https://x.example/docs/api")
        self.assertNotEqual(a, b, "路径大小写敏感，不能被规范化掉")

    def test_tracking_params_removed(self):
        a = canonical_url("https://x.example/p?utm_source=a&utm_medium=b&gclid=1")
        b = canonical_url("https://x.example/p")
        self.assertEqual(a, b)

    def test_meaningful_params_kept(self):
        """ref / source / from 可能承载路由语义，必须保留。"""
        for param in ("ref=wechat", "source=nav", "from=list"):
            with self.subTest(param=param):
                self.assertIn(param.split("=")[0], canonical_url(f"https://x.example/p?{param}"))

    def test_query_order_and_fragment_normalized(self):
        a = canonical_url("https://x.example/p?b=2&a=1#section")
        b = canonical_url("https://x.example/p?a=1&b=2")
        self.assertEqual(a, b)

    def test_trailing_slash_and_www(self):
        self.assertEqual(canonical_url("https://www.x.example/p/"), canonical_url("https://x.example/p"))

    def test_scheme_insensitive(self):
        self.assertTrue(is_same_url("http://x.example/p", "https://x.example/p"))

    def test_invalid(self):
        self.assertIsNone(canonical_url(None))
        self.assertIsNone(canonical_url(""))
        self.assertIsNone(canonical_url("not a url"))
        self.assertIsNone(canonical_url("随便一段中文"))
        self.assertIsNone(canonical_url("http://"))
        # 无 scheme 的裸域名仍然可用
        self.assertEqual(canonical_url("example.com/p"), "example.com/p")


class TestIdContract(unittest.TestCase):
    def test_stable(self):
        rec = {"title": "Sony Embedded Systems Internship 2027", "organization": "Sony"}
        self.assertEqual(derive_id(rec), derive_id(dict(rec)))

    def test_same_opportunity_same_cycle_same_id(self):
        a = {"title": "Sony Summer Internship 2027", "organization": "Sony"}
        b = {"title": "Sony Summer Internship 2027", "organization": "Sony Inc."}
        self.assertEqual(derive_id(a), derive_id(b), "机构后缀差异不应产生不同 ID")

    def test_different_cycle_different_id(self):
        a = {"title": "Sony Summer Internship 2026", "organization": "Sony"}
        b = {"title": "Sony Summer Internship 2027", "organization": "Sony"}
        self.assertNotEqual(derive_id(a), derive_id(b), "不同年份必须是不同 ID")

    def test_cjk_id_is_legal(self):
        oid = derive_id({"title": "清华大学 暑期科研 2027", "organization": "清华大学"})
        self.assertTrue(oid)
        self.assertNotIn(oid, ("unknown-opportunity",))
        rec = {"id": oid, "title": "t", "organization": "o", "primary_category": "research"}
        self.assertEqual(validate_opportunity(rec), [], "CJK ID 必须通过 contract 校验")

    def test_org_not_duplicated(self):
        self.assertNotIn("清华-清华大学", derive_id({"title": "清华大学暑期科研", "organization": "清华大学"}))

    def test_ensure_id_repairs_invalid(self):
        rec = {"id": "Has Space", "title": "X Program 2026", "organization": "Org",
               "primary_category": "career"}
        ensure_id(rec)
        self.assertNotEqual(rec["id"], "Has Space")
        self.assertEqual(validate_opportunity(rec), [])

    def test_fallback_when_nothing_usable(self):
        oid = derive_id({"title": "★★★", "organization": "★★"})
        self.assertTrue(oid.startswith("opportunity-"), oid)


class TestCycle(unittest.TestCase):
    def test_parts_and_key(self):
        rec = {"title": "Sony Summer Internship 2027", "organization": "Sony"}
        self.assertEqual(cycle_parts(rec), (("2027",), "summer"))
        self.assertEqual(extract_cycle(rec), "2027-summer")

    def test_year_conflict(self):
        a = {"title": "Sony Internship 2026"}
        b = {"title": "Sony Internship 2027"}
        self.assertEqual(cycles_conflict(a, b), (True, "year_differs"))

    def test_season_conflict(self):
        a = {"title": "Sony Summer Internship 2027"}
        b = {"title": "Sony Winter Internship 2027"}
        self.assertEqual(cycles_conflict(a, b), (True, "season_differs"))

    def test_season_asymmetry_is_not_conflict(self):
        """"Summer 2027" 与 "2027" 是同一周期，不能判冲突。"""
        a = {"title": "Sony Summer Internship 2027"}
        b = {"title": "Sony Internship 2027"}
        self.assertEqual(cycles_conflict(a, b), (False, ""))

    def test_missing_cycle_info_is_not_conflict(self):
        a = {"title": "Sony Internship"}
        b = {"title": "Sony Internship 2027"}
        self.assertEqual(cycles_conflict(a, b), (False, ""))


class TestContractValidation(unittest.TestCase):
    def base(self, **kw):
        rec = {"id": "x-2026", "title": "t", "organization": "o", "primary_category": "career"}
        rec.update(kw)
        return rec

    def test_valid(self):
        self.assertEqual(validate_opportunity(self.base()), [])

    def test_missing_required(self):
        self.assertTrue(validate_opportunity({"title": "t"}))

    def test_bad_enum(self):
        self.assertTrue(validate_opportunity(self.base(primary_category="jobs")))
        self.assertTrue(validate_opportunity(self.base(trust_tier="E")))
        self.assertTrue(validate_opportunity(self.base(verification_status="maybe")))
        self.assertTrue(validate_opportunity(self.base(secondary_categories=["career", "nope"])))

    def test_bad_id_pattern(self):
        self.assertTrue(validate_opportunity(self.base(id="Has Space")))

    def test_bad_date(self):
        self.assertTrue(validate_opportunity(self.base(deadline="next month")))
        self.assertEqual(validate_opportunity(self.base(deadline="2026-10")), [])
        self.assertEqual(validate_opportunity(self.base(deadline="2026-10-03")), [])

    def test_evidence_status(self):
        self.assertEqual(validate_opportunity(self.base(evidence={"deadline": {"status": "explicit"}})), [])
        self.assertTrue(validate_opportunity(self.base(evidence={"deadline": {"status": "maybe"}})))

    def test_verdict_names(self):
        self.assertEqual(validate_opportunity(self.base(eligibility={"verdict": "Probably Eligible"})), [])
        self.assertTrue(validate_opportunity(self.base(eligibility={"verdict": "Yes"})))

    def test_profile_goals(self):
        self.assertEqual(validate_profile({"goals": [{"type": "internship"}]}), [])
        self.assertTrue(validate_profile({"goals": [{"type": "job"}]}))

    def test_categories_single_source(self):
        self.assertEqual(len(CATEGORIES), 13)


if __name__ == "__main__":
    unittest.main()
