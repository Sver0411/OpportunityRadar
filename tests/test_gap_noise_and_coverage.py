"""F4/F6 回归：参与手续不得污染发展缺口；中英能力词要能互相识别。

来源：2026-09-20 对已安装 skill 做端到端实测时暴露的真实失败 ——
一条中文学生的运行里，9 个"发展缺口"有 6 个是报名材料（online application /
passport copy / supervisor approval / 个人资料 / 身份证-学籍证明 / 项目申请书），
并且每个都触发了 Bridge 搜索，产出「缺护照复印件 → 桥接到开源之夏」这类结论。
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import common as C      # noqa: E402
import gaps as GP       # noqa: E402
import graph as G       # noqa: E402

# 实测中的真实画像（中文用户）
PROFILE = {
    "life_stage": ["student"], "career_stage": ["undergraduate"],
    "education": {"degree": "undergraduate", "major": "物联网工程",
                  "school_country": "China"},
    "skills": [{"name": "C"}, {"name": "Python"}, {"name": "ESP32"}],
    "interests": [{"name": "embedded"}, {"name": "IoT"}],
    "constraints": {"preferred_country": ["China"], "weekly_time": "8"},
    "goals": [{"type": "skill", "priority": "medium"}],
}

# 实测中的真实候选（材料全部来自真实官方页）
REAL = [
    {"id": "ospp", "title": "开源之夏 2026", "primary_category": "open_source",
     "skills_required": ["Git"],
     "required_materials": ["个人资料", "项目申请书", "身份证/学籍在线验证报告"]},
    {"id": "kaust", "title": "KAUST MEWC 2027", "primary_category": "research",
     "skills_required": ["research fundamentals"],
     "required_materials": ["CV", "official transcripts (English)", "passport copy",
                            "research proposal draft"]},
    {"id": "ustc", "title": "USTC Research Internship", "primary_category": "research",
     "nationality_requirement": "Non-Chinese citizens with a foreign passport",
     "required_materials": ["online application", "supervisor approval"]},
    {"id": "socchina", "title": "嵌入式芯片与系统设计竞赛", "primary_category": "competition",
     "skills_required": ["嵌入式", "嵌入式开发"]},
]


class TestMaterialsAreNotGaps(unittest.TestCase):
    def setUp(self):
        self.gaps = GP.collect_gaps(REAL, PROFILE)
        self.names = [g["name"] for g in self.gaps]

    def test_materials_never_become_gaps(self):
        for mat in ("online application", "passport copy", "supervisor approval",
                    "个人资料", "身份证/学籍在线验证报告", "项目申请书"):
            with self.subTest(material=mat):
                self.assertNotIn(mat, self.names)

    def test_materials_are_reclassified_never_dropped(self):
        """既不进缺口、也不丢：手续类进 logistics，其余进 preparation。"""
        summary = GP.gap_summary(self.gaps)
        buckets = (set(summary.get("logistics_prerequisites") or [])
                   | set(summary.get("preparation_items") or []))
        for mat in ("个人资料", "CV", "passport copy", "online application",
                    "supervisor approval", "official transcripts (English)",
                    "research proposal draft", "身份证/学籍在线验证报告"):
            with self.subTest(material=mat):
                self.assertNotIn(mat, self.names, f"{mat} 不得进入缺口")
                self.assertIn(mat, buckets, f"{mat} 被静默丢弃了")

    def test_nationality_requirement_is_an_eligibility_constraint_not_a_gap(self):
        summary = GP.gap_summary(self.gaps)
        self.assertIn("Non-Chinese citizens with a foreign passport",
                      summary["eligibility_constraints"])
        self.assertNotIn("Non-Chinese citizens with a foreign passport", self.names)
        self.assertEqual([g for g in self.gaps if g["type"] == "location_visa"], [])

    def test_portfolio_artefact_materials_still_count(self):
        """材料**本身是公开产出物**时仍然是 portfolio 缺口（不误伤真实缺口）。"""
        opps = [{"id": "x", "title": "TinyML challenge", "primary_category": "competition",
                 "required_materials": ["demo video"]}]
        gaps = GP.collect_gaps(opps, PROFILE)
        self.assertIn("demo video", [g["name"] for g in gaps])

    def test_no_bridge_search_for_materials(self):
        """实测缺陷：缺护照复印件被拿去搜 Bridge。"""
        report = G.gap_to_bridge_report(self.gaps, REAL, PROFILE)
        searched = {e["gap"]["name"] for e in report}
        for mat in ("passport copy", "online application", "个人资料", "CV"):
            with self.subTest(material=mat):
                self.assertNotIn(mat, searched)

    def test_is_logistics_covers_the_observed_materials(self):
        for mat in ("online application", "passport copy", "supervisor approval",
                    "身份证", "学籍在线验证报告", "个人资料", "项目申请书"):
            with self.subTest(material=mat):
                self.assertTrue(GP.is_logistics(mat), f"{mat} 未被识别为手续类")


class TestCrossLanguageSkillCoverage(unittest.TestCase):
    """实测缺陷：机会要求写「嵌入式」，画像写 embedded/ESP32 → 幻影缺口。"""

    def test_chinese_requirement_covered_by_english_interest(self):
        for req in ("嵌入式", "嵌入式开发", "物联网"):
            with self.subTest(requirement=req):
                self.assertTrue(GP._covered(req, PROFILE),
                                f"「{req}」应被画像的兴趣/技能覆盖")

    def test_cjk_substring_containment(self):
        self.assertTrue(GP._covered("嵌入式开发", {"skills": [{"name": "嵌入式"}]}))
        self.assertTrue(GP._covered("嵌入式", {"skills": [{"name": "嵌入式开发"}]}))

    def test_interests_count_as_coverage(self):
        self.assertTrue(GP._covered("embedded", PROFILE))

    def test_equivalents_do_not_over_cover_sibling_skills(self):
        """「会 ESP32」≠「会 RTOS」：同族表不得被整体搬来做覆盖判定。"""
        self.assertFalse(GP._covered("RTOS", PROFILE))
        self.assertFalse(GP._covered("TinyML", PROFILE))

    def test_equivalents_map_only_direct_translations(self):
        for zh, en in C.SKILL_EQUIVALENTS.items():
            with self.subTest(zh=zh):
                self.assertTrue(zh and en)
                self.assertNotIn("/", zh)          # 不做多义合并
                self.assertEqual(zh, zh.strip())


if __name__ == "__main__":
    unittest.main()
