"""Benchmark consistency: gate numbers + report claims must come from real data.

Rules enforced:
1. `gates.json` must equal the values recomputed from `_metrics-v2.json` (no drift).
2. Every failing gate must be declared in `known_failures.json` (nothing fails silently).
3. `REPORT.md` must not claim "all gates passed" / "全部达标" while `all_pass` is false.
4. Thresholds must never be lowered to make a report look better: the threshold file is
   the source of truth and the test compares against it.
"""

from __future__ import annotations

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BM = os.path.join(ROOT, "benchmarks")


def _load(name):
    with open(os.path.join(BM, name), encoding="utf-8") as fh:
        return json.load(fh)


class TestBenchmarkGates(unittest.TestCase):
    def setUp(self):
        self.metrics = _load("_metrics-v2.json")
        self.gates = _load("gates.json")
        self.known = _load("known_failures.json")
        with open(os.path.join(BM, "REPORT.md"), encoding="utf-8") as fh:
            self.report = fh.read()

    # 1) 数据不漂移
    def test_gates_match_metrics(self):
        for pid, row in self.metrics.items():
            g = row.get("gates", {})
            rec_n = g.get("rec_n", 0)
            with self.subTest(persona=pid):
                self.assertEqual(self.gates["gates"][pid]["expired_leakage"], g.get("rec_expired", 0))
                self.assertEqual(self.gates["gates"][pid]["unverified_actionable_leakage"],
                                 g.get("rec_unverified", 0))
                expected_pct = round(100.0 * g.get("rec_verified", 0) / rec_n) if rec_n else 0
                self.assertEqual(self.gates["gates"][pid]["final_verification_pct"], expected_pct)

    # 2) 失败必须显式声明
    def test_failures_are_declared(self):
        declared = {(f["persona"], f["gate"]) for f in self.known["known_failures"]}
        for f in self.gates["failures"]:
            with self.subTest(persona=f["persona"], gate=f["gate"]):
                self.assertIn((f["persona"], f["gate"]), declared,
                              f"未声明的失败指标：{f['persona']} / {f['gate']} = {f['value']}")

    def test_all_pass_flag_is_consistent(self):
        self.assertEqual(self.gates["all_pass"], not self.gates["failures"])

    # 3) 报告文字不得与数据矛盾
    def test_report_does_not_overclaim(self):
        if not self.gates["all_pass"]:
            banned = ("全部 hard quality gates 达标", "all hard quality gates 达标",
                      "全部达标", "all gates passed", "All hard gates passed",
                      "All hard quality gates passed")
            for phrase in banned:
                with self.subTest(phrase=phrase):
                    self.assertNotIn(phrase, self.report,
                                     f"存在失败指标，报告不得声称「{phrase}」")

    def test_report_mentions_failing_values(self):
        for f in self.gates["failures"]:
            with self.subTest(persona=f["persona"], gate=f["gate"]):
                self.assertIn(str(f["value"]), self.report,
                              "报告必须写出该指标的真实数值")

    # 4) 阈值来自文件，且不低于既定 SLA
    def test_thresholds_are_not_relaxed(self):
        t = self.gates["thresholds"]
        self.assertEqual(t["expired_leakage_max"], 0)
        self.assertEqual(t["unverified_actionable_leakage_max"], 0)
        self.assertGreaterEqual(t["final_verification_pct_min"], 80)
        self.assertGreaterEqual(t["radar_only_useful_min"], 2)


if __name__ == "__main__":
    unittest.main()
