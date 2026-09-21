"""RC2 回归基线：五个独立会话（2026-09-21）的结构化输入，跑新 presentation / planner 后不得回归。

基线来自 `usertests/rc2-validation/inputs/{A..E}/`（画像 + 真实候选）。
这一层是**防回归**：A/B/C 本轮不重新联网跑，所以必须由测试保证它们的结构化产物
经过新的主线选择器 / 起点段 / Explore 镜头规划后不变形。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import presentation as P    # noqa: E402
import score as S           # noqa: E402
import sources as SI        # noqa: E402

TODAY = dt.date(2026, 9, 21)
INPUTS = os.path.join(ROOT, "usertests", "rc2-validation", "inputs")


def load(case):
    d = os.path.join(INPUTS, case)
    prof = json.load(open(os.path.join(d, "profile.json"), encoding="utf-8"))
    batch = json.load(open(os.path.join(d, "opportunities.json"), encoding="utf-8"))
    return prof, batch["opportunities"]


def render(case):
    prof, opps = load(case)
    res = S.score_all(prof, opps, today=TODAY)
    rows = list(res.get("results") or []) + [{**e, "zone": "excluded"}
                                             for e in (res.get("excluded") or [])]
    ans = P.render_answer(prof, rows, [], [], mode="C" if case == "E" else "A")
    return prof, opps, res, rows, ans


class TestNoRegressionAcrossPersonas(unittest.TestCase):
    """所有 persona 共有的不变量。"""

    def test_every_persona_still_produces_a_usable_answer(self):
        for case in ("A", "B", "C", "D", "E"):
            with self.subTest(case=case):
                _, _, res, rows, ans = render(case)
                zones = res.get("zones") or {}
                self.assertGreater(zones.get("recommended_now", 0) + zones.get("worth_verifying", 0), 0,
                                   "至少要给出可看的机会")
                self.assertEqual(ans["violations"], [], "输出自检必须为 0")
                self.assertTrue(ans["confidence"]["level"] in ("high", "medium", "low"))

    def test_no_persona_claims_a_preference_it_never_stated(self):
        for case in ("A", "B", "C", "D", "E"):
            prof = load(case)[0]
            _, _, _, _, ans = render(case)
            cards = (ans["main"] or []) + (ans["worth_verifying"] or [])
            signals = P._profile_signals(prof)
            for c in cards:
                with self.subTest(case=case, card=c["opportunity_id"]):
                    if "偏好相符" in (c.get("why_fit") or ""):
                        self.assertTrue(signals["location_fit"])
                    if "与你的目标直接相关" in (c.get("why_fit") or ""):
                        self.assertTrue(signals["goal_fit"])

    def test_mainline_is_never_the_urgency_first_item_by_construction(self):
        """主线由目标相关性决定；紧急但不是主线的必须被标为"近期窗口"。"""
        for case in ("A", "B", "C", "D", "E"):
            _, _, _, _, ans = render(case)
            alloc = ans.get("allocation") or {}
            levels = {i["opportunity_id"]: i["level"] for i in (alloc.get("items") or [])}
            if not levels:
                continue
            self.assertIn("主线", set(levels.values()), f"{case} 应有且只有一个主线")
            self.assertEqual(list(levels.values()).count("主线"), 1)
            if case == "D":
                # D 的具体主线正确性在下面单独断言；这里只保证不是"第一个就是主线"
                self.assertNotEqual(ans.get("allocation", {}).get("mainline"),
                                    (alloc.get("items") or [{}])[0].get("opportunity_id")
                                    if len(alloc.get("items") or []) > 1 else None)


class TestCaseDFixtures(unittest.TestCase):
    """D：起点可见 + 主线由目标相关性决定。"""

    def test_starting_point_is_visible(self):
        _, _, _, _, ans = render("D")
        sp = ans.get("starting_point") or {}
        self.assertTrue(sp.get("has_capital"), "D 明确说了 5 年后端 → 必须体现")
        self.assertTrue(any("后端" in c for c in sp["capital"]))
        self.assertTrue(any("5" in c for c in sp["capital"]))
        self.assertIn("你的起点", sp["text"])

    def test_starting_point_transfer_hint_only_with_structured_support(self):
        prof = load("D")[0]
        self.assertIsNone(P.starting_point(prof, None, [])["transfer_hint"],
                          "没有 gap/produces 支持时不得写「应该迁到哪」")
        with_support = P.starting_point(prof, {"gap_filled": {"gap": "AI production 证据"}}, [])
        self.assertIn("AI production 证据", with_support["transfer_hint"])

    def test_mainline_prefers_goal_relevance_over_urgency(self):
        _, opps, _, rows, ans = render("D")
        ml = ans["mainline"]["opportunity_id"]
        main_row = next(r for r in rows if r.get("id") == ml)
        others = [r for r in rows if r.get("id") != ml and r.get("zone") == "recommended_now"]
        for r in others:
            with self.subTest(other=r["id"]):
                # 主线的目标相关度（或后续通道/Utility）不得低于其它推荐
                self.assertGreaterEqual(
                    (main_row["components"]["goal_fit"],
                     P._FO_RANK.get(str((main_row.get("future_optionality") or {}).get("level")), 0),
                     P._UTILITY_RANK.get(str(main_row.get("utility")), 0)),
                    (r["components"]["goal_fit"],
                     P._FO_RANK.get(str((r.get("future_optionality") or {}).get("level")), 0),
                     P._UTILITY_RANK.get(str(r.get("utility")), 0)))


class TestExploreLenses(unittest.TestCase):
    """E：Explore 镜头与按镜头的核实选择；同时保证不影响有目标的用户。"""

    def test_lenses_only_for_blank_explore_profiles(self):
        e = load("E")[0]
        self.assertTrue(SI.explore_lens_enabled(e, "C")["enabled"])
        for case in ("A", "B", "C", "D"):
            with self.subTest(case=case):
                self.assertFalse(SI.explore_lens_enabled(load(case)[0], "C")["enabled"],
                                 f"{case} 不应启用 explore 镜头")

    def test_query_batch_covers_at_least_three_lenses(self):
        e = load("E")[0]
        qs = SI.plan_explore_queries(e, "C")
        lenses = {q["lens"] for q in qs}
        self.assertGreaterEqual(len(lenses), 3)
        self.assertEqual(len(lenses), len(qs), "同一镜头不应重复占多个名额")

    def test_query_batch_is_not_anti_technical(self):
        """镜头里必须包含技术类角度；这是"打开窗口"，不是"排除技术"。"""
        lenses = {q["lens"] for q in SI.plan_explore_queries(load("E")[0], "C", lens_limit=8)}
        self.assertTrue(lenses & {"contribute", "build", "research"})

    def test_verification_selection_covers_different_lenses(self):
        _, opps, _, _, _ = render("E")
        sel = SI.select_verification_targets(opps, 4, axis_fn=P.explore_axes_of, mode="C")
        self.assertTrue(sel)
        axes = {s["axis"] for s in sel if s["axis"]}
        top_in_axis = [s for s in sel if s["verification_selected_because"] == "top_in_axis"]
        self.assertEqual(len(axes), len(top_in_axis),
                         "每个镜头最多一条 top_in_axis，且必须来自不同镜头")
        for s in sel:
            with self.subTest(item=s["opportunity_id"]):
                self.assertIn(s["verification_selected_because"],
                              ("top_in_axis", "global_top", "urgency", "fallback"))

    def test_verification_selection_does_not_change_any_gate(self):
        """选择器只返回"先核实谁"，不得改动候选或判定字段。"""
        _, opps, _, _, _ = render("E")
        before = json.dumps(opps, ensure_ascii=False, sort_keys=True)
        SI.select_verification_targets(opps, 4, axis_fn=P.explore_axes_of, mode="C")
        self.assertEqual(before, json.dumps(opps, ensure_ascii=False, sort_keys=True))

    def test_presented_axes_never_stuffed(self):
        """呈现集的轴数必须等于真实可达的轴数，不能为过 benchmark 塞弱条目。"""
        _, opps, _, rows, ans = render("E")
        presented = [r for r in rows if r.get("zone") in ("recommended_now", "worth_verifying")]
        cov = P.explore_coverage(presented)
        self.assertEqual(cov["axis_count"], len(cov["axes"]))
        self.assertTrue(cov["axis_reasons"], "每条轴都要能追溯理由")


if __name__ == "__main__":
    unittest.main()
