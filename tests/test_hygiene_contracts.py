"""Pre-user-test hygiene contracts: local state, benchmark status semantics, SI provenance."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import common as C      # noqa: E402
import sources as SI    # noqa: E402

BM = os.path.join(ROOT, "benchmarks")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class TestLocalStateContract(unittest.TestCase):
    def test_docs_list_every_allowed_state_file(self):
        """文档必须与 common.STATE_FILES 一致，否则实现与 contract 会漂移。"""
        skill = read("SKILL.md")
        state_doc = read("references/state-and-feedback.md")
        for name in C.STATE_FILES:
            with self.subTest(file=name):
                self.assertIn(name, skill, f"SKILL.md 未列出 {name}")
                self.assertIn(name, state_doc, f"state-and-feedback.md 未列出 {name}")

    def test_sources_state_fields_are_documented_and_limited(self):
        for field in C.SOURCE_STATE_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, read("references/state-and-feedback.md"))
        banned = ("content", "page_text", "search_results", "email", "token", "password")
        for b in banned:
            self.assertNotIn(f'"{b}"', " ".join(C.SOURCE_STATE_FIELDS))

    def test_yield_writer_only_writes_allowed_fields(self):
        with tempfile.TemporaryDirectory() as d:
            SI.record_yield(d, "https://lab.example", category="research", region="Japan",
                            outcome="actionable")
            with open(os.path.join(d, "sources.json"), encoding="utf-8") as fh:
                data = json.load(fh)
            entry = next(iter(data["entries"].values()))
            self.assertEqual(set(entry), set(C.SOURCE_STATE_FIELDS))

    def test_state_dir_name_is_single_sourced(self):
        self.assertEqual(C.STATE_DIR, ".opportunity-radar")
        self.assertIn(C.STATE_DIR, read("SKILL.md"))


class TestBenchmarkStatusSemantics(unittest.TestCase):
    """历史快照与当前状态必须分开且都可机器读取。"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(BM, "known_failures.json"), encoding="utf-8") as fh:
            cls.known = json.load(fh)
        with open(os.path.join(BM, "gates.json"), encoding="utf-8") as fh:
            cls.gates = json.load(fh)
        with open(os.path.join(BM, "_metrics-stabilization.json"), encoding="utf-8") as fh:
            cls.stab = json.load(fh)

    def test_active_failures_zero_means_current_all_pass(self):
        active = self.known.get("known_failures", [])
        current_all_pass = not active
        self.assertEqual(current_all_pass, len(active) == 0)
        self.assertEqual(current_all_pass, True, "active 为空时 current_all_pass 必须为 True")
        # 机器可读：current 状态单独存放
        self.assertIn("personas", self.stab)
        iot = self.stab["personas"]["iot-embedded"]
        self.assertGreaterEqual(iot["final_verification_pct"], 80)
        self.assertEqual(iot["expired_leakage"], 0)
        self.assertEqual(iot["unverified_actionable_leakage"], 0)

    def test_historical_snapshot_preserved_not_rewritten(self):
        """round-2 的 67% 必须原样保留，只允许加 resolved 标记。"""
        hist = self.gates["gates"]["iot-embedded"]["final_verification_pct"]
        self.assertEqual(hist, 67, "历史快照不得改写")
        statuses = {f["status"] for f in self.gates["failures"]}
        self.assertIn("resolved", statuses)
        self.assertFalse(self.gates["all_pass"], "历史快照的 all_pass 反映当时状态")

    def test_resolved_entry_keeps_history(self):
        for f in self.known.get("resolved_failures", []):
            with self.subTest(persona=f["persona"]):
                for key in ("old_value", "new_value", "threshold", "root_cause", "fix",
                            "resolved_at", "failure_classification"):
                    self.assertIn(key, f)


class TestSourceProvenance(unittest.TestCase):
    def test_stage_override_queries_do_not_fake_a_family(self):
        for profile in ({"life_stage": ["working"]}, {"life_stage": ["student"],
                                                      "career_stage": ["undergraduate"]}):
            qs = SI.plan_queries({"type": "research", "name": "研究经历"}, profile,
                                 topic="Edge AI", region="Japan", limit=8)
            for q in qs:
                if q.get("family") is None:
                    continue
                # 有 family 的 query 必须真的含该 family 的领域词
                markers = SI.FAMILY_QUERY_MARKERS.get(q["family"], ())
                self.assertTrue(any(m in q["query"].lower() for m in markers),
                                f"{q['query'][:40]} 与 family={q['family']} 不匹配")

    def test_no_hardcoded_year_in_current_markers(self):
        """CURRENT_MARKERS 不得写死年份（否则会自然过期）。"""
        for m in SI.CURRENT_MARKERS:
            with self.subTest(marker=m):
                self.assertIsNone(re.search(r"\b(?:19|20)\d{2}\b", m),
                                  f"marker {m} 含硬编码年份")

    def test_next_year_detection_is_dynamic(self):
        today = dt.date(2026, 9, 20)
        page = {"title": "Programme", "summary": f"intake {today.year + 1}"}
        self.assertEqual(SI.source_freshness(page, today)["source_freshness"], "current")
        past = {"title": "Programme", "summary": f"intake {today.year - 2}"}
        self.assertEqual(SI.source_freshness(past, today)["source_freshness"], "historical")


if __name__ == "__main__":
    unittest.main()
