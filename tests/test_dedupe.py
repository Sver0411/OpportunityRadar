"""dedupe.py 的测试：周期守卫、URL 规范化、链式误合并防护、冲突报告。"""

from __future__ import annotations

import json
import unittest

import _helpers

import dedupe as D


def rec(oid, title, org, url=None, **kw):
    r = {"id": oid, "title": title, "organization": org,
         "primary_category": kw.pop("primary_category", "career"),
         "trust_tier": kw.pop("trust_tier", "C"), "official_url": url}
    r.update(kw)
    return r


class TestBasics(unittest.TestCase):
    def test_same_cycle_same_url_merges(self):
        a = rec("a", "Nagi Robotics Summer Internship 2027", "Nagi Robotics",
                "https://nagi.example/students/summer?utm_source=x")
        b = rec("b", "2027 Summer Internship Program", "Nagi Robotics, Inc.",
                "https://nagi.example/students/summer/")
        res = D.dedupe([a, b])
        self.assertEqual(res["cluster_count"], 1, "同一 URL（仅 utm/尾斜杠差异）应合并")
        self.assertEqual(res["clusters"][0]["size"], 2)

    def test_different_year_same_url_does_not_merge(self):
        a = rec("a", "Alpha Robotics Summer Internship 2026", "Alpha Robotics",
                "https://alpha.example/program")
        b = rec("b", "Alpha Robotics Summer Internship 2027", "Alpha Robotics",
                "https://alpha.example/program")
        res = D.dedupe([a, b])
        self.assertEqual(res["cluster_count"], 2, "同一 URL 的跨年项目必须保持独立")
        self.assertTrue(res["cycle_variants"], "应报出周期差异供人工确认")

    def test_same_title_different_org_does_not_merge(self):
        a = rec("a", "Embedded Systems Internship 2027", "Alpha Robotics", "https://alpha.example/x")
        b = rec("b", "Embedded Systems Internship 2027", "Beta Aerospace", "https://beta.example/x")
        res = D.dedupe([a, b])
        self.assertEqual(res["cluster_count"], 2)

    def test_tracking_url_variants_merge(self):
        a = rec("a", "Gamma Lab Research Program 2026", "Gamma Lab", "https://gamma.example/rp")
        b = rec("b", "Gamma Lab Research Program 2026", "Gamma Lab",
                "https://www.gamma.example/rp/?gclid=1&utm_campaign=spring")
        self.assertEqual(D.dedupe([a, b])["cluster_count"], 1)

    def test_case_sensitive_paths_stay_distinct(self):
        a = rec("a", "Delta Program 2026", "Delta", "https://delta.example/Program")
        b = rec("b", "Delta Program 2026", "Delta", "https://delta.example/program")
        self.assertNotEqual(D.canonical_url(a["official_url"]), D.canonical_url(b["official_url"]))


class TestChainGuard(unittest.TestCase):
    """Union-Find 单链：A~B、B~C 成立但 A~C 不成立时不得合并成一个簇。"""

    def setUp(self):
        self.a = rec("alpha-2026", "Alpha Robotics Embedded Systems Internship 2026",
                     "Alpha Robotics", "https://alpha.example/programs", trust_tier="A")
        self.b = rec("alpha-generic", "Alpha Robotics Embedded Systems Internship",
                     "Alpha Robotics", "https://alpha.example/programs")
        self.c = rec("alpha-2027", "Alpha Robotics Embedded Systems Internship 2027",
                     "Alpha Robotics", "https://other.example/alpha")

    def test_links_exist(self):
        self.assertGreaterEqual(D.pair_score(self.a, self.b)[0], 0.72)
        self.assertGreaterEqual(D.pair_score(self.b, self.c)[0], 0.72)

    def test_cycle_guard_blocks_direct_link(self):
        score, detail = D.pair_score(self.a, self.c)
        self.assertLess(score, 0.72)
        self.assertEqual(detail.get("reason"), "different_cycle")

    def test_coherence_prevents_chain_merge(self):
        res = D.dedupe([self.a, self.b, self.c])
        merged = [set(c["member_ids"]) for c in res["clusters"]]
        self.assertNotIn({"alpha-2026", "alpha-generic", "alpha-2027"}, merged,
                         "不同年份的机会不应经中间记录被链式合并")
        self.assertTrue(res["ejected_by_coherence"], "应记录被一致性检查剔出的成员")


class TestConflicts(unittest.TestCase):
    def test_deadline_conflict_reported(self):
        a = rec("a", "Nagi Robotics Summer Internship 2027", "Nagi Robotics",
                "https://nagi.example/students/summer", trust_tier="C",
                deadline="2026-10-17")
        b = rec("b", "2027 Summer Internship Program", "Nagi Robotics",
                "https://nagi.example/students/summer/", trust_tier="A",
                deadline="2026-10-03")
        res = D.dedupe([a, b])
        self.assertEqual(res["cluster_count"], 1)
        fields = {c["field"] for c in res["clusters"][0]["conflicts"]}
        self.assertIn("deadline", fields)
        self.assertEqual(res["clusters"][0]["canonical_id"], "b", "canonical 应选信任层级最高者")

    def test_maybe_pairs_left_for_review(self):
        a = rec("a", "Tokyo Embedded Challenge 2026", "Tokyo Embedded Association",
                "https://t.example/c", country="Japan", primary_category="competition")
        b = rec("b", "Tokyo Embedded Design Contest 2026", "Metropolitan Foundation",
                None, country="Japan", primary_category="competition")
        res = D.dedupe([a, b])
        self.assertEqual(res["cluster_count"], 2, "机构不同不应自动合并")
        self.assertTrue(res["maybe_pairs"], "应作为疑似重复交模型复核")


class TestExampleBatch(unittest.TestCase):
    def test_batch_runs_and_removes_duplicates(self):
        recs = json.load(open(_helpers.path("examples", "opportunity.batch.example.json"),
                              encoding="utf-8"))["opportunities"]
        res = D.dedupe(recs)
        self.assertLess(res["cluster_count"], res["input_count"])
        self.assertTrue(any(c["size"] >= 2 for c in res["clusters"]))

    def test_cluster_ids_are_stable(self):
        recs = json.load(open(_helpers.path("examples", "opportunity.batch.example.json"),
                              encoding="utf-8"))["opportunities"]
        self.assertEqual(D.dedupe(recs)["cluster_count"], D.dedupe(recs)["cluster_count"])


if __name__ == "__main__":
    unittest.main()
