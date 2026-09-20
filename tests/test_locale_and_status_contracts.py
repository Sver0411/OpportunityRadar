"""实测暴露的两个真缺陷的回归测试（2026-09-20 端到端 skill 冒烟测试）。

1. **locale 泄漏**：family 模板把日语写死成通用第二语言 → 中文/英文用户也收到日语 query。
2. **契约矛盾**：schema 的 `application_status` 枚举不含 `rolling`，而 evidence.py
   的 PARTICIPATION_OPEN_STATUSES 依赖它 → 那条分支永远不可达，滚动招募的机会
   无法在 schema 合法前提下被表达成「可参与」。
"""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import common as C      # noqa: E402
import evidence as E    # noqa: E402
import sources as SI    # noqa: E402

CN = {"life_stage": ["student"], "career_stage": ["undergraduate"],
      "education": {"school_country": "China"}, "constraints": {"preferred_country": ["China"]}}
JP = {"life_stage": ["student"], "education": {"school_country": "Japan"},
      "constraints": {"preferred_country": ["Japan"]}}
US = {"life_stage": ["working"], "education": {"school_country": "United States"},
      "constraints": {"preferred_country": ["United States"]}}
UNKNOWN = {"life_stage": ["working"]}


class TestQueryLocaleIsolation(unittest.TestCase):
    """"语言中立模板" 是文档契约，必须机器校验。"""

    def test_resolved_languages_follow_target_region(self):
        self.assertEqual(SI.query_languages(CN)[0], "zh")
        self.assertEqual(SI.query_languages(JP)[0], "ja")
        self.assertEqual(SI.query_languages(US), ["en"])
        # 未收录/无地区 → 回落英文底座，不猜语言
        self.assertEqual(SI.query_languages(UNKNOWN), ["en"])

    def test_english_base_is_always_kept(self):
        for prof in (CN, JP, US, UNKNOWN):
            with self.subTest(profile=str(prof)[:40]):
                self.assertIn("en", SI.query_languages(prof))

    def test_no_japanese_leak_for_non_japan_users(self):
        """真实失败：中文用户拿到 "コントリビュート 方法"。"""
        for prof, label in ((CN, "CN"), (US, "US"), (UNKNOWN, "unknown")):
            qs = SI.plan_queries({"type": "portfolio", "name": "公开产出"}, prof,
                                 topic="embedded IoT", limit=8)
            with self.subTest(region=label):
                self.assertTrue(qs)
                self.assertEqual([q for q in qs if q.get("lang") == "ja"], [])

    def test_japanese_users_still_get_japanese_queries(self):
        qs = SI.plan_queries({"type": "research", "name": "研究经历"}, JP,
                             topic="Edge AI", region="Japan", limit=8)
        self.assertTrue(any(q.get("lang") == "ja" for q in qs))
        self.assertTrue(any(q.get("lang") == "en" for q in qs))

    def test_base_intents_are_language_neutral(self):
        """`intents` 里不得再出现任何 CJK —— 非英语模板必须走 LOCALE_INTENTS。"""
        for fam, spec in SI.SOURCE_FAMILIES.items():
            for tpl in spec["intents"]:
                with self.subTest(family=fam, template=tpl):
                    self.assertEqual(SI._query_lang(tpl), "en",
                                     f"{fam} 的 intents 不是语言中立模板：{tpl}")

    def test_locale_variants_are_tagged_from_the_table_not_by_heuristic(self):
        """纯汉字日语（学会 学生会員 / 模擬試験）无法与中文区分 → 语言必须来自模板表。

        JP 计划里不得出现被误标成 zh 的 query；CN 计划里同样不得出现 ja。
        """
        jp_qs = SI.plan_queries({"type": "research", "name": "研究经历"}, JP,
                                topic="Edge AI", region="Japan", limit=10)
        self.assertTrue(any(q.get("lang") == "ja" for q in jp_qs))
        self.assertEqual([q for q in jp_qs if q.get("lang") == "zh"], [])

        cn_qs = SI.plan_queries({"type": "research", "name": "研究经历"}, CN,
                                topic="Edge AI", region="China", limit=10)
        self.assertTrue(any(q.get("lang") == "zh" for q in cn_qs))
        self.assertEqual([q for q in cn_qs if q.get("lang") == "ja"], [])

    def test_locale_variant_tables_only_declare_real_languages(self):
        for fam, by_lang in SI.LOCALE_INTENTS.items():
            for lg, tpls in by_lang.items():
                with self.subTest(family=fam, lang=lg):
                    self.assertIn(lg, ("ja", "zh"))
                    self.assertTrue(tpls)
        for stage, by_intent in SI.STAGE_INTENT_LOCALES.items():
            for intent, by_lang in by_intent.items():
                for lg in by_lang:
                    with self.subTest(stage=stage, intent=intent, lang=lg):
                        self.assertIn(lg, ("ja", "zh"))

    def test_stage_overrides_are_language_neutral(self):
        for stage, by_intent in SI.STAGE_INTENT_OVERRIDES.items():
            for intent, tpls in by_intent.items():
                for tpl in tpls:
                    with self.subTest(stage=stage, intent=intent):
                        self.assertEqual(SI._query_lang(tpl), "en")

    def test_every_family_variant_matches_its_query_markers(self):
        """有 family 的 query 必须真的含该 family 的领域词（provenance 不许硬挂）。"""
        for prof in (CN, JP, US):
            for gap in ({"type": "research", "name": "研究经历"},
                        {"type": "language", "name": "日语成绩"},
                        {"type": "portfolio", "name": "公开产出"}):
                for q in SI.plan_queries(gap, prof, topic="Edge AI", region="Japan", limit=10):
                    fam = q.get("family")
                    if not fam:
                        continue
                    markers = SI.FAMILY_QUERY_MARKERS.get(fam, ())
                    with self.subTest(query=q["query"][:36], family=fam):
                        self.assertTrue(any(m in q["query"].lower() for m in markers),
                                        f"{q['query'][:40]} 与 family={fam} 不匹配")

    def test_explicit_languages_override_resolution(self):
        qs = SI.plan_queries({"type": "portfolio", "name": "公开产出"}, CN,
                             topic="embedded", limit=6, languages=["en"])
        self.assertTrue(qs)
        self.assertTrue(all(q.get("lang") == "en" for q in qs))


class TestOpportunityApplicationStatusContract(unittest.TestCase):
    """`application_status`（机会侧）与 state 里的用户侧跟踪状态是两件事。"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "schemas", "opportunity.schema.json"),
                  encoding="utf-8") as fh:
            cls.schema = json.load(fh)

    def test_schema_enum_matches_common_enum(self):
        enum = [v for v in self.schema["properties"]["application_status"]["enum"]
                if v is not None]
        self.assertEqual(set(enum), set(C.OPPORTUNITY_APPLICATION_STATUSES))

    def test_participation_open_statuses_are_schema_legal(self):
        """真实缺陷：schema 拒绝 'rolling'，导致 evidence.py 的 rolling 分支不可达。"""
        enum = set(self.schema["properties"]["application_status"]["enum"])
        for v in C.PARTICIPATION_OPEN_STATUSES:
            with self.subTest(status=v):
                self.assertIn(v, enum, f"{v} 不被 schema 接受 → evidence 分支不可达")
        self.assertIn("rolling", enum)

    def test_user_tracking_statuses_are_not_opportunity_statuses(self):
        """两套枚举不得混用（字段同名，是本次实测最容易踩的坑）。"""
        self.assertEqual(set(C.APPLICATION_STATUSES) & set(C.OPPORTUNITY_APPLICATION_STATUSES),
                         set())

    def _opp(self, stated, evidence_status="explicit"):
        return {
            "id": "x", "title": "t", "organization": "o",
            "application_status": stated,
            "verification_status": "verified_official",
            "official_url": "https://example.org/prog",
            "evidence": {"application_status": {"status": evidence_status,
                                                "source_url": "https://example.org/prog",
                                                "verified_at": "2026-09-20"}},
        }

    def test_rolling_counts_as_participation_open(self):
        res = E.application_status_evidence(self._opp("rolling"))
        self.assertTrue(res["present"])
        self.assertTrue(res["participation_open"])

    def test_missing_top_level_field_is_named_as_top_level(self):
        """真实失败：报 'evidence.application_status(application_status)' 分不清是哪个字段。"""
        res = E.application_status_evidence(self._opp(None))
        self.assertFalse(res["present"])
        joined = " ".join(res["missing"])
        self.assertIn("top-level", joined)
        self.assertIn("open/rolling", joined)

    def test_user_tracking_value_is_flagged_not_silently_demoted(self):
        """把 saved/applied 这类用户侧值填进机会侧字段 → 必须显式报错，不静默降级。"""
        res = E.application_status_evidence(self._opp("saved"))
        self.assertFalse(res["present"])
        self.assertTrue(any("非法" in m for m in res["missing"]))
        self.assertFalse(res["participation_open"])


if __name__ == "__main__":
    unittest.main()


class TestCliDateFlagConsistency(unittest.TestCase):
    """agent 面向的 CLI：时间参数名必须一致，否则很容易调错（实测中我自己踩了）。"""

    def test_normalize_date_accepts_today_like_the_other_scripts(self):
        import subprocess
        script = os.path.join(ROOT, "scripts", "normalize_date.py")
        for flag in ("--today", "--now"):
            with self.subTest(flag=flag):
                out = subprocess.run([sys.executable, script, "2026-09-24", flag, "2026-09-20",
                                      "--format", "json"], capture_output=True, text=True)
                self.assertEqual(out.returncode, 0, out.stderr[:200])
                self.assertIn("2026-09-24", out.stdout)
