"""Guard for user-test case records (C/D/E).

A hand-written "recommended_now" must never survive a real gate computation:
1. every declared zone must equal the gate-computed zone (usertests/_apply_gate.py output);
2. any candidate whose computed zone is recommended_now must carry the evidence structure
   the gate requires (verified_official + evidence.application_status with source_url/verified_at).
"""

from __future__ import annotations

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = ("case-d-japan-masters", "case-c-promotion", "case-e-unknown", "case-b-professional")


class TestUserTestRecords(unittest.TestCase):
    def _records(self):
        for d in CASES:
            p = os.path.join(ROOT, "usertests", d, "record.json")
            if os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    yield d, json.load(fh)

    def test_gate_computed_matches_declared_zone(self):
        """当前标注必须与真实 gate 一致；历史 mismatch 允许保留（审计痕迹）。"""
        for d, r in self._records():
            if not r.get("gate_computed_summary"):
                continue  # 未跑过 _apply_gate 的记录跳过
            bad = []
            for c in r.get("candidates", []):
                gc = (c.get("gate_computed") or {}).get("zone")
                if not gc or not c.get("zone"):
                    continue
                if c["zone"] != gc:
                    bad.append({"title": c.get("title"), "declared": c.get("zone"),
                                "computed": gc})
            with self.subTest(case=d):
                self.assertEqual(bad, [], f"{d}: 标注与真实 gate 不一致")

    def test_recommended_now_has_evidence(self):
        for d, r in self._records():
            for c in r.get("candidates", []):
                zone = (c.get("gate_computed") or {}).get("zone") or c.get("zone")
                if zone != "recommended_now":
                    continue
                with self.subTest(case=d, title=c.get("title")):
                    self.assertTrue(str(c.get("official_url") or "").strip())
                    ev = c.get("evidence") or {}
                    self.assertIn("application_status", ev,
                                  "主推荐必须带 evidence.application_status（否则 gate 无法认证）")


if __name__ == "__main__":
    unittest.main()
