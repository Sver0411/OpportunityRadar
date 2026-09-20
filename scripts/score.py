#!/usr/bin/env python3
"""score.py - Opportunity 匹配度与优先级的确定性打分（决策辅助，不是结论）。

三条核心原则：

1. **硬条件优先于模型判断。**
   页面明确写了"仅限博士"，而用户明确是本科 → 结果就是 Ineligible。
   模型 verdict 只能补充语义判断（related field、经验相关性），
   不能推翻 deadline、学历、年级、毕业年份、国籍、学校、GPA、语言成绩这些确定项。
   见 `merge_verdict()`。

2. **画像缺失 ≠ 不满足。**
   Profile 是渐进式构建的，没填语言成绩不等于不会日语。
   信息缺失一律 `Unknown`，只有用户**明确表示**不具备时才向 Ineligible 方向判断。

3. **未知不作 0 分。**
   页面没写技能要求 → 中性分；避免错杀信息不全的真实机会。

Match 与 Priority 分离：`Priority = 0.85*Match + 0.15*Urgency`；
区间类截止日以**截止端点**计算紧迫度（`normalize_date.urgency_days`）。

用法：
  python3 score.py --profile profile.json --opportunities opps.json
  python3 score.py --profile examples/profiles/cs-student.example.json \
                  --opportunities examples/opportunity.batch.example.json --format table
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    DEADLINE_TYPES, EVIDENCE_FIELDS, GOAL_TO_CATEGORY, INTEREST_ALIASES, WEIGHTS,
    canonical_country, is_explicit_none, load_records as load_records_common,
    validate_opportunity,
)
from normalize_date import freshness, parse_date  # noqa: E402
from readiness import readiness  # noqa: E402
from utility import personal_utility  # noqa: E402
import evidence as EV  # noqa: E402

VERDICT_ORDER = {
    "Eligible": 0, "Probably Eligible": 1, "Unknown": 2,
    "Probably Ineligible": 3, "Ineligible": 4,
}
VERDICT_SCORE = {"Eligible": 100, "Probably Eligible": 82, "Unknown": 55,
                 "Probably Ineligible": 25, "Ineligible": 0}

TRUST_SCORE = {"A": 100, "B": 85, "C": 60, "D": 35, None: 50}

#: 进入 Recommended now 的门槛（benchmark 驱动：宁可少推荐，不要推过期/无来源的）
MIN_RECOMMEND_MATCH = 55
#: 已确认不可申请的状态 → 直接 excluded（Freshness Gate）
CLOSED_FRESHNESS = ("closed", "expired")
#: 可以做主推荐的 freshness 状态
OPEN_FRESHNESS = ("open", "likely_open")

PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.35, None: 0.5}

GOAL_TO_VALUE_DIM = {
    "internship": ["career", "portfolio"], "fulltime": ["career", "financial"],
    "research": ["research", "skill"], "competition": ["portfolio", "skill"],
    "education": ["research", "career"], "language": ["skill", "career"],
    "skill": ["skill"], "open_source": ["skill", "portfolio", "networking"],
    "hobby": ["interest"], "funding": ["financial"],
    "event": ["networking", "skill"], "project": ["portfolio", "skill"],
    "entrepreneurship": ["career", "networking"], "networking": ["networking"],
    "career": ["career", "financial"],
}

VALUE_LEVEL = {"high": 1.0, "medium": 0.6, "low": 0.3, "unknown": 0.5, None: 0.5}

#: 出现频率过高、单独命中不能说明技能满足的通用 token
GENERIC_SKILL_TOKENS = frozenset({
    "data", "engineering", "analysis", "analytics", "development", "programming",
    "software", "hardware", "system", "systems", "research", "design", "science",
    "technology", "technical", "computer", "management", "learning", "machine",
    "tools", "tool", "framework", "frameworks", "platform", "application",
    "applications", "related", "field", "knowledge", "experience", "background",
    "ability", "communication", "teamwork", "basic", "advanced", "fundamental",
    "fundamentals", "general", "skill", "skills", "concept", "concepts",
})

#: 技能同族映射（**保守**：只收高确定性的技术同族）
#: 刻意不收录 "Docker↔Kubernetes"、"Python↔Machine Learning"、"React↔Frontend"
#: 这类概念扩张，也不把 C 与 C++ 视为等价（C++ 单列一族）。
SKILL_ALIAS_FAMILIES = {
    "rtos": ("freertos", "zephyr", "threadx", "rt-thread", "rtthread", "nuttx",
             "micrium", "vxworks", "rtos", "real-time operating system"),
    "esp32": ("esp32", "esp32-s3", "esp32-c3", "esp32-c6", "esp32-s2", "esp-idf"),
    "ros": ("ros", "ros2", "ros 2"),
    "javascript": ("javascript", "js", "ecmascript", "node", "nodejs", "node.js"),
    "typescript": ("typescript", "ts"),
    "c++": ("c++", "cpp", "cplusplus"),
    "linux": ("linux", "ubuntu", "debian", "raspbian", "embedded linux", "yocto"),
    "tinyml": ("tinyml", "tflite", "tensorflow lite", "tensorflow lite micro", "edge impulse"),
    "arduino": ("arduino", "avr", "atmega"),
    "sql": ("sql", "mysql", "postgresql", "postgres", "sqlite", "mariadb"),
    "pytorch": ("pytorch", "torch"),
    "tensorflow": ("tensorflow", "keras"),
    "hdl": ("fpga", "verilog", "vhdl", "systemverilog"),
}

#: 反向索引：任一写法 → 家族名
SKILL_ALIAS_INDEX = {alias: fam for fam, aliases in SKILL_ALIAS_FAMILIES.items() for alias in aliases}


#: 页面写明"不限制国籍/向所有人开放"的信号
NATIONALITY_OPEN_SIGNALS = (
    "国籍不問", "国籍不问", "国籍不限", "無国籍要件", "no nationality requirement",
    "open to all nationalities", "any nationality", "regardless of nationality",
    "open to students worldwide", "international students welcome", "all applicants",
    "不限国籍", "面向全球学生",
)

#: 页面写明"仅限某国国籍/居民/工作许可"的信号（用于识别"这里存在限制"）
NATIONALITY_RESTRICT_SIGNALS = (
    "citizens only", "nationals only", "must be a citizen", "citizenship required",
    "permanent resident", "must reside in", "resident of", "domestic applicants",
    "work authorization", "work permit", "right to work", "authorized to work",
    "visa holder", "passport", "sponsorship not provided",
    "no sponsorship", "legally authorized to work", "国内在住", "日本国籍", "国籍要件",
    "仅限中国籍", "限本校学生", "本国籍", "eea", "swiss national", "eu citizen",
    "gcc", "公民", "在住", "国籍限制",
)

#: 国籍/地区 -> 可识别的措辞（用于把"仅限 X 国籍"与画像国籍做显式比对）
NATIONALITY_DEMONYMS = {
    "japanese": ("japan", "japanese", "日本"),
    "chinese": ("china", "chinese", "中国"),
    "american": ("united states", "usa", "us citizen", "american", "美国"),
    "korean": ("korea", "korean", "韓国", "한국", "韩国"),
    "indian": ("india", "indian", "インド", "印度"),
    "german": ("germany", "german", "ドイツ", "德国"),
    "french": ("france", "french", "フランス", "法国"),
    "british": ("united kingdom", "uk ", "britain", "british", "英国"),
    "australian": ("australia", "australian", "オーストラリア", "澳大利亚"),
    "canadian": ("canada", "canadian", "カナダ", "加拿大"),
    "singaporean": ("singapore", "singaporean", "シンガポール", "新加坡"),
}


def demonym_of(text) -> set[str]:
    low = f" {str(text or '').lower()} "
    out = set()
    for key, aliases in NATIONALITY_DEMONYMS.items():
        if any(a in low for a in aliases):
            out.add(key)
    return out

#: 排除国际申请人的信号
NO_SPONSORSHIP_SIGNALS = ("sponsorship not provided", "no sponsorship", "without sponsorship",
                          "must be legally authorized to work", "work authorization required")


# ------------------------------------------------------------------ 小工具

def norm(s):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u30ff+#.]+", " ", str(s or "").lower()).strip()


def as_list(v):
    if v in (None, "", [], {}):
        return []
    return v if isinstance(v, list) else [v]


def text_of(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return " ".join(text_of(x) for x in v)
    if isinstance(v, dict):
        return " ".join(str(x) for x in v.values() if x is not None)
    return str(v)


def match_any(text: str, needles) -> str | None:
    low = (text or "").lower()
    for n in needles:
        if n.lower() in low:
            return n
    return None


# ------------------------------------------------------------------ 技能匹配

def skill_tokens(text) -> list[str]:
    """技能名 → token 列表。保留 + / # / . 这些对技能名有意义的字符（C++ ≠ C）。"""
    return [t for t in norm(text).split() if t]


def tok_matches(need: str, have: str) -> bool:
    if need == have:
        return True
    if need in GENERIC_SKILL_TOKENS or have in GENERIC_SKILL_TOKENS:
        return False                      # 通用词必须精确相等
    if len(need) >= 4 and (have.startswith(need) or need.startswith(have)):
        return True                       # python ↔ python3、esp32 ↔ esp32-s3
    return False


def skill_families(text) -> set:
    """技能名 → 命中的同族集合（按 token 识别，因此 "RTOS experience" 也能命中 rtos 家族）。"""
    return {SKILL_ALIAS_INDEX[t] for t in skill_tokens(text) if t in SKILL_ALIAS_INDEX}


def skill_hit(required, profile_skills) -> bool:
    """判断某个要求技能是否被画像中的技能覆盖。

    刻意避免"任意 token 交集"式误判：`data engineering` 不应被 `data analysis` 命中
    （仅有通用词 data 重合）。算命中的情况：
      1. 归一化后完全相等
      2. 属于同一**高确定性同族**（RTOS ↔ FreeRTOS、ESP32 ↔ ESP32-S3、c++ ↔ cpp）；
         C 与 C++ **不**属同族
      3. required 的**全部非通用 token** 都能在某个画像技能里找到对应 token
      4. 全是通用词时（如 "data engineering"），要求完整 token 集合都被包含
    """
    req_tokens = skill_tokens(required)
    if not req_tokens:
        return False
    req_families = skill_families(required)
    for ps in profile_skills:
        p_tokens = skill_tokens(ps)
        if not p_tokens:
            continue
        if req_tokens == p_tokens:
            return True
        if req_families and (req_families & skill_families(ps)):
            return True
        sig = [t for t in req_tokens if t not in GENERIC_SKILL_TOKENS and len(t) >= 2]
        if sig and all(any(tok_matches(t, h) for h in p_tokens) for t in sig):
            return True
        if not sig and all(any(tok_matches(t, h) for h in p_tokens) for t in req_tokens):
            return True
    return False


# ------------------------------------------------------------------ Evidence Gate

#: 需要证据才能作为硬性判断依据的字段（与 common.EVIDENCE_FIELDS 对齐）
HARD_GATED_FIELDS = (
    "deadline", "education_level", "student_year", "graduation_window",
    "language_requirement", "nationality_requirement", "school_requirement", "GPA_requirement",
)


def evidence_status(opp, field) -> str:
    """返回字段的证据等级：explicit | inferred | unknown | missing | legacy。

    * explicit / inferred / unknown —— evidence 结构里明确写了
    * missing  —— 有 evidence 结构，但没有追踪这个字段
    * legacy   —— 完全没有 evidence 结构（旧数据）→ 兼容模式
    """
    ev = opp.get("evidence")
    if not isinstance(ev, dict) or not ev:
        return "legacy"
    entry = ev.get(field)
    if not isinstance(entry, dict):
        return "missing"
    st = str(entry.get("status") or "").strip().lower()
    return st if st in ("explicit", "inferred", "unknown") else "missing"


def is_hard_evidence(opp, field) -> bool:
    """只有 explicit（或旧数据兼容模式）才能参与硬性淘汰。

    `inferred` / `unknown` / `missing` 一律不得用于硬性淘汰 ——
    页面没有明确要求，就不能因为用户"看起来不符合"而淘汰。
    """
    return evidence_status(opp, field) in ("explicit", "legacy")


# ------------------------------------------------------------------ 硬条件：日期 / 学历 / 年级 / 毕业

def deadline_info(opp, today: dt.date) -> dict:
    """截止日信息。**结构化字段优先，原始字符串解析兜底。**

    返回 {days, type, expired, source}：
      * type 优先取 `opp.deadline_type`（由 normalize_date 生成），
        不会因为 `deadline` 为空就被重新推断成 unknown；
      * rolling / asap / flexible / tbd 一律不计算天数，也不判过期；
      * 只有 fixed / range 才用 `deadline` 计算剩余天数（区间取截止端点）。
    """
    raw = opp.get("deadline")
    declared = opp.get("deadline_type")
    declared = declared if declared in DEADLINE_TYPES else None

    if declared in ("rolling", "asap", "flexible", "tbd"):
        return {"days": None, "type": declared, "expired": False if declared == "rolling" else None,
                "source": "field"}

    if raw in (None, ""):
        return {"days": None, "type": declared or "unknown", "expired": None,
                "source": "field" if declared else "none"}

    res = parse_date(str(raw), now=today.isoformat())
    parsed_type = res.get("deadline_type")
    return {"days": res.get("urgency_days"),
            "type": declared or parsed_type or "unknown",
            "expired": res.get("expired"),
            "source": "field+parse" if declared else "parse"}


def parse_ym_pairs(text) -> list[tuple[int, int | None]]:
    """从文本中抽取 (年, 月) 对；只有年份时月为 None。"""
    s = str(text or "")
    out: list[tuple[int, int | None]] = []
    # A year range is not a year-month pair: 2026-2027 must retain both years.
    if re.search(r"(?<!\d)(?:19|20)\d{2}\s*[-–—~～至到]\s*(?:19|20)\d{2}(?!\d)", s):
        return [(int(y), None) for y in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", s)]
    for m in re.finditer(r"(?<!\d)(\d{4})\s*[-/.年]\s*(\d{1,2})(?!\d)\s*月?", s):
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            out.append((y, mo))
        else:
            out.append((y, None))
    if not out:
        for m in re.finditer(r"(?i)\b" + r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
                             + r"[a-z]*\.?\s*,?\s*(\d{4})", s):
            mon = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                   "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}[m.group(1).lower()]
            out.append((int(m.group(2)), mon))
    if not out:
        for m in re.finditer(r"(?<!\d)((?:19|20)\d{2})(?!\d)", s):
            out.append((int(m.group(1)), None))
    return out


def parse_grad_window(text):
    """把毕业时间要求解析成可比较的月份区间 (start_ym, end_ym, year_only)。

    start_ym/end_ym 形如 (2027, 9) / (2028, 6)；(year, None) 表示只有年份精度。
    无法解析时返回 None。
    """
    pairs = parse_ym_pairs(text)
    if not pairs:
        return None
    if len(pairs) == 1:
        y, m = pairs[0]
        if m is None:
            return (y, 1), (y, 12), True
        return (y, m), (y, m), False
    y0, m0 = pairs[0]
    y1, m1 = pairs[-1]
    a = (y0, m0 if m0 is not None else 1)
    b = (y1, m1 if m1 is not None else 12)
    if a > b:
        a, b = b, a
    return a, b, (m0 is None and m1 is None)


def ym_of_graduation(value):
    """用户毕业时间 → (year, month|None)。"""
    pairs = parse_ym_pairs(value)
    if not pairs:
        return None
    return pairs[0]


def in_grad_window(user_ym, window) -> tuple[bool | None, str]:
    if not user_ym or not window:
        return None, "无法比较"
    start, end, year_only = window
    uy, um = user_ym
    if year_only or um is None:
        lo, hi = start[0], end[0]
        return (lo <= uy <= hi), f"按年份比较（要求 {lo}-{hi}）"
    lo = (start[0], start[1] if start[1] else 1)
    hi = (end[0], end[1] if end[1] else 12)
    return (lo <= (uy, um) <= hi), f"按月比较（要求 {lo[0]}-{lo[1]:02d} ~ {hi[0]}-{hi[1]:02d}）"


# ------------------------------------------------------------------ 硬条件：GPA / 语言 / 国籍 / 学校

def parse_gpa(value):
    """解析 GPA 表达 → (数值, 满分) ；无法解析返回 None。不做跨体系换算。"""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value), None
    s = str(value).strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), None
    return None


def gpa_check(required, user_value) -> tuple[str, str]:
    """返回 (结果, 说明)。结果 ∈ ok / fail / unknown_missing / unknown_incomparable。"""
    req = parse_gpa(required)
    usr = parse_gpa(user_value)
    if req is None:
        return "unknown_incomparable", "页面 GPA 要求无法解析"
    if usr is None:
        return "unknown_missing", "画像未提供 GPA，无法确认是否达标"
    (rv, rs), (uv, us) = req, usr
    if rs is None or us is None:
        return "unknown_incomparable", "评分体系不完整，无法比较（不做换算）"
    if abs(rs - us) > 1e-6:
        return "unknown_incomparable", f"评分体系不同（{uv}/{us} vs {rv}/{rs}），不做换算"
    if uv + 1e-6 >= rv:
        return "ok", f"GPA {uv}/{us} 满足要求 {rv}/{rs}"
    return "fail", f"GPA {uv}/{us} 低于要求 {rv}/{rs}"


#: 语言考试识别
LANGUAGE_EXAMS = {
    "japanese language proficiency test": "JLPT", "jlpt": "JLPT",
    "toeic": "TOEIC", "toefl": "TOEFL", "ielts": "IELTS", "gre": "GRE", "gmat": "GMAT",
    "cet-6": "CET6", "cet-4": "CET4", "cet6": "CET6", "cet4": "CET4", "cet": "CET",
    "topik": "TOPIK", "hsk": "HSK", "jtest": "JTEST", "teps": "TEPS",
}

#: 语言名 → 规范值
LANGUAGE_NAMES = {
    "japanese": "japanese", "日本語": "japanese", "日语": "japanese", "日文": "japanese",
    "english": "english", "英語": "english", "英语": "english", "英文": "english",
    "chinese": "chinese", "中文": "chinese", "汉语": "chinese", "中国語": "chinese",
    "korean": "korean", "한국어": "korean", "韓国語": "korean", "韩语": "korean", "韓語": "korean",
    "german": "german", "deutsch": "german", "德语": "german", "ドイツ語": "german",
    "french": "french", "français": "french", "法语": "french", "フランス語": "french",
    "spanish": "spanish", "español": "spanish", "スペイン語": "spanish",
    "russian": "russian", "俄语": "russian", "ロシア語": "russian",
    "italian": "italian", "italiano": "italian", "意大利语": "italian",
    "portuguese": "portuguese", "português": "portuguese", "葡萄牙语": "portuguese",
}

#: 只有自然语言描述、**不可量化**的能力表述：不得映射成 JLPT / CEFR 分数
QUALITATIVE_LEVEL_PHRASES = (
    "business level", "business-level", "native level", "native-level", "native speaker",
    "professional working proficiency", "professional proficiency", "working proficiency",
    "full professional proficiency", "fluent", "conversational", "daily conversation",
    "beginner level", "intermediate level", "advanced level",
    "ビジネスレベル", "ネイティブ", "日常会話", "業務レベル", "商务水平", "母语水平",
)

CEFR_ORDER = ("a1", "a2", "b1", "b2", "c1", "c2")


def parse_levels(text, default_unit: str = "") -> dict:
    """从文本中提取 {单位: 数值}。单位 ∈ jlpt / cefr / cet_level / 考试名。

    **不同单位之间不比较、不换算**（JLPT N2 ≠ IELTS 6.5 ≠ TOEIC 800）——
    单位不一致时由调用方返回 Unknown，而不是伪造一个换算结果。
    方向统一为"数值越大越好"：JLPT N1=5 … N5=1；CEFR a1=0 … c2=5；
    CET-4=2、CET-6=3（与 CET 的分数 425–710 分属不同单位，避免把等级当分数比较）。
    """
    s = " ".join(skill_tokens(text))
    out: dict = {}
    m = re.search(r"\bn\s?([1-5])\b", s)
    if m:
        out["jlpt"] = float(6 - int(m.group(1)))
    m = re.search(r"\b([abc][12])\b", s)
    if m and m.group(1) in CEFR_ORDER:
        out["cefr"] = float(CEFR_ORDER.index(m.group(1)))
    m = re.search(r"\bcet\s?[-\s]?\s?([46])\b", s)
    if m:
        out["cet_level"] = 2.0 if m.group(1) == "4" else 3.0
        s = re.sub(r"\bcet\s?[-\s]?\s?[46]\b", " ", s)
    m = re.search(r"(?<![a-z0-9])(\d{1,3}(?:\.\d)?)\s*\+?", s)
    if m:
        out[default_unit or "numeric"] = float(m.group(1))
    return out


def qualitatives_in(text) -> list[str]:
    low = f" {str(text or '').lower()} "
    return [q for q in QUALITATIVE_LEVEL_PHRASES if q in low]


def normalize_language_requirement(item) -> dict:
    """把 string / object 两种形态统一成一个结构。

    返回 {language, exam, level_text, raw, levels, qualitative, quantifiable}
      * quantifiable=True  → 提取到可比较的单位化等级，可参与硬性判断
      * quantifiable=False 且 qualitative 非空 → 只有自然语言描述（business-level 等），
        交给语义判断，**绝不**映射成具体等级
    """
    if isinstance(item, dict):
        language_raw = str(item.get("language") or "")
        exam_raw = str(item.get("exam") or "")
        level_text = str(item.get("min_level") or "")
        raw = " ".join(x for x in (language_raw, exam_raw, level_text) if x)
    else:
        language_raw = exam_raw = ""
        level_text = str(item or "")
        raw = str(item or "")

    blob = " ".join(skill_tokens(f"{language_raw} {exam_raw} {level_text}"))
    language = next((v for k, v in LANGUAGE_NAMES.items() if k in blob), "")
    exam = next((v for k, v in sorted(LANGUAGE_EXAMS.items(), key=lambda kv: -len(kv[0]))
                 if k in blob), "")
    if not language and exam == "JLPT":
        language = "japanese"
    levels = parse_levels(blob, default_unit=exam)
    if not exam:
        levels.pop("numeric", None)      # 没有考试上下文时，裸数字不构成可比较等级
        if language == "japanese" and "jlpt" in levels:
            exam = "JLPT"                # "Japanese N2" 即 JLPT N2（N 级为 JLPT 专用）
    qualitative = qualitatives_in(raw)
    return {"language": language, "exam": exam, "level_text": level_text, "raw": raw,
            "levels": levels, "qualitative": qualitative, "quantifiable": bool(levels)}


def entry_language_units(entry) -> tuple[set, dict]:
    """画像语言条目 → (语言规范值集合, {单位: 数值})。

    注意必须走 skill_tokens()（会小写化）——否则 "TOEIC" 这类大写考试名匹配不到，
    成绩会被当成无单位的裸数字（曾因此把 TOEIC 900 判为无法比对）。
    """
    blob = " ".join(skill_tokens(f"{entry.get('language','')} {entry.get('exam','')} "
                                 f"{entry.get('score','')} {entry.get('level','')}"))
    toks = blob.split()
    langs = {LANGUAGE_NAMES[t] for t in toks if t in LANGUAGE_NAMES}
    exam = next((v for k, v in sorted(LANGUAGE_EXAMS.items(), key=lambda kv: -len(kv[0]))
                 if k in blob), "")
    if not langs and exam == "JLPT":
        langs = {"japanese"}
    return langs, parse_levels(blob, default_unit=exam)


def language_check(opp, profile) -> tuple[str, str]:
    """返回 (结果, 说明)。结果 ∈ ok / unknown_missing / unknown_low_info / fail。"""
    entries = [e for e in as_list(profile.get("languages")) if isinstance(e, dict)]
    results = []
    for item in as_list(opp.get("language_requirement")):
        req = normalize_language_requirement(item)
        lang = req["language"]
        # string 形态直接用原文做标签，避免拼出 "japanese JLPT Japanese JLPT N2" 这类重复
        if isinstance(item, dict):
            label = " ".join(x for x in (lang or "语言", req["exam"], req["level_text"]) if x)
        else:
            label = req["raw"].strip() or "语言能力"

        cands = []
        for e in entries:
            langs, units = entry_language_units(e)
            if (lang and lang in langs) or (not lang and req["exam"]
                                            and any(u == req["exam"] for u in units)):
                cands.append((e, units))
        if not cands:
            results.append(("unknown_missing",
                            f"页面要求 {label}，画像中未记录该语言 → 无法判断（缺失不等于不会）"))
            continue

        if any(is_explicit_none(e.get("level")) or is_explicit_none(e.get("score")) for e, _ in cands):
            results.append(("fail", f"画像明确标注不具备该语言（{lang or label}），而页面有硬性语言要求"))
            continue

        if not req["quantifiable"]:
            hint = f"（页面措辞：{req['qualitative'][0]}）" if req["qualitative"] else ""
            results.append(("unknown_low_info",
                            f"页面语言要求 {label}{hint} 无法量化为可比较的等级 → 交语义判断，"
                            "不做硬性判定"))
            continue

        req_units = req["levels"]
        satisfied = False
        below = None
        incomparable = False
        for _e, units in cands:
            comparable = False
            for unit, need in req_units.items():
                have = units.get(unit)
                if have is None:
                    continue
                comparable = True
                if have + 1e-6 >= need:
                    satisfied = True
                else:
                    below = f"页面要求 {label}，画像中的成绩未达该等级"
                break
            if not comparable and units:
                incomparable = True

        if satisfied:
            results.append(("ok", f"语言要求（{label}）与画像记录相符"))
        elif below:
            results.append(("fail", below))
        elif incomparable:
            results.append(("unknown_low_info",
                            f"页面要求 {label}，画像记录的是另一套评分体系 → 不做换算，需人工确认"))
        else:
            results.append(("unknown_low_info",
                            f"页面要求 {label}，画像有该语言但未记录对应成绩/等级 → 信息不足（不是不满足）"))
    if not results:
        return "ok", ""
    for kind, msg in results:
        if kind == "fail":
            return "fail", msg
    for kind, msg in results:
        if kind.startswith("unknown"):
            return kind, msg
    return "ok", results[0][1]


def nationality_check(opp, profile) -> tuple[str, str]:
    req_text = text_of(opp.get("nationality_requirement"))
    if not req_text:
        return "none", ""
    if match_any(req_text, NATIONALITY_OPEN_SIGNALS):
        return "ok", "页面明确不限制国籍"
    user_nat = (profile.get("nationality")
                or (profile.get("education") or {}).get("nationality") or "")
    visa = (profile.get("constraints") or {}).get("visa") or ""
    no_sponsor = match_any(req_text, NO_SPONSORSHIP_SIGNALS)
    if no_sponsor and "need_sponsor" in str(visa).lower():
        return "fail", "页面明确不提供工作签证赞助，而画像标注需要赞助"
    if not user_nat and not visa:
        return "unknown_missing", (
            f"页面有国籍/工作许可限制（{req_text[:40]}），画像未提供国籍与签证信息 → 无法判断")

    required_demo = demonym_of(req_text)
    user_demo = demonym_of(user_nat) if user_nat else set()
    if required_demo and user_demo:
        if required_demo & user_demo:
            return "ok", f"画像国籍与页面要求相符（{user_nat}）"
        return "fail", (f"页面限定 {'/'.join(sorted(required_demo))} 国籍，"
                        f"画像为 {user_nat} → 明确不符")
    if required_demo and not user_demo:
        return "unknown_low_info", "页面写有国籍限制，但画像国籍表述无法与之比对"
    restricted = match_any(req_text, NATIONALITY_RESTRICT_SIGNALS)
    if restricted:
        return "unknown_low_info", (
            f"页面含限制性措辞（{restricted}）但未写明可逐字比对的具体国籍/地区 → 需人工确认是否影响你")
    # requirement 非空但解析器读不懂 —— **绝不**默认"没有限制"
    return "unknown_low_info", (
        f"页面 nationality_requirement 非空但无法解析（{req_text[:40]}）→ "
        "未知不等于没有限制，需人工确认")


#: 学校名里过于通用、不能单独支撑命中的词
GENERIC_SCHOOL_TOKENS = frozenset({
    "university", "college", "institute", "institutes", "school", "academy", "national",
    "federal", "state", "大学", "学院", "大学院", "国立", "公立", "the", "of",
})


def school_tokens(text) -> list[str]:
    return [t for t in re.split(r"[^0-9a-z\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]+",
                                str(text or "").lower()) if t]


def school_match(school, req) -> bool:
    """学校名匹配：整词/整串匹配，或**全部有效 token**命中。

    刻意不用裸 `in` 子串判断：`MIT` 会命中 `adMITted`、`adMIT` 这类词内部片段。
    """
    sc = str(school or "").strip().lower()
    rq = str(req or "").strip().lower()
    if not sc or not rq:
        return False
    # 英文/数字：要求作为独立词出现（CJK 无词边界，整串出现即可）
    if re.search(rf"(?<![0-9a-z]){re.escape(sc)}(?![0-9a-z])", rq):
        return True
    rq_tokens = set(school_tokens(rq))
    sig = [t for t in school_tokens(sc)
           if len(t) >= 3 and t not in GENERIC_SCHOOL_TOKENS]
    return bool(sig) and all(t in rq_tokens for t in sig)


def school_check(opp, profile) -> tuple[str, str]:
    req = text_of(opp.get("school_requirement"))
    if not req:
        return "none", ""
    school = (profile.get("education") or {}).get("school")
    if not school:
        return "unknown_missing", f"页面有学校限制（{req[:40]}），画像未提供学校信息"
    if school_match(school, req):
        return "ok", f"画像学校与页面要求相符（{school}）"
    return "unknown_low_info", "页面写有学校限制，但无法确认你的学校是否在其范围内（不推断为不符合）"


# ------------------------------------------------------------------ 资格判定

def _sev(verdict: str) -> int:
    return VERDICT_ORDER.get(verdict, 2)


def merge_verdict(hard: str | None, hard_kind: str, agent: str | None) -> tuple[str, str]:
    """合并硬条件结论与模型 verdict。

    hard_kind ∈ hard_conflict | hard_ok | missing_profile | missing_source |
                incomparable | none

    * 硬冲突（hard_conflict）→ 模型不得推翻（可降不可升）
    * 硬条件满足（hard_ok）→ 模型只能更保守，不能更乐观
    * missing_profile → 模型可判断（它可能在对话里拿到了画像之外的信息）
    * missing_source / incomparable → 模型最多给到 Probably Eligible
    """
    if hard is None:
        return (agent or "Unknown"), ("agent" if agent else "none")
    if hard_kind == "hard_conflict" and _sev(hard) >= 3:
        return hard, "hard_constraint"
    if hard_kind == "missing_profile":
        return (agent or hard), ("agent" if agent else "hard_constraint")
    if hard_kind in ("missing_source", "incomparable", "evidence_gate"):
        # 页面信息不足、口径不可比、或证据等级不足：模型可以补上它读到的额外信息，
        # 但不得给出比"Probably Eligible"更确定的结论。
        if agent and _sev(agent) < _sev("Probably Eligible"):
            return "Probably Eligible", "agent_clamped"
        return (agent or hard), ("agent" if agent else "hard_constraint")
    # hard_ok / none：模型可以更保守，但不能更乐观
    if agent and _sev(agent) > _sev(hard):
        return agent, "agent_downgrade"
    return hard, "hard_constraint"


# ---------------------------------------------------------------- 画像 provenance

#: profile 中会进入硬性资格判断的字段路径
ELIGIBILITY_PROFILE_PATHS = (
    "education.degree", "education.current_year", "education.expected_graduation",
    "education.GPA", "education.school", "education.major", "education.major_family",
    "nationality", "languages", "constraints.visa",
)

INFERRED_PENDING = "inferred_pending"


def profile_provenance(profile, path) -> str:
    """字段级 provenance：_provenance[path] → 顶层 _source → 缺省 user_stated。"""
    prov = profile.get("_provenance")
    if isinstance(prov, dict) and path in prov:
        return str(prov[path]).strip().lower()
    src = profile.get("_source")
    if isinstance(src, str) and src.strip():
        return src.strip().lower()
    return "user_stated"


def filter_profile_for_eligibility(profile) -> tuple[dict, list[str]]:
    """摘掉标记为 `inferred_pending` 的画像字段，只用于**资格判断**。

    推断出来的信息可以参与搜索扩词与排序（那两处仍用完整画像），
    但不能当成"用户明确说过"去做硬性淘汰 —— 否则一个猜错的年级会让用户被误判为不符合资格。
    返回 (可用于资格的画像副本, 被摘掉的字段路径列表)。
    """
    safe = copy.deepcopy(profile)
    stripped: list[str] = []
    for path in ELIGIBILITY_PROFILE_PATHS:
        if profile_provenance(profile, path) != INFERRED_PENDING:
            continue
        parts = path.split(".")
        node = safe
        for p in parts[:-1]:
            node = node.get(p) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, dict) and parts[-1] in node:
            node[parts[-1]] = None
            stripped.append(path)
    return safe, stripped


def eligibility_component(opp, profile, today, stripped_fields=None):
    """对**所有**有数据的硬条件逐项检查，取最严重的结论作为最终硬判定。

    四条规则：
      1. 不做"第一个满足就返回"的短路：学历满足但语言信息缺失 → Unknown，不是 Eligible。
      2. **没有任何硬性信息 → Unknown**（页面没写要求 ≠ 用户大概率符合）。
      3. **Evidence Gate**：只有 evidence=explicit（或旧数据无 evidence 的 legacy 模式）
         才能用于硬性淘汰；inferred / unknown / missing 一律不得淘汰，改判 Unknown。
      4. `Ineligible` 只用于**无歧义**的冲突（枚举值/日期：学历、学年、毕业窗口、已过期）；
         文本类冲突（国籍措辞、学校名单、语言表述、GPA 口径）用 `Probably Ineligible`。

    返回 (score, verdict, reasons[], needs_llm, verdict_source, kind, warnings[])。
    """
    reasons: list[str] = []
    warnings: list[str] = []
    today = today or dt.date.today()
    ed = profile.get("education") or {}
    degree = ed.get("degree")
    if isinstance(degree, list):
        degree = degree[0] if degree else None
    agent_verdict = (opp.get("eligibility") or {}).get("verdict")
    needs_llm = False
    capped = False          # 存在非 explicit 证据 → 不给最乐观结论
    gated = False           # 曾因证据不足把淘汰改判为 Unknown

    found: list[tuple[str, str, str]] = []      # (verdict, kind, reason)

    def add(verdict, kind, reason, field, unambiguous=False):
        nonlocal capped, gated
        st = evidence_status(opp, field)
        if verdict in ("Ineligible", "Probably Ineligible"):
            if not is_hard_evidence(opp, field):
                found.append(("Unknown", "evidence_gate", reason))
                reasons.append(reason + "（证据不足，未作为淘汰依据）")
                warnings.append(
                    f"{field} 的证据等级为 {st or 'unknown'}，不能作为硬性淘汰依据 → 改判 Unknown")
                gated = True
                return
            if verdict == "Ineligible" and not unambiguous:
                verdict = "Probably Ineligible"
        if verdict in ("Eligible", "Probably Eligible") and st != "explicit":
            capped = True
        found.append((verdict, kind, reason))
        reasons.append(reason)

    # 1. 时间窗口
    dinfo = deadline_info(opp, today)
    if dinfo["expired"]:
        add("Ineligible", "hard_conflict", f"报名截止日已过（{opp.get('deadline')}）",
            field="deadline", unambiguous=True)
    elif dinfo["type"] == "rolling":
        reasons.append("滚动招募，无固定截止日")

    # 2. 学历（枚举值 → 无歧义）
    # education_level is the applicant's *current* qualification, never the
    # degree awarded by an education opportunity (program_degree).
    levels = [str(x) for x in as_list(opp.get("education_level"))]
    if levels and "any" not in levels:
        if not degree:
            add("Unknown", "missing_profile", f"页面限定学历 {levels}，画像未提供学历 → 无法判断",
                field="education_level")
        elif degree not in levels:
            add("Ineligible", "hard_conflict", f"页面限定学历 {levels}，画像学历为 {degree}",
                field="education_level", unambiguous=True)
        else:
            add("Eligible", "hard_ok", f"学历相符（{degree} 在 {levels} 内）", field="education_level")

    # 3. 学年
    years = [y for y in as_list(opp.get("student_year")) if str(y).isdigit()]
    cy = ed.get("current_year")
    if years:
        if not cy:
            add("Unknown", "missing_profile", f"页面限定学年 {years}，画像未提供年级 → 无法判断",
                field="student_year")
        elif int(cy) not in [int(y) for y in years]:
            add("Ineligible", "hard_conflict", f"页面限定学年 {years}，画像为 {cy} 年级",
                field="student_year", unambiguous=True)
        else:
            add("Eligible", "hard_ok", f"学年相符（{cy} 在 {years} 内）", field="student_year")

    # 4. 毕业时间窗口（按月比较）
    if opp.get("graduation_window"):
        window = parse_grad_window(opp["graduation_window"])
        user_ym = ym_of_graduation(ed.get("expected_graduation"))
        if window and not user_ym:
            add("Unknown", "missing_profile",
                f"页面要求毕业时间 {opp['graduation_window']}，画像未提供毕业时间 → 无法判断",
                field="graduation_window")
        elif window and user_ym:
            ok, how = in_grad_window(user_ym, window)
            if ok is True:
                add("Eligible", "hard_ok", f"毕业时间落在要求窗口内（{how}）",
                    field="graduation_window")
            elif ok is False:
                add("Ineligible", "hard_conflict", f"毕业时间不在要求窗口内（{how}）",
                    field="graduation_window", unambiguous=True)
            else:
                add("Unknown", "incomparable", "毕业时间无法比较（解析失败）", field="graduation_window")
        else:
            add("Unknown", "incomparable", f"页面毕业时间要求无法解析：{opp['graduation_window']!r}",
                field="graduation_window")

    # 5. 国籍 / 工作许可（文本措辞 → 只用 Probably Ineligible）
    nat_state, nat_msg = nationality_check(opp, profile)
    if nat_msg:
        if nat_state == "fail":
            add("Probably Ineligible", "hard_conflict", nat_msg, field="nationality_requirement")
        elif nat_state == "unknown_missing":
            add("Unknown", "missing_profile", nat_msg, field="nationality_requirement")
        elif nat_state == "unknown_low_info":
            add("Unknown", "incomparable", nat_msg, field="nationality_requirement")
        elif nat_state == "ok":
            add("Eligible", "hard_ok", nat_msg, field="nationality_requirement")

    # 6. 学校限制（名单/措辞无法完整解析 → 只用 Unknown / Probably Ineligible）
    sch_state, sch_msg = school_check(opp, profile)
    if sch_msg:
        if sch_state == "unknown_missing":
            add("Unknown", "missing_profile", sch_msg, field="school_requirement")
        elif sch_state == "unknown_low_info":
            add("Unknown", "incomparable", sch_msg, field="school_requirement")
        elif sch_state == "ok":
            add("Eligible", "hard_ok", sch_msg, field="school_requirement")

    # 7. GPA（同体系才比较）
    if opp.get("GPA_requirement"):
        state, msg = gpa_check(opp["GPA_requirement"], ed.get("GPA"))
        if state == "fail":
            add("Probably Ineligible", "hard_conflict", msg, field="GPA_requirement")
        elif state.startswith("unknown"):
            add("Unknown", "missing_profile" if state == "unknown_missing" else "incomparable",
                msg, field="GPA_requirement")
        else:
            add("Eligible", "hard_ok", msg, field="GPA_requirement")

    # 8. 语言
    if opp.get("language_requirement"):
        state, msg = language_check(opp, profile)
        if state == "fail":
            add("Probably Ineligible", "hard_conflict", msg, field="language_requirement")
        elif state.startswith("unknown"):
            add("Unknown", "missing_profile" if state == "unknown_missing" else "incomparable",
                msg, field="language_requirement")
        else:
            add("Eligible", "hard_ok", msg, field="language_requirement")

    # 9. 专业（语义条件：只区分 Eligible / Probably Eligible，不作为硬冲突）
    if opp.get("major_requirement"):
        mr = text_of(opp.get("major_requirement"))
        major = norm(ed.get("major"))
        if not major:
            add("Unknown", "missing_profile", "页面有专业要求，但画像未提供专业 → 无法判断",
                field="major_requirement")
        else:
            tokens = [t for t in major.split() if len(t) > 2]
            if tokens and any(t in norm(mr) for t in tokens):
                add("Probably Eligible", "semantic_ok",
                    "专业要求与画像专业字面相关（最终以组织方定义为准）", field="major_requirement")
            else:
                needs_llm = True
                add("Probably Eligible", "semantic_review",
                    "专业要求需语义判断（related field 类表述）：不构成硬冲突，但要按组织方定义确认",
                    field="major_requirement")

    if not found:
        # 页面对资格条件什么都没写 —— 没写要求 ≠ 大概率符合
        hard, kind = "Unknown", "missing_source"
        reasons.append("页面未写明任何硬性资格条件，也没有可判定的冲突项 → 无法判断"
                       "（没写要求不等于大概率符合）")
    else:
        hard, kind, _ = max(found, key=lambda x: _sev(x[0]))
        if gated and _sev(hard) <= 2:
            kind = "evidence_gate"
    if hard == "Eligible" and capped:
        hard = "Probably Eligible"
    if capped:
        legacy = any(evidence_status(opp, f) == "legacy" for f in HARD_GATED_FIELDS)
        warnings.append(
            "该记录没有 evidence 结构（旧格式）：硬性判断未标注来源，结论封顶在 Probably Eligible"
            if legacy else
            "存在 inferred/unknown 证据：乐观结论封顶在 Probably Eligible，不能给出 Eligible")

    for path in (stripped_fields or []):
        warnings.append(f"画像字段 {path} 标记为 inferred_pending，未用于资格判断")

    final, source = merge_verdict(hard, kind, agent_verdict)
    if agent_verdict and _sev(agent_verdict) < _sev(hard) and kind == "hard_conflict":
        reasons.append(f"注意：模型判定为 {agent_verdict}，但被硬性条件覆盖为 {final}")
    return VERDICT_SCORE.get(final, 55), final, reasons, needs_llm, source, kind, warnings


# ------------------------------------------------------------------ 其余分项

LEVEL_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.3, "unknown": 0.5, None: 0.5}


def goal_component(opp, profile):
    """目标契合：先看类别，再看 **V3 outcome facets**（跨类别命中）。

    为什么需要 outcome：一个 CFP（`event`）对 networking / skill 目标是强契合，
    但按类别匹配会判成"不重合" —— 这正是 V3 要修的"字段只存在于 JSON 里"的问题。
    """
    goals = as_list(profile.get("goals"))
    if not goals:
        return 60.0, "画像未提供目标，按中性处理"
    cats = {opp.get("primary_category")} | set(as_list(opp.get("secondary_categories")))
    outcomes = opp.get("outcomes") or {}
    # 目标的"价值维度"名与 outcome facet 名不完全相同（networking ↔ network）
    FACET_ALIAS = {"networking": "network", "financial": "financial"}
    best, note = 0.0, "与声明的目标不重合"
    for g in goals:
        if not isinstance(g, dict):
            continue
        w = PRIORITY_WEIGHT.get(g.get("priority"), 0.5)
        for c in GOAL_TO_CATEGORY.get(g.get("type"), []):
            if opp.get("primary_category") == c:
                if w > best:
                    best, note = w, f"命中目标 {g.get('type')}（priority={g.get('priority')}）"
            elif c in cats:
                if w * 0.8 > best:
                    best, note = w * 0.8, f"作为次要类别命中目标 {g.get('type')}"
            else:
                # 跨类别：用"这个机会能带来什么"（outcome facet）命中目标
                facet = FACET_ALIAS.get(c, c)
                level = LEVEL_SCORE.get(str(outcomes.get(facet)).lower(), 0.5)
                if facet in outcomes and level >= 0.6:
                    v = w * level
                    if v > best:
                        best, note = v, f"产出 outcomes.{facet}={outcomes[facet]} 命中目标 {g.get('type')}"
    return (100.0 * best if best else 15.0), note


def skill_component(opp, profile):
    ps = [s.get("name") if isinstance(s, dict) else s for s in as_list(profile.get("skills"))]
    req = as_list(opp.get("skills_required"))
    pref = as_list(opp.get("skills_preferred"))
    if not ps:
        return 50.0, "画像未提供技能，按中性处理"
    if req:
        hit = [r for r in req if skill_hit(r, ps)]
        rc = len(hit) / len(req)
        pc = (sum(1 for p in pref if skill_hit(p, ps)) / len(pref)) if pref else 0.0
        return 100 * (0.75 * rc + 0.25 * pc), f"硬性技能覆盖 {len(hit)}/{len(req)}" + (
            f"（命中：{', '.join(map(str, hit))}）" if hit else "")
    if pref:
        pc = sum(1 for p in pref if skill_hit(p, ps)) / len(pref)
        return 100 * (0.35 + 0.5 * pc), f"页面只写了偏好技能，覆盖 {pc:.0%}"
    return 50.0, "页面未写明技能要求"


def interest_component(opp, profile):
    interests = as_list(profile.get("interests"))
    if not interests:
        return 55.0, "画像未提供兴趣"
    text = " ".join([norm(str(opp.get("title"))), norm(str(opp.get("summary"))),
                     " ".join(norm(t) for t in as_list(opp.get("tags"))),
                     norm(str(opp.get("primary_category"))),
                     " ".join(norm(x) for x in as_list(opp.get("major_requirement"))),
                     " ".join(norm(k) for k in (opp.get("outcomes") or {})),
                     " ".join(norm(x) for x in as_list(opp.get("produces"))),
                     " ".join(norm(x) for x in as_list(opp.get("skills_preferred"))),
                     " ".join(norm(x) for x in as_list(opp.get("skills_required")))])
    matched = []
    for it in interests:
        key = norm(it)
        aliases = INTEREST_ALIASES.get(key, [key])
        if any(norm(a) and norm(a) in text for a in aliases):
            matched.append(it)
    if not matched:
        return 20.0, "未发现与画像兴趣的重合信号"
    ratio = len(matched) / len(interests)
    return 100 * (0.25 + 0.75 * min(1.0, ratio * 2)), f"兴趣命中：{', '.join(matched)}"


def city_match(a, b) -> bool:
    """城市匹配：token 集合相等或一方包含另一方（"Nagoya" ↔ "Nagoya City"）。不用子串。"""
    ta, tb = set(school_tokens(a)), set(school_tokens(b))
    if not ta or not tb:
        return False
    return ta == tb or ta <= tb or tb <= ta


def location_component(opp, profile):
    c = profile.get("constraints") or {}
    pref_countries = [v for v in (canonical_country(x) for x in as_list(c.get("preferred_country"))) if v]
    pref_cities = as_list(c.get("preferred_city"))
    pref_regions = as_list(c.get("preferred_region"))
    remote_pref = c.get("remote")
    relocation = c.get("relocation")
    if not pref_countries and not pref_cities and not pref_regions and remote_pref is None:
        return 60.0, "画像未提供地区约束"

    raw_country = opp.get("country")
    opp_country = canonical_country(raw_country)
    opp_city = opp.get("city")
    opp_region = opp.get("region")

    if pref_cities and opp_city and any(city_match(x, opp_city) for x in pref_cities):
        return 100.0, f"城市匹配：{opp_city}"
    if pref_regions and opp_region and any(city_match(x, opp_region) for x in pref_regions):
        return 98.0, f"省/地区匹配：{opp_region}"
    if pref_regions and opp_region and not any(city_match(x, opp_region) for x in pref_regions):
        return 30.0, f"省/地区 {opp_region} 不在偏好列表中"
    if pref_regions and not opp_region and pref_countries and opp_country in pref_countries:
        return 55.0, "国家匹配，但页面未证实所在省/地区"
    if pref_countries and opp_country and opp_country in pref_countries:
        return 95.0, f"国家/地区匹配：{raw_country}"
    if opp.get("remote") and remote_pref:
        return 95.0, "远程，符合你的 remote 偏好"
    if opp.get("remote") and remote_pref is None:
        return 85.0, "远程机会（画像未表态，按可接受处理）"
    if opp_country and pref_countries and opp_country not in pref_countries:
        return (60.0 if relocation else 25.0), f"地区为 {raw_country}，不在偏好列表中"
    if raw_country and pref_countries and opp_country is None:
        # 页面写法无法规范化 → 不做子串猜测（"US" 会命中 "Belarus"）
        return 55.0, f"页面地区写法（{raw_country}）无法与偏好列表比对 → 地区信息不足"
    if not raw_country and not opp.get("remote"):
        return 45.0, "页面未写明地点，无法确认地区匹配"
    return 55.0, "地区信息不足"


def value_component(opp, profile):
    v = opp.get("value") or {}
    if not v:
        return 55.0, "尚未评估价值维度"
    goals = as_list(profile.get("goals"))
    dims = []
    for g in sorted([g for g in goals if isinstance(g, dict)],
                    key=lambda g: -PRIORITY_WEIGHT.get(g.get("priority"), 0.5)):
        dims = GOAL_TO_VALUE_DIM.get(g.get("type"), [])
        if dims:
            break
    if not dims:
        dims = list(v.keys())
    vals = [VALUE_LEVEL.get(str(v.get(d, "")).lower(), 0.5) for d in dims if d in v]
    if not vals:
        return 55.0, "价值评估与目标维度无交集"
    return 100 * sum(vals) / len(vals), f"按目标相关维度（{', '.join(dims)}）评分"


def trust_component(opp):
    t = opp.get("trust_tier")
    score = TRUST_SCORE.get(t, 50)
    vs = opp.get("verification_status")
    note = f"来源 Tier {t}" if t else "来源层级未知"
    if vs == "conflicting":
        score -= 5
        note += "，官方与第三方信息冲突（已以官方为准）"
    elif vs == "unverified":
        score -= 10
        note += "，未获官方确认"
    elif vs == "expired":
        score -= 30
        note += "，官方页面显示已结束"
    elif vs == "verified_official":
        note += "，3 项关键事实已官方确认"
    return max(0, score), note


def novelty_component(opp, seen_index):
    if seen_index is None:
        return 80.0, "无本地状态，按新机会处理"
    st = opp.get("seen_status") or seen_index.get(opp.get("id"))
    if st == "repeat":
        return 40.0, "上次已推荐且无变化"
    if st == "changed":
        return 90.0, "已见过但有关键字段变化"
    if st == "new" or st is None:
        return 100.0, "新发现"
    return 80.0, "状态未知"


def urgency_score(days):
    if days is None:
        return None
    if days < 0:
        return 0.0
    if days <= 3:
        return 100.0
    if days <= 7:
        return 92.0
    if days <= 14:
        return 82.0
    if days <= 30:
        return 68.0
    if days <= 60:
        return 50.0
    if days <= 120:
        return 35.0
    return 20.0


def band(score):
    return "High" if score >= 80 else ("Medium" if score >= 60 else "Low")


def recommendation_zone(row: dict) -> str:
    """Final Recommendation Gate（benchmark 失败驱动）。

    返回三个输出区之一：
      * ``recommended_now``  —— 现在值得申请：freshness 为 open/likely_open、
        有 canonical source、官方已核实且有申请状态证据、不是 Ineligible，
        并且（match 达到最低门槛 **或 Personal Utility 为 high**）。
      * ``worth_verifying``  —— 有价值但状态/来源/资格未确认，单独区域展示。
      * ``excluded``         —— 已过期/已结束，或明确不符合资格。

    Utility 之所以能替代 match 门槛：渐进式画像下 match 常因未知分项偏低，
    而 Utility 已经综合了 readiness / outcome / 投入 / 未来通道 ——
    它是 V3 的决策层，不能只活在 JSON 里。
    """
    if row.get("freshness") and row["freshness"].get("status") in CLOSED_FRESHNESS:
        return "excluded"
    if row.get("verdict") == "Ineligible":
        return "excluded"
    if row.get("conflicts"):
        # 时间冲突 / dealbreaker：不是 Ineligible，但不能和低投入机会一样推荐（V3 §35）
        return "worth_verifying"
    # actionable 已编码：open/likely_open，或 evergreen/recurring + 当前参与证据
    if row.get("actionable") \
            and str(row.get("official_url") or "").strip() \
            and row.get("verification_status") == "verified_official" \
            and row.get("application_status_evidence") \
            and row.get("size_verified", True) \
            and row.get("evidence_complete") \
            and row.get("actionable") \
            and (row.get("match", 0) >= MIN_RECOMMEND_MATCH or row.get("utility") == "high"):
        return "recommended_now"
    return "worth_verifying"


def actionable_evidence(opp, today):
    """Only a dated, official, field-specific observation can support 'apply now'."""
    if opp.get("verification_status") != "verified_official":
        return False
    ev = opp.get("evidence") or {}
    for field in ("application_status", "deadline"):
        item = ev.get(field) or {}
        if item.get("status") != "explicit" or not item.get("source_url"):
            continue
        date_text = item.get("verified_at") or opp.get("last_verified")
        try:
            age = (today - dt.date.fromisoformat(str(date_text)[:10])).days
        except (TypeError, ValueError):
            continue
        if 0 <= age <= 30:
            return True
    return False


# ------------------------------------------------------------------ 主流程

#: 明确的小时表述（周为默认周期）
HOUR_PATTERNS = (
    r"(\d{1,3})\s*(?:h|hr|hrs|hour|hours)\b",
    r"(\d{1,3})\s*(?:時間|小时)",
    r"(?:每周|每週|週|周)\s*(\d{1,3})\s*(?:時間|小时)",
)

#: 非"周"周期（月/年/日）——与"每周可投入小时数"不是同一量纲，不做换算
NON_WEEKLY_PERIOD = ("month", "monthly", "year", "annual", "day", "daily",
                     "ヶ月", "か月", "个月", "每月")


def parse_hours(text):
    """只有当文本**明确表达小时语义**时才返回数字（默认按周理解）。

    "3 months full-time"、"part-time"、"2 days/week" 无法可靠换算成每周小时数，
    一律返回 `None`，交给模型做语义提醒 —— 绝不能把 "3 months" 当成 3 小时/周。
    """
    if text in (None, ""):
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).lower()
    if any(p in s for p in NON_WEEKLY_PERIOD):
        return None
    for pat in HOUR_PATTERNS:
        m = re.search(pat, s, re.I)
        if m:
            return float(m.group(1))
    return None


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def evidence_gaps(opp) -> list[str]:
    """按 evidence 结构指出关键字段的证据缺口（没有 evidence 时退回 notes 提示）。"""
    ev = opp.get("evidence") or {}
    gaps = []
    for f in EVIDENCE_FIELDS:
        entry = ev.get(f)
        if not isinstance(entry, dict):
            continue
        st = entry.get("status")
        if st in ("inferred", "unknown"):
            gaps.append(f"{f}: {st}" + (f"（{entry.get('note')}）" if entry.get("note") else ""))
        elif st == "explicit" and not entry.get("source_url"):
            gaps.append(f"{f}: explicit 但缺 source_url")
    return gaps


def score_all(profile, opps, seen_index=None, today=None, strict=False, context=None):
    today = today or dt.date.today()
    if context:
        # Current-turn intent overrides persistent preferences for this run only.
        profile = copy.deepcopy(profile)
        if "goals" in context:
            profile["goals"] = context["goals"]
        current = context.get("constraints") or {}
        retained = dict(profile.get("constraints") or {})
        if "preferred_country" in current:
            retained.pop("preferred_region", None)
            retained.pop("preferred_city", None)
        profile["constraints"] = {**retained, **current}
    results, excluded, contract_issues = [], [], []
    # 只用于资格判断：把 inferred_pending 的画像字段摘掉；其余分项仍用完整画像
    safe_profile, stripped = filter_profile_for_eligibility(profile)

    for opp in opps:
        if not isinstance(opp, dict):
            continue
        issues = validate_opportunity(opp)
        if issues:
            contract_issues.append({"id": opp.get("id"), "errors": issues})
            if strict:
                continue

        (el_score, verdict, el_reasons, needs_llm, v_source, v_kind,
         el_warnings) = eligibility_component(opp, safe_profile, today, stripped)
        goal_fit, goal_note = goal_component(opp, profile)
        skill_fit, skill_note = skill_component(opp, profile)
        interest_fit, interest_note = interest_component(opp, profile)
        location_fit, location_note = location_component(opp, profile)
        value_fit, value_note = value_component(opp, profile)
        trust, trust_note = trust_component(opp)
        novelty, novelty_note = novelty_component(opp, seen_index)
        comp = {
            "eligibility": el_score, "goal_fit": goal_fit, "skill_fit": skill_fit,
            "interest_fit": interest_fit, "location_fit": location_fit,
            "value_fit": value_fit, "trust": trust, "novelty": novelty,
        }
        match = round(sum(WEIGHTS[k] * v for k, v in comp.items()))

        fr = freshness(opp, today)
        if fr["status"] in CLOSED_FRESHNESS:
            excluded.append({"id": opp.get("id"), "title": opp.get("title"),
                             "reason": f"{fr['status']}: {fr['reason']}"})
            continue

        size_pref = as_list((profile.get("constraints") or {}).get("organization_size"))
        size = opp.get("organization_size")
        if size_pref and size and size != "unknown" and size not in size_pref:
            excluded.append({"id": opp.get("id"), "title": opp.get("title"),
                             "reason": f"企业规模 {size} 不符合本轮限定 {size_pref}"})
            continue
        size_ev = (opp.get("evidence") or {}).get("organization_size") or {}
        size_verified = not size_pref or (size in size_pref and size_ev.get("status") == "explicit"
                                          and bool(size_ev.get("source_url")))

        dinfo = deadline_info(opp, today)
        ug, dtype = dinfo["days"], dinfo["type"]
        us = urgency_score(ug)
        flags, warnings = [], list(el_warnings)

        if verdict == "Ineligible":
            excluded.append({"id": opp.get("id"), "title": opp.get("title"),
                             "reason": "Ineligible: " + "；".join(el_reasons)})
            continue
        if dinfo["expired"] and not is_hard_evidence(opp, "deadline"):
            warnings.append(f"截止日已过（{opp.get('deadline')}）但证据等级不足，未直接排除，请人工确认")

        if ug is not None and ug <= 14:
            flags.append("urgent")
        if dtype in ("rolling", "asap", "flexible", "tbd"):
            flags.append(dtype)
        if dtype == "unknown" and opp.get("deadline") in (None, ""):
            flags.append("no_deadline")
        hours = parse_hours(opp.get("time_commitment"))
        limit = parse_hours((profile.get("constraints") or {}).get("weekly_time"))
        if hours and limit and hours > limit:
            flags.append("heavy_load")
            warnings.append(f"时间投入（{opp.get('time_commitment')}）超出你的每周上限 {limit:g}h")
        if opp.get("verification_status") == "unverified":
            flags.append("unverified")
            warnings.append("未找到官方确认来源")
        if not str(opp.get("official_url") or "").strip():
            flags.append("no_canonical_source")
            warnings.append("未找到官方来源（canonical source），不得进入 Recommended now")

        # V3：readiness + 冲突检测（gate 的一部分，不改权重）
        rd = readiness(opp, profile)
        conflicts = []
        for b in rd["blockers"]:
            if "时间冲突" in b:
                conflicts.append("heavy_commitment_conflict")
                flags.append("heavy_commitment_conflict")
            else:
                conflicts.append("dealbreaker_conflict")
                flags.append("dealbreaker_conflict")
            warnings.append(b)
        if rd["status"] == "unknown":
            flags.append("readiness_unknown")

        # V3：证据前置检查（extraction 后、gate 前）—— Match/Utility 都不能绕过
        evc = EV.check(opp, today)
        actionable = fr["status"] in OPEN_FRESHNESS or (
            fr["status"] in ("evergreen", "recurring") and evc["participation_open"])
        if not evc["complete"]:
            flags.append("evidence_incomplete")
            warnings.append("证据不完整：缺少 " + "、".join(evc["missing"])
                            + "（不得进入 Recommended now）")

        # V3：Personal Utility（决策层）—— 让 Utility 真正影响推荐，不只是 JSON 字段
        util = personal_utility(opp, profile, {"eligibility_verdict": verdict, "components": comp,
                                               "urgency": None})

        _row = {"freshness": fr, "official_url": opp.get("official_url"),
                "verification_status": opp.get("verification_status"),
                "application_status_evidence": actionable_evidence(opp, today),
                "size_verified": locals().get("size_verified", True),
                "conflicts": conflicts, "evidence_complete": evc["complete"],
                "actionable": actionable, "utility": util["band"], "match": match,
                "verdict": verdict}
        zone = recommendation_zone(_row)
        demotion = None if zone == "recommended_now" else EV.demotion_reason(opp, _row, evc)
        if needs_llm:
            flags.append("needs_semantic_check")
        if not opp.get("language_requirement"):
            flags.append("language_unspecified")
            warnings.append("页面未写明语言要求")
        if evidence_status(opp, "deadline") == "legacy":
            flags.append("provenance_unavailable")
        for g in evidence_gaps(opp):
            warnings.append(f"证据缺口 {g}")

        priority = round(0.85 * match + 0.15 * us) if us is not None else match
        if "heavy_load" in flags:
            priority -= 5
        if "unverified" in flags:
            priority -= 8

        results.append({
            "id": opp.get("id"),
            "title": opp.get("title"),
            "organization": opp.get("organization"),
            "primary_category": opp.get("primary_category"),
            "layer": opp.get("layer"),
            "components": comp,
            "eligibility_verdict": verdict,
            "eligibility_source": v_source,
            "eligibility_kind": v_kind,
            "eligibility_reasons": el_reasons,
            "match_score": match,
            "match_band": band(match),
            "urgency": us,
            "days_remaining": ug,
            "deadline_type": dtype,
            "deadline_source": dinfo["source"],
            "freshness": fr["status"],
            "freshness_reason": fr["reason"],
            "evidence_complete": evc["complete"],
            "evidence_missing": evc["missing"],
            "evidence_verified_at": evc["application_status"]["verified_at"],
            "participation_open": evc["participation_open"],
            "actionable": actionable,
            "utility": util["band"],
            "utility_reasons": util["reasons"][:3],
            "readiness": rd["status"],
            "readiness_detail": rd,
            "conflicts": conflicts,
            "zone": zone,
            "demotion": demotion,
            "priority_score": priority,
            "priority_band": band(priority),
            "flags": flags,
            "warnings": warnings,
            "reasons": {
                "goal_fit": goal_note,
                "skill_fit": skill_note,
                "interest_fit": interest_note,
                "location_fit": location_note,
                "value_fit": value_note,
                "trust": trust_note,
                "novelty": novelty_note,
            },
        })

    results.sort(key=lambda r: (-r["priority_score"], -r["match_score"], str(r["id"])))

    cats, layers = {}, {}
    for r in results:
        cats[r["primary_category"]] = cats.get(r["primary_category"], 0) + 1
        if r["layer"]:
            layers[r["layer"]] = layers.get(r["layer"], 0) + 1
    diversity = {
        "categories": cats,
        "layers": layers,
        "checks": {
            "categories_ge_3": len(cats) >= 3,
            "has_adjacent": layers.get("adjacent", 0) >= 1,
            "has_explore": layers.get("explore", 0) >= 1,
            "single_category_share_ok": (max(cats.values()) / len(results) <= 0.5) if results else None,
        },
        "note": "这是覆盖面自检（参考值），不是硬性配额：Adjacent/Explore 只在达到质量与"
                "验证门槛时纳入，绝不为凑配额塞入弱机会。见 references/ranking.md §3。",
    }

    return {
        "params": {"weights": WEIGHTS,
                   "priority_formula": "0.85*match + 0.15*urgency（区间以截止端点计）",
                   "today": today.isoformat(),
                   "disclaimer": "确定性打分，仅作排序辅助；展示时用档次 + 理由，不要展示裸分数当结论"},
        "scored": len(results),
        "results": results,
        "excluded": excluded,
        "contract_issues": contract_issues,
        "diversity": diversity,
        "zones": {
            "recommended_now": sum(1 for r in results if r.get("zone") == "recommended_now"),
            "worth_verifying": sum(1 for r in results if r.get("zone") == "worth_verifying"),
            "excluded": len(excluded),
        },
    }


def render_table(res):
    out = ["| # | 机会 | 类别 | Match | 紧迫 | Priority | 档 | 资格 | 判定来源 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(res["results"], 1):
        out.append(f"| {i} | {r['title']} | {r['primary_category']} | {r['match_score']} "
                   f"| {'' if r['urgency'] is None else int(r['urgency'])} | {r['priority_score']} "
                   f"| {r['priority_band']} | {r['eligibility_verdict']} | {r['eligibility_source']} |")
    if res["excluded"]:
        out += ["", "已排除："] + [f"- {e['id']}: {e['reason']}" for e in res["excluded"]]
    if res.get("contract_issues"):
        out += ["", "contract 问题："] + [f"- {c['id']}: {c['errors'][0]}" for c in res["contract_issues"]]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Opportunity 匹配度/优先级确定性打分（决策辅助）")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--context", help="本轮目标/地区 JSON；仅覆盖本轮评分，不修改画像")
    ap.add_argument("--opportunities", required=True)
    ap.add_argument("--seen", help="seen.json，用于 novelty 与重复处理")
    ap.add_argument("--today", help="参照日期 YYYY-MM-DD，默认今天")
    ap.add_argument("--output")
    ap.add_argument("--format", choices=["json", "table"], default="json")
    ap.add_argument("--strict", action="store_true", help="出现 contract 问题时跳过该记录")
    ap.add_argument("--zone", choices=["recommended_now", "worth_verifying"], default=None,
                    help="只输出 Final Recommendation Gate 之后某个区的结果")
    args = ap.parse_args(argv)

    profile = load_json(args.profile)
    opps = load_records_common(args.opportunities)
    seen_index = None
    if args.seen and os.path.exists(args.seen):
        seen_index = {k: v.get("status") for k, v in (load_json(args.seen).get("entries") or {}).items()}

    today = dt.date.fromisoformat(args.today) if args.today else None
    context = load_json(args.context) if args.context else None
    res = score_all(profile, opps, seen_index, today, strict=args.strict, context=context)
    if args.zone:
        keep = [r for r in res["results"] if r.get("zone") == args.zone]
        res["results"] = keep
        res["scored"] = len(keep)
    if res["contract_issues"]:
        print(f"[warn] {len(res['contract_issues'])} 条记录存在 contract 问题"
              "（见输出 contract_issues 字段）", file=sys.stderr)
    payload = render_table(res) if args.format == "table" else json.dumps(res, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print(f"写入 {args.output}（scored={res['scored']} excluded={len(res['excluded'])}）", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
