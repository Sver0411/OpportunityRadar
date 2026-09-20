"""跨文件一致性测试：同一个概念在 SKILL.md / references / schemas / scripts 里只能有一套定义。

这是"单一事实来源"的机器化保证：任何一处枚举或权重被改动而另一处没跟上，测试会失败。
文档测试只检查**功能性**问题（文件存在、相对链接与锚点有效、无开发残留），
不检查视觉风格（徽章数量、emoji、中英章节数是否 1:1）。
"""

from __future__ import annotations

import json
import os
import re
import unittest

import _helpers

import common as C

ROOT = _helpers.ROOT
READMES = ("README.md", "README.en.md")


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

    def test_layers_agree(self):
        schema_l = tuple(x for x in OPP_SCHEMA["properties"]["layer"]["enum"] if x)
        self.assertEqual(schema_l, C.LAYERS)

    def test_visibility_agree(self):
        schema_v = tuple(x for x in OPP_SCHEMA["properties"]["seen_status"]["enum"] if x)
        self.assertEqual(schema_v, C.VISIBILITY)
        for v in C.VISIBILITY:
            self.assertIn(v, STATE_DOC, f"state-and-feedback.md 未说明状态 {v}")

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

    def test_hard_gated_fields_covered_by_evidence_fields(self):
        """score.py 的 Evidence Gate 字段必须都在 schema 的证据字段清单内，否则无法标注。"""
        src = read("scripts/score.py")
        m = re.search(r"HARD_GATED_FIELDS = \((.*?)\)", src, re.S)
        gated = set(re.findall(r'"(\w+)"', m.group(1)))
        self.assertTrue(gated <= set(C.EVIDENCE_FIELDS),
                        f"Evidence Gate 字段未纳入 schema 证据字段：{gated - set(C.EVIDENCE_FIELDS)}")

    def test_mode_weights_cover_all_categories(self):
        import locales as L
        for mode, w in L.MODE_WEIGHTS.items():
            with self.subTest(mode=mode):
                self.assertEqual(set(w), set(C.CATEGORIES))
        for mode in ("A", "B", "C", "D"):
            self.assertIn(f"**{mode}", read("references/search-strategy.md"),
                          f"search-strategy.md 未说明模式 {mode}")


    def test_v3_profile_enums_match_schema(self):
        """V3：life_stage / career_stage 的取值必须与 common.py 完全一致。"""
        prof = json.loads(read("schemas/profile.schema.json"))
        props = prof["properties"]
        for field, enum in (("life_stage", C.LIFE_STAGES), ("career_stage", C.CAREER_STAGES)):
            with self.subTest(field=field):
                items = props[field]["items"]["enum"]
                self.assertEqual(tuple(items), tuple(enum))
        self.assertEqual(tuple(props["readiness"] if False else []), ())

    def test_v3_opportunity_enums_match_schema(self):
        """V3：outcomes facets / readiness statuses 必须与 common.py 一致。"""
        opp = json.loads(read("schemas/opportunity.schema.json"))
        props = opp["properties"]
        self.assertEqual(tuple(sorted(props["outcomes"]["properties"])),
                         tuple(sorted(C.OUTCOME_FACETS)))
        self.assertEqual(tuple(props["readiness"]["properties"]["status"]["enum"][:-1]),
                         tuple(C.READINESS_STATUSES))
        self.assertEqual(tuple(props["time_to_value"]["enum"][:-1]), tuple(C.TIME_TO_VALUE))
        self.assertEqual(tuple(sorted(props["career_capital"]["properties"])),
                         tuple(sorted(C.CAPITAL_DIMS)))
        self.assertIn("unlocks", props)
        self.assertIn("produces", props)
        self.assertIn("goal_contribution", props)
        self.assertIn("future_optionality", props)
        self.assertIn("career_leverage", props)

    def test_v3_new_scripts_indexed(self):
        for rel in ("scripts/readiness.py", "scripts/graph.py", "scripts/coverage.py",
                    "scripts/utility.py"):
            with self.subTest(script=rel):
                self.assertIn(rel, SKILL)

    def test_profile_provenance_documented(self):
        self.assertIn("_provenance", PROF_SCHEMA["properties"])
        src = read("scripts/score.py")
        self.assertIn("filter_profile_for_eligibility", src)
        self.assertIn("inferred_pending", src)


class TestNoDuplicatedLogic(unittest.TestCase):
    """canonical_url / derive_id / norm_org / 国家规范化只能有一份实现（common.py）。"""

    SHARED = ("def canonical_url", "def derive_id", "def norm_org", "def slugify",
              "def canonical_country", "TRACKED_FIELDS =", "def core_title",
              "GOAL_TO_CATEGORY = {", "INTEREST_ALIASES = {")

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
        on_disk = {f"references/{f}" for f in os.listdir(os.path.join(ROOT, "references"))
                   if os.path.isfile(os.path.join(ROOT, "references", f))}
        # locales/ 是一个目录：SKILL.md 说明"generic 常加载 + 按地区加载 <cc>.md"即可
        groups = ("references/locales", "references/source-families")
        for f in sorted(on_disk - indexed):
            with self.subTest(file=f):
                self.assertTrue(any(g in SKILL and f.startswith(g) for g in groups),
                                f"未被索引：{f}")

    def test_source_family_files_documented(self):
        """source-families 里的每个文件都要在它自己的 README 中列出。"""
        d = os.path.join(ROOT, "references", "source-families")
        readme = read("references/source-families/README.md")
        for f in sorted(os.listdir(d)):
            if f == "README.md" or not f.endswith(".md"):
                continue
            with self.subTest(file=f):
                self.assertIn(f, readme, f"{f} 未在 source-families/README.md 中列出")

    def test_locale_files_all_documented(self):
        import locales as L
        for region, cc in L.LOCALE_FILES.items():
            with self.subTest(region=region):
                path = os.path.join(ROOT, "references", "locales", f"{cc}.md")
                self.assertTrue(os.path.exists(path), f"{path} 不存在")
                self.assertIn(f"{cc}.md", read("references/locales/README.md"),
                              f"locales/README.md 未列出 {cc}.md")
        self.assertTrue(os.path.exists(os.path.join(ROOT, L.GENERIC_LOCALE_FILE)))

    def test_locale_module_is_indexed(self):
        self.assertIn("scripts/locales.py", SKILL)

    def test_every_script_is_indexed(self):
        indexed = set(re.findall(r"`(scripts/[\w.-]+\.py)`", SKILL))
        on_disk = {f"scripts/{f}" for f in os.listdir(os.path.join(ROOT, "scripts"))
                   if f.endswith(".py")}
        self.assertEqual(on_disk - indexed, set(), "存在未被 SKILL.md 索引的脚本")

    def test_uploaded_examples_are_marked_fictional(self):
        """示例文件必须显式声明数据为虚构（真实断言，不是恒真）。"""
        profiles = [f"examples/profiles/{n}" for n in sorted(
            os.listdir(os.path.join(ROOT, "examples", "profiles")))]
        for rel in (["examples/opportunity.example.json",
                     "examples/opportunity.batch.example.json"] + profiles):
            with self.subTest(file=rel):
                note = json.loads(read(rel)).get("_note", "")
                self.assertTrue(note, f"{rel} 缺少 _note")
                self.assertTrue("fictional" in note.lower() or "虚构" in note,
                                f"{rel} 未声明数据为虚构")


class TestRepoHygiene(unittest.TestCase):
    BANNED = ("TODO", "FIXME", "XXX", "待补充", "占位符")
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
        for rel in READMES:
            with self.subTest(file=rel):
                hits = [b for b in banned if b in read(rel)]
                self.assertEqual(hits, [], f"{rel} 残留开发过程内容：{hits}")

    def test_readme_claims_backed_by_tests(self):
        for rel in READMES:
            with self.subTest(file=rel):
                text = read(rel)
                if "tests" in text or "unittest" in text:
                    self.assertTrue(os.path.isdir(os.path.join(ROOT, "tests")))

    def test_readme_does_not_reference_missing_paths(self):
        """README 里提到的仓库内路径必须真实存在（脚本/目录/文件）。"""
        for rel in READMES:
            text = read(rel)
            refs = set(re.findall(r"\]\(\.?/?((?:assets|references|schemas|scripts|examples|tests|"
                                  r"README[\w.-]*\.md|DEVELOPMENT\.md|SKILL\.md|LICENSE)[\w./-]*)\)",
                                  text))
            missing = [r for r in refs if not os.path.exists(os.path.join(ROOT, r))]
            with self.subTest(file=rel):
                self.assertEqual(missing, [], f"{rel} 指向不存在的路径：{missing}")


def heading_anchors(markdown: str) -> set[str]:
    """按 GitHub 规则把标题转成锚点：小写、去标点（含 emoji）、空格转连字符。"""
    out = set()
    for line in markdown.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if not m:
            continue
        slug = m.group(1).strip().lower()
        slug = re.sub(r"[^\w\- ]+", "", slug, flags=re.UNICODE)
        out.add(slug.replace(" ", "-"))
    return out


class TestDocsFunctional(unittest.TestCase):
    """只检查功能性：文件存在、相对链接与锚点有效。不检查视觉风格。"""

    def test_both_readmes_exist_and_cross_link(self):
        for rel in READMES:
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)), f"{rel} 不存在")
        self.assertIn("./README.en.md", read("README.md"))
        self.assertIn("./README.md", read("README.en.md"))
        self.assertIn("./README.md", read("README.zh-CN.md"))

    def test_internal_anchors_resolve(self):
        """`](#anchor)` 必须指向本文件里存在的标题。"""
        for rel in READMES:
            with self.subTest(file=rel):
                text = read(rel)
                anchors = set(re.findall(r"\]\(#([^)]+)\)", text))
                broken = sorted(a for a in anchors if a not in heading_anchors(text))
                self.assertEqual(broken, [], f"{rel} 存在失效锚点：{broken}")

    def test_readme_does_not_overclaim_host_support(self):
        """不要把"有联网"等同于"会加载 SKILL.md"。"""
        for rel in READMES:
            with self.subTest(file=rel):
                low = read(rel).lower()
                self.assertNotIn("any web-capable host agent", low)
                self.assertNotIn("no api keys", low)


if __name__ == "__main__":
    unittest.main()
