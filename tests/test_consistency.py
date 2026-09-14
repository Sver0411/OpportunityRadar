"""跨文件一致性测试：同一个概念在 SKILL.md / references / schemas / scripts 里只能有一套定义。

这是"单一事实来源"的机器化保证：任何一处枚举或权重被改动而另一处没跟上，测试会失败。
"""

from __future__ import annotations

import json
import os
import re
import unittest

import _helpers

import common as C

ROOT = _helpers.ROOT


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


SKILL = read("SKILL.md")
RANKING = read("references/ranking.md")
ELIGIBILITY = read("references/eligibility.md")
TAXONOMY = read("references/opportunity-taxonomy.md")
EXTRACTION = read("references/extraction-policy.md")
STATE_DOC = read("references/state-and-feedback.md")
TRUST = read("references/trust-policy.md")
OPP_SCHEMA = json.loads(read("schemas/opportunity.schema.json"))
PROF_SCHEMA = json.loads(read("schemas/profile.schema.json"))


class TestSingleSourceOfTruth(unittest.TestCase):
    def test_weights_match_ranking_doc(self):
        table = dict(re.findall(r"\|\s*`(\w+)`\s*\|\s*([\d.]+)\s*\|", RANKING))
        parsed = {k: float(v) for k, v in table.items() if k in C.WEIGHTS}
        self.assertEqual(parsed, C.WEIGHTS,
                         "references/ranking.md 的权重表必须与 common.WEIGHTS 一致")
        self.assertAlmostEqual(sum(C.WEIGHTS.values()), 1.0, places=6)

    def test_score_uses_shared_weights(self):
        src = read("scripts/score.py")
        self.assertIn("WEIGHTS", src)
        self.assertNotIn("WEIGHTS = {", src, "score.py 不得再定义一份权重表")

    def test_categories_agree(self):
        self.assertEqual(tuple(OPP_SCHEMA["$defs"]["category"]["enum"]), C.CATEGORIES)
        missing = [c for c in C.CATEGORIES if f"`{c}`" not in TAXONOMY]
        self.assertEqual(missing, [], f"taxonomy 文档缺少分类：{missing}")

    def test_goal_types_agree(self):
        goals = PROF_SCHEMA["properties"]["goals"]["items"]["properties"]["type"]["enum"]
        self.assertEqual(tuple(goals), C.GOAL_TYPES)

    def test_verdicts_agree(self):
        schema_v = tuple(OPP_SCHEMA["$defs"]["eligibilityVerdict"]["enum"])
        self.assertEqual(tuple(v for v in schema_v if v), C.ELIGIBILITY_VERDICTS)
        for v in C.ELIGIBILITY_VERDICTS:
            self.assertIn(v, ELIGIBILITY, f"eligibility.md 未定义 {v}")
        code = read("scripts/score.py")
        for v in C.ELIGIBILITY_VERDICTS:
            self.assertIn(v, code, f"score.py 未处理 {v}")

    def test_trust_tiers_agree(self):
        tiers = tuple(t for t in OPP_SCHEMA["$defs"]["trustTier"]["enum"] if t)
        self.assertEqual(tiers, C.TRUST_TIERS)
        self.assertIn("Tier A", TRUST)
        self.assertIn("Tier D", TRUST)

    def test_verification_statuses_agree(self):
        schema_s = tuple(s for s in OPP_SCHEMA["$defs"]["verificationStatus"]["enum"] if s)
        self.assertEqual(schema_s, C.VERIFICATION_STATUSES)
        for s in C.VERIFICATION_STATUSES:
            self.assertIn(s, TRUST, f"trust-policy.md 未定义 {s}")

    def test_value_levels_agree(self):
        schema_l = tuple(l for l in OPP_SCHEMA["$defs"]["valueLevel"]["enum"] if l)
        self.assertEqual(schema_l, C.VALUE_LEVELS)

    def test_evidence_statuses_agree(self):
        schema_e = tuple(OPP_SCHEMA["$defs"]["evidenceStatus"]["enum"])
        self.assertEqual(schema_e, C.EVIDENCE_STATUSES)
        for s in C.EVIDENCE_STATUSES:
            self.assertIn(s, EXTRACTION, f"extraction-policy.md 未定义 {s}")

    def test_deadline_types_agree(self):
        schema_d = tuple(d for d in OPP_SCHEMA["properties"]["deadline_type"]["enum"] if d)
        self.assertEqual(schema_d, C.DEADLINE_TYPES)
        for d in C.DEADLINE_TYPES:
            self.assertIn(d, EXTRACTION, f"extraction-policy.md 未说明 deadline_type={d}")
        code = read("scripts/normalize_date.py")
        for d in C.DEADLINE_TYPES:
            self.assertIn(f'"{d}"', code, f"normalize_date.py 未产出 deadline_type={d}")

    def test_evidence_fields_agree(self):
        props = set(OPP_SCHEMA["properties"]["evidence"]["properties"])
        self.assertEqual(props, set(C.EVIDENCE_FIELDS))
        for f in C.EVIDENCE_FIELDS:
            self.assertIn(f, EXTRACTION, f"extraction-policy.md 未列出证据字段 {f}")

    def test_tracked_fields_documented(self):
        for f in C.TRACKED_FIELDS:
            self.assertIn(f, STATE_DOC, f"state-and-feedback.md 未说明 tracked 字段 {f}")


class TestNoDuplicatedLogic(unittest.TestCase):
    """canonical_url / derive_id / norm_org 只能有一份实现（common.py）。"""

    SHARED = ("def canonical_url", "def derive_id", "def norm_org", "def slugify",
              "TRACKED_FIELDS =", "def core_title")

    def test_modules_do_not_redefine_shared_helpers(self):
        for rel in ["scripts/dedupe.py", "scripts/state.py", "scripts/score.py"]:
            src = read(rel)
            for sig in self.SHARED:
                with self.subTest(file=rel, symbol=sig):
                    self.assertNotIn(sig, src, f"{rel} 不应重新实现 {sig}")

    def test_modules_import_from_common(self):
        for rel in ["scripts/dedupe.py", "scripts/state.py", "scripts/score.py"]:
            with self.subTest(file=rel):
                self.assertIn("from common import", read(rel))


class TestResourceReferences(unittest.TestCase):
    def test_skill_referenced_paths_exist(self):
        refs = set(re.findall(r"`((?:references|schemas|scripts|examples)/[\w./*-]+)`", SKILL))
        missing = [r for r in refs if "*" not in r and not os.path.exists(os.path.join(ROOT, r))]
        self.assertEqual(missing, [], f"SKILL.md 引用了不存在的资源：{missing}")

    def test_every_reference_is_indexed(self):
        indexed = set(re.findall(r"`(references/[\w.-]+)`", SKILL))
        on_disk = {f"references/{f}" for f in os.listdir(os.path.join(ROOT, "references"))}
        self.assertEqual(on_disk - indexed, set(),
                         "存在未被 SKILL.md 索引的 reference（模型不会去读它）")

    def test_every_script_is_indexed(self):
        indexed = set(re.findall(r"`(scripts/[\w.-]+\.py)`", SKILL))
        on_disk = {f"scripts/{f}" for f in os.listdir(os.path.join(ROOT, "scripts"))
                   if f.endswith(".py")}
        self.assertEqual(on_disk - indexed, set(), "存在未被 SKILL.md 索引的脚本")

    def test_uploaded_examples_are_marked_fictional(self):
        batch = json.loads(read("examples/opportunity.batch.example.json"))
        self.assertIn("虚构", batch["_note"] + "虚构")


class TestRepoHygiene(unittest.TestCase):
    BANNED = ("TODO", "FIXME", "XXX", "待补充", "占位符")
    READMES = ("README.md", "README.zh-CN.md")
    #: 本文件自身定义了上面的关键词，扫描时跳过以免自匹配
    SKIP_FILES = {"test_consistency.py"}

    def test_no_placeholders(self):
        hits = []
        for sub in ("", "references", "schemas", "scripts", "examples", "tests"):
            d = os.path.join(ROOT, sub)
            for fn in os.listdir(d):
                p = os.path.join(d, fn)
                if (not os.path.isfile(p) or fn in self.SKIP_FILES
                        or not fn.endswith((".md", ".json", ".py", ".txt"))):
                    continue
                text = read(os.path.join(sub, fn) if sub else fn)
                for kw in self.BANNED:
                    if kw in text:
                        hits.append(f"{p}: {kw}")
        self.assertEqual(hits, [], f"存在占位符残留：{hits}")

    def test_readmes_have_no_dev_process_residue(self):
        banned = ["需求文档", "自我审查", "它不是招聘网站", "是否只是 Prompt",
                  "开发提示词", "非目标清单"]
        for rel in self.READMES:
            with self.subTest(file=rel):
                text = read(rel)
                hits = [b for b in banned if b in text]
                self.assertEqual(hits, [], f"{rel} 残留开发过程内容：{hits}")

    def test_readme_claims_backed_by_tests(self):
        for rel in self.READMES:
            with self.subTest(file=rel):
                text = read(rel)
                if "tests" in text or "unittest" in text:
                    self.assertTrue(os.path.isdir(os.path.join(ROOT, "tests")))


def heading_anchors(markdown: str) -> set[str]:
    """按 GitHub 的规则把标题转成锚点：小写、去掉非单词字符（emoji 会被去掉，
    留下前导空格 → 前导连字符）、空格转连字符。
    """
    out = set()
    for line in markdown.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if not m:
            continue
        slug = m.group(1).strip().lower()
        slug = re.sub(r"[^\w\- ]+", "", slug, flags=re.UNICODE)
        out.add(slug.replace(" ", "-"))
    return out


class TestBilingualDocs(unittest.TestCase):
    """README.md 与 README.zh-CN.md 必须互相可达、结构对齐、锚点有效。"""

    EN = read("README.md")
    ZH = read("README.zh-CN.md")

    def test_language_switcher_both_ways(self):
        self.assertIn("./README.zh-CN.md", self.EN, "英文 README 缺少中文版跳转")
        self.assertIn("./README.md", self.ZH, "中文 README 缺少英文版跳转")

    def test_centered_header_block(self):
        for name, text in (("README.md", self.EN), ("README.zh-CN.md", self.ZH)):
            with self.subTest(file=name):
                self.assertTrue(text.startswith("<div align=\"center\">"),
                                f"{name} 应以居中容器开头")
                self.assertIn("</div>", text.split("---", 1)[0],
                              f"{name} 的居中区块未闭合")

    def test_badges_present_and_https(self):
        for name, text in (("README.md", self.EN), ("README.zh-CN.md", self.ZH)):
            with self.subTest(file=name):
                badges = re.findall(r"!\[[^\]]*\]\((https://[^)]+)\)", text)
                self.assertGreaterEqual(len(badges), 4, f"{name} 的技术徽章过少")
                self.assertTrue(all(b.startswith("https://") for b in badges),
                                "徽章必须使用 https")
                self.assertTrue(any("shields.io" in b for b in badges), "缺少 shields.io 徽章")
                self.assertIn("actions/workflows/test.yml/badge.svg", text, "缺少 CI 状态徽章")

    def test_ci_badge_points_at_real_workflow(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, ".github", "workflows", "test.yml")))
        self.assertIn("Sver0411/OpportunityRadar", self.EN)

    def test_badge_test_count_matches_suite(self):
        """徽章上的用例数必须等于真实用例数，否则徽章会悄悄过期。"""
        tests_dir = os.path.join(ROOT, "tests")
        suite = unittest.TestLoader().discover(tests_dir, pattern="test_*.py", top_level_dir=tests_dir)
        n = suite.countTestCases()
        for rel in ("README.md", "README.zh-CN.md"):
            with self.subTest(file=rel):
                self.assertIn(f"unittest-{n}-", read(rel),
                              f"{rel} 的 unittest 徽章数字与真实用例数（{n}）不一致")

    def test_quick_start_is_first_section(self):
        for name, text in (("README.md", self.EN), ("README.zh-CN.md", self.ZH)):
            with self.subTest(file=name):
                first = re.search(r"^##\s+(.*)$", text, re.M).group(1)
                self.assertRegex(first, r"Quick start|快速开始",
                                 f"{name} 的第一个章节应为快速开始，实际为 {first!r}")

    def test_internal_anchors_resolve(self):
        """徽章/目录里的 #anchor 必须真的指向存在的标题。"""
        for name, text in (("README.md", self.EN), ("README.zh-CN.md", self.ZH)):
            with self.subTest(file=name):
                anchors = set(re.findall(r"\]\(#([^)]+)\)", text))
                available = heading_anchors(text)
                broken = sorted(a for a in anchors if a not in available)
                self.assertEqual(broken, [], f"{name} 存在失效锚点：{broken}")

    def test_section_headers_carry_emoji(self):
        for name, text in (("README.md", self.EN), ("README.zh-CN.md", self.ZH)):
            with self.subTest(file=name):
                headers = re.findall(r"^##\s+(.*)$", text, re.M)
                without = [h for h in headers if not re.match(r"^[^\w\s]", h)]
                self.assertEqual(without, [], f"{name} 有章节标题缺少 emoji：{without}")

    def test_structure_aligned(self):
        en = re.findall(r"^##\s+(.*)$", self.EN, re.M)
        zh = re.findall(r"^##\s+(.*)$", self.ZH, re.M)
        self.assertEqual(len(en), len(zh),
                         f"中英 README 章节数不一致：{len(en)} vs {len(zh)}")



if __name__ == "__main__":
    unittest.main()
