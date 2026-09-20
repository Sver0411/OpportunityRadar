"""10 个事实链 fixture：freshness 判定 + evidence 前置检查 → 期望 zone。

覆盖 rolling / evergreen / recurring / fixed / 无法确认 / 第三方声称 / 官网反爬，
确保"真实存在且当前可参与的长尾机会能进主推荐"与"没有当前证据的机会进不了主推荐"。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import unittest

import _helpers

import evidence as EV
import score as S

FIXTURE = os.path.join(_helpers.ROOT, "tests", "fixtures", "evidence_freshness_cases.json")


class TestFreshnessEvidenceCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as fh:
            cls.fx = json.load(fh)
        cls.today = dt.date.fromisoformat(cls.fx["today"])

    def _row(self, case):
        res = S.score_all(self.fx["profile"], [case["opportunity"]], today=self.today)
        if res["results"]:
            return res["results"][0], None
        return None, res["excluded"][0] if res["excluded"] else None

    def test_all_cases(self):
        for case in self.fx["cases"]:
            exp = case["expected"]
            with self.subTest(case=case["id"], label=case["label"]):
                row, exc = self._row(case)
                if row is None:                     # 被排除（如过期）
                    self.assertEqual(exp["zone"], "excluded")
                    self.assertIn(exp["freshness"], exc.get("reason", ""))
                    continue
                self.assertEqual(row["freshness"], exp["freshness"])
                self.assertEqual(row["zone"], exp["zone"])
                if "actionable" in exp:
                    self.assertEqual(row["actionable"], exp["actionable"])
                if "demotion_code" in exp:
                    self.assertEqual((row.get("demotion") or {}).get("code"), exp["demotion_code"])
                if exp["zone"] == "recommended_now":
                    self.assertTrue(row["evidence_complete"],
                                    "主推荐必须证据完整")
                    self.assertTrue(row["actionable"], "主推荐必须 actionable")

    def test_evergreen_alone_is_not_actionable(self):
        """evergreen 只有页面介绍、没有参与入口 → 不得进主推荐（evergreen ≠ verified open）。"""
        case = next(c for c in self.fx["cases"] if c["id"] == "evergreen_without_entry")
        row, _ = self._row(case)
        self.assertFalse(row["actionable"])
        self.assertEqual(row["zone"], "worth_verifying")

    def test_demotion_distinguishes_process_from_fact(self):
        """区分"系统漏记证据"与"官网无法确认/无法读取"。"""
        checks = {
            "null_unconfirmable": ("page_cannot_confirm", "fact"),
            "third_party_claims_open": ("no_canonical_source", "process"),
            "official_blocked": ("page_not_verifiable", "infrastructure"),
        }
        for cid, (code, kind) in checks.items():
            case = next(c for c in self.fx["cases"] if c["id"] == cid)
            row, _ = self._row(case)
            with self.subTest(case=cid):
                self.assertEqual(row["demotion"]["code"], code)
                self.assertEqual(row["demotion"]["kind"], kind)

    def test_evidence_checker_rejects_stale_and_partial(self):
        base = {"official_url": "https://x.example", "verification_status": "verified_official",
                "application_status": "open"}
        with open(FIXTURE, encoding="utf-8") as fh:
            opps = json.load(fh)
        good = dict(base, evidence={"application_status": {
            "status": "explicit", "source_url": "https://x.example", "verified_at": "2026-09-19"}})
        self.assertTrue(EV.check(good, self.today)["complete"])
        stale = dict(base, evidence={"application_status": {
            "status": "explicit", "source_url": "https://x.example", "verified_at": "2026-01-01"}})
        self.assertFalse(EV.check(stale, self.today)["complete"])
        partial = dict(base, evidence={"application_status": {"status": "inferred"}})
        self.assertFalse(EV.check(partial, self.today)["complete"])
        no_status = dict(base, application_status=None, evidence={"application_status": {
            "status": "explicit", "source_url": "https://x.example", "verified_at": "2026-09-19"}})
        self.assertFalse(EV.check(no_status, self.today)["complete"])


if __name__ == "__main__":
    unittest.main()
