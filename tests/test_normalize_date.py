"""normalize_date.py 的回归测试。

覆盖：固定日期、区间、跨年区间、年份不明、滚动招募、TBD/ASAP/Flexible 与 rolling 的区分、
非法输入、区间紧迫度取截止端点、时间与时区保留、以及月份名吞词的历史 bug。
"""

from __future__ import annotations

import unittest

import _helpers  # noqa: F401  (把 scripts/ 加入 sys.path)

from normalize_date import parse_date

NOW = "2026-09-14"


def p(text, **kw):
    return parse_date(text, now=NOW, **kw)


class TestFixedDates(unittest.TestCase):
    def test_iso_and_variants(self):
        for text in ["2026-09-20", "2026/9/20", "2026.9.20", "2026年9月20日",
                     "Sep 20, 2026", "20 September 2026", "20-Sep-2026",
                     "Deadline: 2026-10-03", "締切：2026年9月20日"]:
            with self.subTest(text=text):
                r = p(text)
                self.assertEqual(r["deadline_type"], "fixed")
                self.assertIsNotNone(r["iso"], msg=f"{text} 应能解析")
                self.assertEqual(r["precision"], "day")

    def test_year_unknown_is_not_guessed(self):
        r = p("9月20日")
        self.assertTrue(r["year_unknown"])
        self.assertIsNone(r["iso"], "年份不明时不得猜测年份")
        self.assertEqual(r["month"], 9)
        self.assertEqual(r["day"], 20)

    def test_year_unknown_with_default_year_is_flagged(self):
        r = p("9月20日", default_year=2026)
        self.assertEqual(r["iso"], "2026-09-20")
        self.assertTrue(r["year_unknown"], "填充的年份必须标记为不确定")

    def test_month_only_precision_is_unknown_not_fixed(self):
        r = p("September 2026")
        self.assertIsNone(r["iso"])
        self.assertEqual(r["deadline_type"], "unknown")
        self.assertEqual(r["precision"], "month")
        self.assertEqual(r["year"], 2026)
        self.assertEqual(r["month"], 9)

    def test_invalid_date(self):
        r = p("未公开")
        self.assertIsNone(r["iso"])
        self.assertNotIn(r["deadline_type"], ("fixed", "range"))


class TestRanges(unittest.TestCase):
    def test_range_parsed(self):
        r = p("2026-09-20 ~ 2026-10-05")
        self.assertEqual(r["deadline_type"], "range")
        self.assertEqual(r["iso"], "2026-09-20")
        self.assertEqual(r["end"], "2026-10-05")

    def test_urgency_uses_end_not_start(self):
        r = p("2026-09-20 ~ 2026-10-05")
        # 到起点 6 天，到终点 21 天：紧迫度必须以截止端点为准
        self.assertEqual(r["days_until_start"], 6)
        self.assertEqual(r["days_until_end"], 21)
        self.assertEqual(r["urgency_days"], 21)
        self.assertFalse(r["expired"])

    def test_cross_year_range_infers_years(self):
        r = p("Dec 20 - Jan 5, 2027")
        self.assertEqual(r["iso"], "2026-12-20")
        self.assertEqual(r["end"], "2027-01-05")

    def test_chinese_range_without_year(self):
        r = p("9月20日-10月5日", default_year=2026)
        self.assertEqual(r["iso"], "2026-09-20")
        self.assertEqual(r["end"], "2026-10-05")


class TestDeadlineTypes(unittest.TestCase):
    def test_rolling_is_rolling(self):
        for text in ["Rolling basis", "open until filled", "随時受付", "常年招募", "招满即止"]:
            with self.subTest(text=text):
                r = p(text)
                self.assertEqual(r["deadline_type"], "rolling")
                self.assertTrue(r["rolling"])
                self.assertIsNone(r["iso"])

    def test_tbd_is_not_rolling(self):
        for text in ["TBD", "未定", "未公开", "後日発表", "to be announced"]:
            with self.subTest(text=text):
                r = p(text)
                self.assertEqual(r["deadline_type"], "tbd")
                self.assertFalse(r["rolling"], "TBD 不等于滚动招募")

    def test_asap_is_not_rolling(self):
        r = p("ASAP")
        self.assertEqual(r["deadline_type"], "asap")
        self.assertFalse(r["rolling"])

    def test_flexible_is_not_rolling(self):
        r = p("Flexible")
        self.assertEqual(r["deadline_type"], "flexible")
        self.assertFalse(r["rolling"])

    def test_status_word_with_real_date_prefers_date(self):
        r = p("Rolling, opens 2026-09-01")
        self.assertEqual(r["iso"], "2026-09-01")
        self.assertEqual(r["deadline_type"], "fixed")


class TestTimeAndTimezone(unittest.TestCase):
    def test_time_and_timezone_preserved(self):
        r = p("2026-10-03 23:59 JST")
        self.assertEqual(r["iso"], "2026-10-03")
        self.assertEqual(r["time"], "23:59")
        self.assertEqual(r["timezone"], "JST")
        self.assertTrue(any("未做 UTC 换算" in n for n in r["notes"]))

    def test_offset_attached_to_time(self):
        r = p("2026-09-20T09:00+09:00")
        self.assertEqual(r["timezone"], "+09:00")

    def test_offset_not_confused_with_year(self):
        """历史 bug：'20-Sep-2026' 的 '-2026' 曾被误判为时区偏移。"""
        r = p("20-Sep-2026")
        self.assertIsNone(r["timezone"])
        self.assertEqual(r["iso"], "2026-09-20")


class TestMonthNameRegression(unittest.TestCase):
    """历史 bug：非月份单词（opens/Rolling）被月份名模式吞掉，导致真实日期被跳过。"""

    def test_word_before_year_is_not_eaten(self):
        for text, expect in [("opens 2026-09-01", "2026-09-01"),
                             ("Apply opens 20 September 2026", "2026-09-20"),
                             ("application period starts 2026年9月20日", "2026-09-20")]:
            with self.subTest(text=text):
                self.assertEqual(p(text)["iso"], expect)


class TestStatusUnchanged(unittest.TestCase):
    def test_empty_input(self):
        r = p("")
        self.assertIsNone(r["iso"])
        self.assertEqual(r["deadline_type"], "unknown")

    def test_no_days_remaining_field(self):
        """days_remaining 语义不清，已移除；应只提供 days_until_start/end/urgency_days。"""
        r = p("2026-09-20")
        self.assertNotIn("days_remaining", r)
        self.assertIn("urgency_days", r)


if __name__ == "__main__":
    unittest.main()
