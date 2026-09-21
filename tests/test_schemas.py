"""Schema 契约测试。

* 有 jsonschema 时：做元校验（check_schema）+ 正向/反向用例。
* 无 jsonschema 时：自动跳过这部分，但**标准库的轻量 contract 校验始终运行**
  （运行时零依赖，完整校验只用于 dev/test）。
"""

from __future__ import annotations

import json
import unittest

import _helpers

from common import validate_opportunity, validate_profile

try:
    from jsonschema import Draft202012Validator
    HAVE_JSONSCHEMA = True
except Exception:                                       # noqa: BLE001
    HAVE_JSONSCHEMA = False


def load(rel):
    with open(_helpers.path(rel), encoding="utf-8") as fh:
        return json.load(fh)


PROFILE_EXAMPLES = [f"examples/profiles/{n}" for n in (
    "cs-student.example.json", "biology-student.example.json",
    "design-student.example.json", "iot-student-jp.example.json")]

OPP = load("schemas/opportunity.schema.json")
PROF = load("schemas/profile.schema.json")
BATCH = load("examples/opportunity.batch.example.json")["opportunities"]


class TestJsonParseable(unittest.TestCase):
    def test_all_json_files_parse(self):
        for rel in ["schemas/opportunity.schema.json", "schemas/profile.schema.json",
                    "examples/opportunity.example.json", "examples/profiles/cs-student.example.json",
                    "examples/opportunity.batch.example.json"]:
            with self.subTest(file=rel):
                load(rel)

    def test_examples_declare_themselves_as_fictional(self):
        """示例数据是虚构的，必须在文件内显式声明，避免被当成真实机会复用。"""
        for rel in (["examples/opportunity.example.json",
                     "examples/opportunity.batch.example.json"] + PROFILE_EXAMPLES):
            with self.subTest(file=rel):
                note = load(rel).get("_note", "")
                self.assertTrue(note, f"{rel} 缺少 _note 声明")
                low = note.lower()
                self.assertTrue("fictional" in low or "虚构" in note,
                                f"{rel} 未声明数据为虚构：{note[:60]}")


class TestStdlibContract(unittest.TestCase):
    """始终运行：不需要 jsonschema。"""

    def test_examples_pass_contract(self):
        self.assertEqual(validate_opportunity(load("examples/opportunity.example.json")), [])
        for o in BATCH:
            with self.subTest(rec=o.get("id")):
                self.assertEqual(validate_opportunity(o), [])
        for rel in PROFILE_EXAMPLES:
            with self.subTest(file=rel):
                self.assertEqual(validate_profile(load(rel)), [])

    def test_contract_catches_breakage(self):
        bad = {"id": "ok-2026", "title": "t", "organization": "o",
               "primary_category": "not_a_category"}
        self.assertTrue(validate_opportunity(bad))


@unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema 未安装（仅 dev/test 需要）")
class TestAgainstJsonschema(unittest.TestCase):
    def setUp(self):
        self.vo = Draft202012Validator(OPP)
        self.vp = Draft202012Validator(PROF)

    def test_meta_validation(self):
        Draft202012Validator.check_schema(OPP)
        Draft202012Validator.check_schema(PROF)

    def test_examples_valid(self):
        for rel in PROFILE_EXAMPLES:
            with self.subTest(file=rel):
                self.assertEqual(list(self.vp.iter_errors(load(rel))), [])
        self.assertEqual(list(self.vo.iter_errors(load("examples/opportunity.example.json"))), [])

    def test_batch_valid(self):
        for o in BATCH:
            with self.subTest(rec=o.get("id")):
                self.assertEqual(list(self.vo.iter_errors(o)), [])

    def test_negative_cases_rejected(self):
        cases = [
            {"id": "x", "title": "t", "organization": "o"},                          # 缺 primary_category
            {"id": "x", "title": "t", "organization": "o", "primary_category": "jobs"},   # 非法枚举
            {"id": "Has Space", "title": "t", "organization": "o",
             "primary_category": "career"},                                            # 非法 id
            {"id": "x", "title": "t", "organization": "o", "primary_category": "career",
             "deadline_type": "sometime"},                                             # 非法 deadline_type
            {"id": "x", "title": "t", "organization": "o", "primary_category": "career",
             "evidence": {"deadline": {"status": "maybe"}}},                           # 非法 evidence status
        ]
        for c in cases:
            with self.subTest(case=c):
                self.assertFalse(self.vo.is_valid(c), f"应当被拒绝：{c}")

    def test_cjk_id_accepted(self):
        rec = {"id": "清华大学-暑期科研-2027", "title": "t", "organization": "o",
               "primary_category": "research"}
        self.assertTrue(self.vo.is_valid(rec), "CJK ID 必须被 schema 接受")


class TestSkillFrontmatter(unittest.TestCase):
    """frontmatter 必须符合 Agent Skills 规范的键集合。"""

    ALLOWED = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

    def setUp(self):
        with open(_helpers.path("SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("---"), "SKILL.md 必须以 frontmatter 开头")
        block = text.split("---", 2)[1]
        self.keys = set()
        for line in block.splitlines():
            if line and not line.startswith((" ", "\t", "-")) and ":" in line:
                self.keys.add(line.split(":", 1)[0].strip())
        self.text = text

    def test_no_unexpected_keys(self):
        extra = self.keys - self.ALLOWED
        self.assertEqual(extra, set(),
                         f"frontmatter 含规范外字段（会导致打包/上传硬报错）：{extra}")

    def test_required_fields(self):
        self.assertIn("name", self.keys)
        self.assertIn("description", self.keys)
        self.assertIn("compatibility", self.keys)

    def test_name_is_hyphen_case(self):
        import re
        m = re.search(r"^name:\s*(.+)$", self.text, re.M)
        self.assertTrue(re.fullmatch(r"[a-z0-9-]+", m.group(1).strip()), m.group(1))

    def test_description_has_triggers_and_anti_triggers(self):
        import re
        m = re.search(r"^description:\s*(.+)$", self.text, re.M)
        desc = m.group(1)
        # 说明：Agent Skills 规范**没有**规定 description 的独立长度上限；
        # 文档化的约束是 description + when_to_use 在 skill listing 中被截断到 1536 字符。
        # 这里用更保守的自设预算 1024，保证触发信息在列表里完整可见。
        self.assertLessEqual(len(desc), 1024,
                             "description 超出本项目自设预算（触发信息会被截断）")
        self.assertIn("最近有什么适合我的机会", desc)
        self.assertIn("不触发", desc)

    def test_compatibility_within_500_chars(self):
        import re
        m = re.search(r"^compatibility:\s*(.+)$", self.text, re.M)
        self.assertLessEqual(len(m.group(1)), 500)


if __name__ == "__main__":
    unittest.main()
