"""Generalization regression tests.

守住一条底线：**Core 不知道用户来自哪里，也不知道用户想做什么。**

这些测试防止仓库里的示例/默认值重新把 Skill 拉回"某个特定地区 + 某个特定专业"的路线。
Capability（能解析 JLPT、能匹配 FreeRTOS）继续保留；这里检查的是**默认假设**。
"""

from __future__ import annotations

import json
import os
import re
import unittest

import _helpers

import locales as L
from common import CATEGORIES

ROOT = _helpers.ROOT


def prof(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


CS = prof("examples/profiles/cs-student.example.json")
BIO = prof("examples/profiles/biology-student.example.json")
DESIGN = prof("examples/profiles/design-student.example.json")
IOT_JP = prof("examples/profiles/iot-student-jp.example.json")
ALL_PROFILES = [CS, BIO, DESIGN, IOT_JP]

EAST_ASIA_MARKERS = ("ja-JP", "zh-CN", "ko-KR")
JAPAN_CHINA_FILES = ("references/locales/jp.md", "references/locales/cn.md")


class TestUsCsUser(unittest.TestCase):
    """US + CS/security 用户：不应该出现日本/中国相关语言或知识文件。"""

    def setUp(self):
        self.plan = L.search_plan(CS)

    def test_locales_are_american_english(self):
        self.assertEqual(self.plan["primary_locales"], ["en-US"])
        # 「国家 + 也可以远程」：国家为主，remote 作为附加目标
        self.assertEqual(self.plan["regions"][0], "us")
        self.assertIn("remote", self.plan["regions"])

    def test_no_east_asian_locales_or_files(self):
        for loc in self.plan["primary_locales"] + self.plan["optional_locales"]:
            self.assertNotIn(loc, EAST_ASIA_MARKERS, f"不该假设东亚语言：{loc}")
        for f in self.plan["load_files"]:
            self.assertNotIn(f, JAPAN_CHINA_FILES)

    def test_loads_us_locale_knowledge_only(self):
        self.assertEqual(self.plan["load_files"],
                         ["references/locales/generic.md", "references/locales/us.md"])

    def test_no_iot_or_embedded_expansion(self):
        """没有 IoT/Embedded 信号就不该生成相关关键词。"""
        joined = " ".join(self.plan["interest_keywords"]).lower()
        for kw in ("esp32", "tinyml", "embedded", "robotics", "drone", "iot"):
            self.assertNotIn(kw, joined, f"无信号却扩展出 {kw}")

    def test_categories_include_security_relevant_ones(self):
        self.assertIn("open_source", self.plan["categories"])
        self.assertIn("competition", self.plan["categories"])


class TestFrenchDesignUser(unittest.TestCase):
    def setUp(self):
        self.plan = L.search_plan(DESIGN)

    def test_french_is_primary(self):
        self.assertEqual(self.plan["primary_locales"], ["fr-FR"])
        self.assertEqual(self.plan["regions"][0], "france")
        self.assertIn("en", self.plan["optional_locales"], "英文是候选召回，不是必搜")

    def test_no_asia_default(self):
        for loc in self.plan["primary_locales"]:
            self.assertNotIn(loc, EAST_ASIA_MARKERS)
        for f in self.plan["load_files"]:
            self.assertNotIn(f, JAPAN_CHINA_FILES)

    def test_no_fr_locale_file_still_works(self):
        """没有 fr.md 也要正常工作 —— locale 文件是增强层，不是硬依赖。"""
        self.assertNotIn("references/locales/fr.md", self.plan["load_files"])
        self.assertTrue(any("generic.md" in f for f in self.plan["load_files"]))
        self.assertEqual(self.plan["unknown_regions"], [])

    def test_creative_categories_lead(self):
        top = self.plan["categories"][:3]
        self.assertTrue(set(top) & {"competition", "project", "hobby"}, top)

    def test_no_tech_only_keywords(self):
        joined = " ".join(self.plan["interest_keywords"]).lower()
        for kw in ("esp32", "tinyml", "embedded", "rtos"):
            self.assertNotIn(kw, joined)


class TestGlobalBiologyUser(unittest.TestCase):
    def setUp(self):
        self.plan = L.search_plan(BIO)

    def test_european_regions(self):
        self.assertEqual(sorted(self.plan["regions"]), ["germany", "netherlands"])
        self.assertIn("de-DE", self.plan["primary_locales"])
        self.assertIn("nl-NL", self.plan["primary_locales"])

    def test_research_and_funding_outrank_internships(self):
        order = self.plan["categories"]
        self.assertIn("research", order[:3], order)
        self.assertIn("funding", order[:5], order)
        self.assertGreater(order.index("research"), -1)
        if "career" in order:
            self.assertLess(order.index("research"), order.index("career"),
                            "研究目标不应被求职类压过")

    def test_loads_german_locale_knowledge(self):
        self.assertIn("references/locales/de.md", self.plan["load_files"])


class TestLocaleLoading(unittest.TestCase):
    def test_only_target_geography_is_loaded(self):
        plan = L.search_plan({"constraints": {"preferred_country": ["US", "Canada"]}})
        for f in plan["load_files"]:
            self.assertNotIn(f, JAPAN_CHINA_FILES)
        self.assertIn("references/locales/us.md", plan["load_files"])

    def test_japan_target_loads_jp_knowledge(self):
        """保留能力：目标地区是日本时，日本知识照常加载。"""
        plan = L.search_plan(IOT_JP)
        self.assertIn("references/locales/jp.md", plan["load_files"])
        self.assertEqual(plan["primary_locales"][0], "ja-JP")

    def test_global_default_is_english_without_region_assumption(self):
        plan = L.search_plan({"interests": ["data"]})
        self.assertEqual(plan["regions"], ["remote"])
        self.assertEqual(plan["primary_locales"], ["en"])
        self.assertEqual(plan["load_files"], [L.GENERIC_LOCALE_FILE])
        self.assertTrue(any("目标地区" in n for n in plan["notes"]))

    def test_unknown_country_still_works(self):
        """未收录地区不能导致失败，也不能假装知道它的语言。"""
        plan = L.search_plan({"constraints": {"preferred_country": ["Kenya"]}})
        self.assertEqual(plan["unknown_regions"], ["Kenya"])
        self.assertEqual(plan["load_files"], [L.GENERIC_LOCALE_FILE])
        self.assertEqual(plan["primary_locales"], ["en"])
        self.assertTrue(any("未收录" in n for n in plan["notes"]))

    def test_free_text_request_cannot_inject_regions(self):
        """请求文本里的普通英文单词不能被当成地区；真实的地区/远程信号才应被采纳。"""
        noise = L.search_plan(CS, request_text="I want a good mentor and a nice team")
        self.assertEqual(noise["regions"][0], "us", "噪声词不该改变地区（只用画像）")
        self.assertEqual(noise["unknown_regions"], [])
        self.assertEqual(noise["region_source"], "profile_fallback")

        remote = L.search_plan(CS, request_text="I want a remote internship")
        self.assertIn("remote", remote["regions"], "remote 是真实的目标信号，应被采纳")
        self.assertEqual(remote["primary_locales"], ["en-US"], "不应因 remote 重复引入裸 en")

    def test_request_region_additive_keeps_profile(self):
        """非限定提及：请求地区在前，画像地区保留（可按语义舍弃）。"""
        plan = L.search_plan(CS, request_text="我想找德国的实习，远程也可以")
        self.assertEqual(plan["regions"][:1], ["germany"])
        self.assertIn("us", plan["regions"])
        self.assertEqual(plan["region_source"], "explicit_additive")

    def test_request_override_drops_profile_regions(self):
        """"只找德国" → 覆盖画像偏好：不再出现 us，也不加载 us.md。"""
        plan = L.search_plan(CS, request_text="这次只找德国的机会")
        self.assertEqual(plan["regions"], ["germany"])
        self.assertEqual(plan["region_source"], "explicit_override")
        self.assertIn("references/locales/de.md", plan["load_files"])
        self.assertNotIn("references/locales/us.md", plan["load_files"])
        self.assertEqual(plan["primary_locales"], ["de-DE"])

    def test_additive_remote_request(self):
        plan = L.search_plan(CS, request_text="美国或者远程都可以")
        self.assertIn("us", plan["regions"])
        self.assertIn("remote", plan["regions"])
        self.assertEqual(plan["region_source"], "explicit_additive")

    def test_unknown_structured_geography_is_preserved(self):
        """未收录地区必须作为 region hint 保留 —— 地区和语言不是一回事。"""
        plan = L.search_plan({"constraints": {"preferred_country": ["Kenya"]}})
        self.assertEqual(plan["unknown_regions"], ["Kenya"])
        self.assertIn("Kenya", plan["region_hints"])
        self.assertEqual(plan["load_files"], [L.GENERIC_LOCALE_FILE])
        self.assertEqual(plan["primary_locales"], ["en"])

    def test_region_source_is_reported(self):
        self.assertEqual(L.search_plan(CS)["region_source"], "profile_fallback")
        self.assertEqual(L.search_plan({})["region_source"], "default_remote")

    def test_known_language_becomes_optional_locale(self):
        """明确具备能力（level 有值）→ 进入候选召回语言。"""
        p = dict(CS, languages=[{"language": "Spanish", "exam": None, "score": None,
                                 "level": "intermediate"}])
        plan = L.resolve_locales(p)
        self.assertEqual(plan["primary_locales"], ["en-US"])
        self.assertIn("es-ES", plan["optional_locales"])
        self.assertTrue(any("明确具备" in n for n in plan["notes"]))

    def test_unknown_language_ability_is_not_added(self):
        """只记录名字 ≠ 会用这门语言理解机会 → 不加入召回语言。"""
        p = dict(CS, languages=[{"language": "Spanish", "exam": None, "score": None,
                                 "level": None}])
        plan = L.resolve_locales(p)
        self.assertNotIn("es-ES", plan["optional_locales"])
        self.assertTrue(any("无法确认可用于搜索" in n for n in plan["notes"]))

    def test_exam_without_score_is_still_unknown(self):
        """出现 JLPT 不代表会日语：exam 有值但 score/level 为空 → 不加入。"""
        p = dict(CS, languages=[{"language": "Japanese", "exam": "JLPT", "score": None,
                                 "level": None}])
        plan = L.resolve_locales(p)
        self.assertNotIn("ja-JP", plan["optional_locales"])

    def test_exam_with_score_counts_as_ability(self):
        p = dict(CS, languages=[{"language": "Japanese", "exam": "JLPT", "score": "N3",
                                 "level": None}])
        plan = L.resolve_locales(p)
        self.assertIn("ja-JP", plan["optional_locales"])

    def test_explicit_none_is_never_added(self):
        p = dict(CS, languages=[{"language": "Japanese", "exam": None, "score": None,
                                 "level": "none"}])
        plan = L.resolve_locales(p)
        self.assertNotIn("ja-JP", plan["optional_locales"])
        self.assertTrue(any("明确标注不具备" in n for n in plan["notes"]))


class TestDynamicDetection(unittest.TestCase):
    def test_tld(self):
        self.assertEqual(L.detect_locale("https://www.univ-xyz.fr/offres")["locale"], "fr-FR")
        self.assertEqual(L.detect_locale("https://example.jp/intern")["locale"], "ja-JP")

    def test_path_prefix(self):
        self.assertEqual(L.detect_locale("https://example.com/ja/recruit")["locale"], "ja-JP")

    def test_script(self):
        self.assertEqual(L.detect_locale("研究室のインターン募集")["locale"], "ja-JP")
        self.assertEqual(L.detect_locale("浙江大学 夏令营")["locale"], "zh-CN")
        self.assertEqual(L.detect_locale("Институт прикладной физики")["locale"], "ru-RU")

    def test_unknown_is_none_not_a_guess(self):
        res = L.detect_locale("https://example.com/en/jobs")
        self.assertIn(res["locale"], ("en", None))
        self.assertIsNone(L.detect_locale("random latin words here")["locale"])
        self.assertIsNone(L.detect_locale("")["locale"])


class TestModeWeights(unittest.TestCase):
    def test_all_modes_cover_all_categories(self):
        for mode, weights in L.MODE_WEIGHTS.items():
            with self.subTest(mode=mode):
                self.assertEqual(set(weights), set(CATEGORIES),
                                 f"模式 {mode} 未覆盖全部类别")

    def test_mode_b_demotes_career_and_promotes_creative(self):
        b = L.MODE_WEIGHTS["B"]
        self.assertLess(b["career"], b["competition"])
        self.assertLess(b["career"], b["open_source"])
        self.assertEqual(b["education"], 0.0)

    def test_mode_weights_are_reachable_from_search_plan(self):
        plan = L.search_plan(DESIGN, mode="C")
        self.assertEqual(plan["mode"], "C")
        self.assertEqual(plan["layer_ratios"]["explore"], L.MODE_LAYERS["C"]["explore"])


class TestInterestExpansion(unittest.TestCase):
    def test_only_profile_signals(self):
        self.assertEqual(L.interest_keywords({"interests": []}), [])
        self.assertEqual(L.interest_keywords({}), [])

    def test_alias_expansion_is_conservative_and_bounded(self):
        kws = L.interest_keywords(CS)
        self.assertTrue(kws)
        self.assertEqual(len(kws), len(set(kws)), "不应重复")
        self.assertIn("security", " ".join(kws).lower())

    def test_non_technical_interests_are_supported(self):
        self.assertEqual(L.interest_keywords({"interests": ["biology"]})[:1], ["biology"])
        self.assertTrue(any("animation" in k for k in L.interest_keywords({"interests": ["art"]})))


class TestExampleProfiles(unittest.TestCase):
    def test_all_profiles_resolve(self):
        for p in ALL_PROFILES:
            with self.subTest(profile=p.get("_notes", [""])[0][:30]):
                plan = L.search_plan(p)
                self.assertTrue(plan["primary_locales"])
                self.assertTrue(plan["load_files"])
                self.assertEqual(plan["load_files"][0], L.GENERIC_LOCALE_FILE)

    def test_profiles_are_diverse(self):
        """示例画像不能是同一个人的多个副本。"""
        families = {(p.get("education") or {}).get("major_family") for p in ALL_PROFILES}
        self.assertGreaterEqual(len(families), 3, families)
        countries = {((p.get("education") or {}).get("school_country")) for p in ALL_PROFILES}
        self.assertGreaterEqual(len(countries), 3, countries)

    def test_no_profile_is_presented_as_default(self):
        for p in ALL_PROFILES:
            note = " ".join(p.get("_notes") or []) + str(p.get("_note"))
            if p is IOT_JP:
                self.assertIn("不代表 Skill 的默认用户", note)


class TestNoHardcodedLocaleDefaults(unittest.TestCase):
    """文档与代码里不应再出现固定的语言清单或单一地区世界观。"""

    def test_language_table_is_runtime_driven(self):
        t = open(os.path.join(ROOT, "references", "search-strategy.md"), encoding="utf-8").read()
        self.assertNotRegex(t, r"EN\s*/\s*CN\s*/\s*JA", "不应有固定语言组合")
        self.assertIn("locales/generic.md", t, "语言选择应指向 locale 框架")

    def test_taxonomy_has_no_language_specific_query_blocks(self):
        t = open(os.path.join(ROOT, "references", "opportunity-taxonomy.md"), encoding="utf-8").read()
        self.assertEqual(re.findall(r"^(EN|CN|JA):", t, re.M), [],
                         "taxonomy 不应内嵌某几种语言的 query")
        self.assertIn("Intent templates", t)

    def test_locale_table_includes_multiple_world_regions(self):
        """locale 表不能只覆盖东亚 —— 否则"通用"是假的。"""
        regions = set(L.REGION_LOCALES)
        self.assertTrue({"germany", "france", "netherlands", "spain", "brazil",
                         "us", "uk"} <= regions, regions)
        east_asia = {"cn", "jp", "kr"}
        self.assertLess(len(east_asia) / len(regions), 0.25,
                        "东亚地区占比过高说明表仍偏置")

    def test_locale_files_are_independent_of_locale_table(self):
        """有语言计划但没有知识文件的地区必须存在（证明文件是增强层）。"""
        no_file = [r for r in L.REGION_LOCALES if r not in L.LOCALE_FILES]
        self.assertTrue(no_file, "若所有地区都有文件，则无法体现'文件是可选的'")
        for r in no_file:
            with self.subTest(region=r):
                self.assertIsNone(L.locale_file(r))


class TestRegionPrecedencePatch(unittest.TestCase):
    """v0.1.1：preferred_country 与 school_country 的优先级、hints 合并、多词别名。"""

    def test_preferred_country_beats_school_country(self):
        """学校所在地只是 fallback，不会被追加成第二个搜索目标。"""
        p = {"education": {"school_country": "China"},
             "constraints": {"preferred_country": ["Japan"]}}
        plan = L.search_plan(p)
        self.assertEqual(plan["regions"], ["japan"])
        self.assertEqual(plan["primary_locales"], ["ja-JP"])
        self.assertIn("references/locales/jp.md", plan["load_files"])

    def test_unknown_preferred_country_beats_school_country(self):
        """即使 preferred 未收录，也不能退回学校所在地。"""
        p = {"education": {"school_country": "US"},
             "constraints": {"preferred_country": ["Kenya"]}}
        plan = L.search_plan(p)
        self.assertEqual(plan["regions"], [])
        self.assertEqual(plan["unknown_regions"], ["Kenya"])
        self.assertNotIn("us", plan["region_hints"])

    def test_mixed_known_and_unknown_hints(self):
        p = {"constraints": {"preferred_country": ["Germany", "Kenya"]}}
        plan = L.search_plan(p)
        self.assertEqual(plan["regions"], ["germany"])
        self.assertEqual(plan["unknown_regions"], ["Kenya"])
        self.assertEqual(plan["region_hints"], ["germany", "Kenya"])
        self.assertEqual(plan["primary_locales"], ["de-DE"])

    def test_multiword_latin_aliases(self):
        cases = {"Find internships in the United States": "us",
                 "opportunities in the United Kingdom": "uk",
                 "research in South Korea": "korea",
                 "programs in Great Britain": "uk"}
        for text, expect in cases.items():
            with self.subTest(text=text):
                self.assertIn(expect, L.target_regions({}, text)["regions"])

    def test_no_false_positive_from_ordinary_words(self):
        """普通英文单词不能被当成国家：没有地区信号时只能落到 Global/Remote。"""
        for text in ("an ordinary sentence about mentoring", "I want a good team and nice coffee"):
            with self.subTest(text=text):
                tr = L.target_regions({}, text)
                self.assertEqual(tr["regions"], ["remote"])
                self.assertEqual(tr["unknown_regions"], [])
                self.assertEqual(tr["source"], "default_remote")

    def test_no_school_country_when_nothing_declared(self):
        self.assertEqual(L.search_plan({"education": {"school_country": "Germany"}})["regions"],
                         ["germany"])



class TestGlobalRemoteIntentPatch(unittest.TestCase):
    """F05：Global / Remote 意图不能被 school_country 覆盖。"""

    def test_remote_without_country_is_global(self):
        p = {"education": {"school_country": "Brazil"}, "constraints": {"remote": True}}
        plan = L.search_plan(p)
        self.assertEqual(plan["regions"], ["remote"])
        self.assertEqual(plan["region_source"], "global_intent")
        self.assertEqual(plan["primary_locales"], ["en"])

    def test_explicit_global_preferred_country(self):
        p = {"education": {"school_country": "Brazil"},
             "constraints": {"preferred_country": ["Global"]}}
        self.assertEqual(L.search_plan(p)["regions"], ["remote"])

    def test_country_plus_remote_is_country_primary(self):
        p = {"constraints": {"preferred_country": ["Germany"], "remote": True}}
        plan = L.search_plan(p)
        self.assertEqual(plan["regions"][0], "germany")
        self.assertIn("remote", plan["regions"])
        self.assertEqual(plan["primary_locales"][0], "de-DE")

    def test_no_remote_still_uses_school_country(self):
        p = {"education": {"school_country": "Germany"}}
        self.assertEqual(L.search_plan(p)["regions"], ["germany"])

    def test_preferred_beats_school_and_unknown_preferred_beats_school(self):
        self.assertEqual(L.search_plan({"education": {"school_country": "China"},
            "constraints": {"preferred_country": ["Japan"]}})["regions"], ["japan"])
        self.assertEqual(L.search_plan({"education": {"school_country": "US"},
            "constraints": {"preferred_country": ["Kenya"]}})["unknown_regions"], ["Kenya"])


if __name__ == "__main__":
    unittest.main()
