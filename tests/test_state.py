"""state.py 的测试：稳定 ID、周期区分、URL 变化检测、deadline 变化检测、反馈流转。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest

import _helpers

import state as ST


def rec(oid, **kw):
    r = {"id": oid, "title": "Alpha Robotics Internship 2026", "organization": "Alpha Robotics",
         "primary_category": "career", "official_url": "https://alpha.example/p"}
    r.update(kw)
    return r


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="or-state-")
        for kind in ("seen", "saved", "ignored"):
            ST.save(self.dir, kind, ST.empty(kind))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def mark(self, records):
        return ST.classify(self.dir, [dict(r) for r in records], write=True)

    def seen(self):
        return ST.load(self.dir, "seen")


class TestIdStability(StateTestCase):
    def test_same_record_is_repeat_on_second_run(self):
        self.assertEqual(len(self.mark([rec("a")])["new"]), 1)
        second = self.mark([rec("a")])
        self.assertEqual(second["repeat"], ["a"])
        self.assertEqual(second["new"], [])

    def test_missing_id_is_derived_and_legal(self):
        out = ST.classify(self.dir, [{"title": "清华大学 暑期科研 2027", "organization": "清华大学"}], write=False)
        self.assertEqual(len(out["new"]), 1)
        derived = out["new"][0]
        self.assertNotEqual(derived, "unknown-opportunity")

    def test_different_cycles_are_distinct_entries(self):
        self.mark([rec("alpha-2026", title="Alpha Robotics Internship 2026")])
        out = self.mark([rec("alpha-2026", title="Alpha Robotics Internship 2026"),
                         rec("alpha-2027", title="Alpha Robotics Internship 2027")])
        self.assertEqual(out["new"], ["alpha-2027"])
        self.assertEqual(len(self.seen()["entries"]), 2)


class TestChangeDetection(StateTestCase):
    def test_tracking_params_do_not_trigger_change(self):
        self.mark([rec("a")])
        out = self.mark([rec("a", official_url="https://alpha.example/p?utm_source=x&utm_medium=y")])
        self.assertEqual(out["changed"], [], "仅有 utm 变化不应报 changed")
        self.assertEqual(out["repeat"], ["a"])

    def test_param_order_does_not_trigger_change(self):
        self.mark([rec("a", official_url="https://alpha.example/p?b=2&a=1")])
        out = self.mark([rec("a", official_url="https://alpha.example/p?a=1&b=2")])
        self.assertEqual(out["changed"], [])

    def test_real_url_change_triggers(self):
        self.mark([rec("a")])
        out = self.mark([rec("a", official_url="https://alpha.example/program-2026")])
        self.assertEqual(out["changed"], ["a"])

    def test_deadline_change_triggers_and_logs(self):
        self.mark([rec("a", deadline="2026-10-03")])
        out = self.mark([rec("a", deadline="2026-10-17")])
        self.assertEqual(out["changed"], ["a"])
        changes = out["details"]["a"]
        self.assertEqual(changes[0]["field"], "deadline")
        self.assertEqual(changes[0]["from"], "2026-10-03")
        self.assertEqual(changes[0]["to"], "2026-10-17")
        self.assertTrue(self.seen()["entries"]["a"]["change_log"])

    def test_untracked_field_change_is_not_changed(self):
        self.mark([rec("a", summary="old")])
        out = self.mark([rec("a", summary="new summary")])
        self.assertEqual(out["changed"], [], "只有 tracked 字段变化才值得重新提醒")


class TestFeedback(StateTestCase):
    def test_saved_then_ignored_moves_entry(self):
        ST.cmd_feedback(self.dir, "saved", "a", title="A", category="career", tags="embedded")
        self.assertIn("a", ST.load(self.dir, "saved")["entries"])
        ST.cmd_feedback(self.dir, "not_relevant", "a", title="A")
        self.assertNotIn("a", ST.load(self.dir, "saved")["entries"])
        self.assertIn("a", ST.load(self.dir, "ignored")["entries"])

    def test_feedback_keeps_first_seen(self):
        ST.cmd_feedback(self.dir, "saved", "a")
        first = ST.load(self.dir, "saved")["entries"]["a"]["first_seen"]
        ST.cmd_feedback(self.dir, "applied", "a")
        self.assertEqual(ST.load(self.dir, "saved")["entries"]["a"]["first_seen"], first)

    def test_rejects_unknown_status(self):
        with self.assertRaises(SystemExit):
            ST.cmd_feedback(self.dir, "maybe", "a")


class TestCorruption(StateTestCase):
    def test_corrupt_state_is_backed_up_not_lost(self):
        p = ST.path_for(self.dir, "seen")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        data = ST.load(self.dir, "seen")
        self.assertEqual(data["entries"], {})
        self.assertTrue(os.path.exists(p + ".bak"), "损坏的状态文件必须先备份再重建")


class TestExampleBatch(StateTestCase):
    def test_batch_then_repeat(self):
        with open(_helpers.path("examples", "opportunity.batch.example.json"),
                  encoding="utf-8") as fh:
            records = json.load(fh)["opportunities"]
        first = self.mark(records)
        self.assertEqual(len(first["new"]), len(records))
        second = self.mark(records)
        self.assertEqual(second["new"], [])
        self.assertEqual(len(second["repeat"]), len(records))


if __name__ == "__main__":
    unittest.main()
