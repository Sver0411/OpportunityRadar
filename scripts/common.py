#!/usr/bin/env python3
"""common.py - OpportunityRadar 的共享基础模块（单一事实来源）。

这个模块存在的原因：ID 生成、URL 规范化、周期(cycle)提取、各类枚举，如果让
dedupe.py / state.py / score.py 各写一份略有差异的实现，就会出现
"官方 URL 只是 utm 变了却被判为变化" 这类跨脚本不一致。因此这些逻辑只在这里实现一次。

零第三方依赖，仅标准库。

用法（作为 CLI 做轻量 contract 校验）：
  python3 common.py --validate examples/opportunity.example.json
  python3 common.py --validate examples/opportunity.batch.example.json
  python3 common.py --id "Sony Summer Internship 2027" --org "Sony"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit

# ---------------------------------------------------------------- 枚举（单一来源）
# schemas/*.json、references/*.md、tests/ 都以这里的取值为准，并由 tests/test_consistency.py 校验。

CATEGORIES = (
    "career", "research", "competition", "education", "language",
    "skill_development", "open_source", "hobby", "funding", "event",
    "project", "entrepreneurship", "networking",
)

GOAL_TYPES = (
    "career", "internship", "fulltime", "research", "competition", "education", "language",
    "skill", "open_source", "hobby", "funding", "event", "project",
    "entrepreneurship", "networking",
)

ELIGIBILITY_VERDICTS = (
    "Eligible", "Probably Eligible", "Unknown", "Probably Ineligible", "Ineligible",
)

TRUST_TIERS = ("A", "B", "C", "D")

VERIFICATION_STATUSES = (
    "verified_official", "partially_verified", "unverified", "conflicting", "expired",
)

VALUE_LEVELS = ("High", "Medium", "Low", "Unknown")

EVIDENCE_STATUSES = ("explicit", "inferred", "unknown")

#: 需要逐字段追踪证据的关键字段（见 references/extraction-policy.md）
EVIDENCE_FIELDS = (
    "application_status", "deadline", "education_level", "student_year", "graduation_window",
    "major_requirement", "language_requirement", "nationality_requirement",
    "school_requirement", "GPA_requirement", "compensation", "organization_size",
)

DEADLINE_TYPES = ("fixed", "range", "rolling", "evergreen", "recurring",
                  "asap", "flexible", "tbd", "unknown")

LAYERS = ("exploit", "adjacent", "explore")

VISIBILITY = ("new", "changed", "repeat")

#: score.py 与 references/ranking.md §2 必须逐项一致（由测试校验）
WEIGHTS = {
    "eligibility": 0.26,
    "goal_fit": 0.19,
    "skill_fit": 0.15,
    "interest_fit": 0.11,
    "location_fit": 0.10,
    "value_fit": 0.08,
    "trust": 0.06,
    "novelty": 0.05,
}

#: 目标类型 → Opportunity 类别（score.py 与 locales.py 共用，避免两套映射）
GOAL_TO_CATEGORY = {
    "career": ["career"], "internship": ["career"], "fulltime": ["career"], "research": ["research"],
    "competition": ["competition"], "education": ["education"], "language": ["language"],
    "skill": ["skill_development"], "open_source": ["open_source"], "hobby": ["hobby"],
    "funding": ["funding"], "event": ["event"], "project": ["project"],
    "entrepreneurship": ["entrepreneurship"], "networking": ["networking"],
}

#: 兴趣别名（**保守**）：只收语义上确实同指的写法。
#: 覆盖技术与非技术两个方向 —— 兴趣不该只认工程领域。
INTEREST_ALIASES = {
    # 技术
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "llm", "生成"],
    "agent": ["agent", "agents", "multi-agent", "llm agent", "autonomous"],
    "iot": ["iot", "internet of things", "sensor network", "smart device", "スマート"],
    "embedded": ["embedded", "firmware", "mcu", "microcontroller", "rtos", "esp32", "stm32", "組み込み"],
    "robotics": ["robotics", "robot", "ros", "mechatronics", "ロボット"],
    "drone": ["drone", "uav", "quadcopter", "无人机", "ドローン"],
    "automotive": ["automotive", "vehicle", "adas", "automobile", "モビリティ"],
    "aviation": ["aviation", "aerospace", "space", "航空", "宇宙"],
    "maker": ["maker", "3d printing", "diy", "fabrication", "ものづくり"],
    "data": ["data", "analytics", "statistics", "visualization"],
    "security": ["security", "ctf", "cybersecurity", "penetration"],
    "energy": ["energy", "renewable", "power systems", "grid"],
    # 创意与人文
    "design": ["design", "ui", "ux", "graphic", "industrial design", "デザイン"],
    "game": ["game", "gamedev", "unity", "unreal", "esports", "ゲーム"],
    "film": ["film", "cinema", "video", "documentary", "映像"],
    "music": ["music", "audio", "sound design", "音楽"],
    "writing": ["writing", "editorial", "journalism", "copywriting", "写作"],
    "art": ["art", "illustration", "drawing", "animation", "美术"],
    "photography": ["photography", "camera", "photo", "写真", "摄影"],
    "fashion": ["fashion", "textile", "costume", "apparel"],
    # 生命科学 / 环境
    "biology": ["biology", "molecular", "genomics", "microbiology", "cell", "ecology",
                "生物", "バイオ", "life science"],
    "health": ["health", "medical", "clinical", "public health", "nursing", "医疗", "医療"],
    "environment": ["environment", "climate", "sustainability", "conservation", "agriculture",
                    "环境", "気候", "agri"],
    "science_communication": ["science communication", "outreach", "science writing", "科学传播"],
    # 社会科学 / 商业 / 公共
    "business": ["business", "management", "strategy", "consulting", "case competition",
                 "経営", "商業"],
    "finance": ["finance", "investment", "fintech", "accounting", "economics", "金融"],
    "entrepreneurship": ["entrepreneurship", "startup", "venture", "founder", "创业"],
    "law_policy": ["law", "policy", "regulation", "governance", "public administration",
                   "法律", "政策"],
    "education": ["education", "teaching", "pedagogy", "curriculum", "教育"],
    "social_impact": ["social impact", "nonprofit", "civic", "community", "volunteer", "公益"],
    "sports": ["sports", "athletics", "fitness", "esports management"],
    # ---- V3：职场与社区类兴趣（C/D/E 验收发现原先完全缺失，CFP/开源/社区机会匹配为 0）----
    "open_source": ["open source", "oss", "github", "maintainer", "contributor", "开源"],
    "networking": ["networking", "professional network", "community", "meetup", "人脉", "社群"],
    "public_speaking": ["public speaking", "speaker", "talk", "presentation", "演讲"],
}

#: 语言条目里表示"明确不具备"的标记（score.py 资格判定与 locales.py 召回门控共用）。
#: 注意：必须排除 None —— `str(None).lower()` 恰好等于 "none"，会把"未填写"误判成"明确不会"。
LANGUAGE_NONE_MARKERS = ("none", "no", "cannot", "not-available", "不会", "无", "未学", "未修", "不懂")


def is_explicit_none(value) -> bool:
    """是否**明确表示不具备**。None/空值一律返回 False（缺失 ≠ 明确不会）。"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value is False
    s = str(value).strip().lower()
    return bool(s) and s in LANGUAGE_NONE_MARKERS


# ---------------------------------------------------------------- V3 枚举
# 全部 optional、向后兼容；老 profile / opportunity JSON 不含这些字段也必须能跑。

#: 人生状态（可多标签：真实的人不是单一状态）
LIFE_STAGES = ("student", "working", "studying_and_working", "career_break",
               "unemployed", "self_employed", "founder")

#: 职业阶段（可多标签，如 ["early_career", "career_switcher"]）
CAREER_STAGES = ("pre_college", "undergraduate", "graduate_student", "new_grad",
                 "early_career", "mid_career", "senior_ic", "manager", "executive",
                 "researcher", "founder", "freelancer", "career_switcher",
                 "returning_to_work")

#: outcome facet：回答"这个机会能给我带来什么"，不是"它是什么"
OUTCOME_FACETS = ("career", "research", "portfolio", "admission", "credential",
                  "network", "financial", "reputation", "exposure", "skill",
                  "interest", "management", "entrepreneurship")

#: 通用等级（outcome / capital / optionality / leverage 共用）
LEVELS = ("high", "medium", "low", "unknown")

#: 准备度（≠ 资格，≠ 录取率）
READINESS_STATUSES = ("ready_now", "minor_preparation", "short_preparation",
                      "major_preparation", "blocked", "unknown")

#: 价值显现周期
TIME_TO_VALUE = ("immediate", "weeks", "months", "long_term", "unknown")

#: 时间灵活度
SCHEDULE_FLEXIBILITY = ("high", "medium", "low", "unknown")

#: Career capital 维度（针对已工作的人）
CAPITAL_DIMS = ("skill_capital", "portfolio_capital", "network_capital",
                "reputation_capital", "credential_capital", "domain_capital",
                "management_capital", "research_capital")

#: 申请生命周期状态（state.py 扩展用）
APPLICATION_STATUSES = ("discovered", "viewed", "interested", "saved", "preparing",
                        "applied", "interviewing", "accepted", "rejected",
                        "withdrawn", "completed", "ignored")

#: **机会侧**的申请状态（官方页面观察到的机会本身是否开放）。与上面**用户侧**的
#: APPLICATION_STATUSES 是两件事，请不要混用：同一个 key `application_status`
#: 在 opportunity 里指的是机会状态，在 state 里指的是用户进度。
#: 必须与 schemas/opportunity.schema.json 的同名 enum 一致（由测试校验）。
OPPORTUNITY_APPLICATION_STATUSES = ("open", "rolling", "closed", "not_open", "unknown")

#: 视为"现在可以申请/参与"的机会侧状态（主推荐前置条件之一）
PARTICIPATION_OPEN_STATUSES = ("open", "rolling")

#: 中文能力词 → 英文同义 token（只收**直译**，不做语义外推）。
#: 用途：机会要求写中文、画像写英文（或反之）时能互相识别，避免产生幻影缺口。
#: 注意：**不要**把整个兴趣同族组映射过来 —— 「会 ESP32」不等于「会 RTOS」。
SKILL_EQUIVALENTS = {
    "嵌入式": "embedded", "嵌入式开发": "embedded", "单片机": "microcontroller",
    "固件": "firmware", "物联网": "iot", "传感器": "sensor", "机器人": "robotics",
    "无人机": "drone", "人工智能": "ai", "机器学习": "machine learning",
    "深度学习": "deep learning", "大模型": "llm", "数据分析": "data analytics",
    "网络安全": "security", "操作系统": "operating system", "数据结构与算法": "algorithm",
    "前后端": "web", "前端开发": "frontend", "后端开发": "backend", "云计算": "cloud",
    "模拟电路": "analog circuit", "数字电路": "digital circuit", "信号处理": "signal processing",
}

#: 目标类型 → 它真正想要的 **outcome facet** 及权重（≠ 类别别名）。
#: 用途：修"目标 × 类别"失效 —— 升 Senior 想要的是 reputation/leadership/management/network，
#: 这些可以由 open_source / event / networking 类别的机会提供，**但只有机会真的声明了**
#: 对应 outcome 时才算命中（靠归一化分母守住，见 score.goal_component）。
#: facet 名取自 OUTCOME_FACETS；未列出的目标类型走"无偏好"（只用类别腿）。
GOAL_OUTCOME_PROFILE = {
    # 晋升/职业进阶：要可见的影响力与担当，不是再学一门课
    "career": {"reputation": 1.0, "career": 1.0, "management": 0.8, "network": 0.7,
               "portfolio": 0.5, "skill": 0.5, "credential": 0.4},
    "fulltime": {"career": 1.0, "financial": 0.8, "skill": 0.6, "network": 0.4},
    "internship": {"career": 1.0, "skill": 0.8, "network": 0.6, "portfolio": 0.5,
                   "exposure": 0.4},
    "research": {"research": 1.0, "admission": 0.7, "network": 0.6, "portfolio": 0.5,
                 "skill": 0.4, "credential": 0.4},
    "education": {"admission": 1.0, "research": 0.6, "credential": 0.6, "network": 0.4,
                  "skill": 0.5},
    "language": {"skill": 0.8, "admission": 0.7, "credential": 0.7, "career": 0.4},
    "open_source": {"portfolio": 1.0, "reputation": 0.8, "skill": 0.7, "network": 0.6,
                    "career": 0.5},
    "skill": {"skill": 1.0, "credential": 0.5, "portfolio": 0.5, "career": 0.5},
    "competition": {"reputation": 0.8, "portfolio": 0.8, "skill": 0.6, "career": 0.4},
    "project": {"portfolio": 1.0, "skill": 0.7, "career": 0.4},
    "funding": {"financial": 1.0, "research": 0.4, "admission": 0.4},
    "event": {"network": 0.8, "exposure": 0.7, "reputation": 0.5, "skill": 0.4},
    "networking": {"network": 1.0, "reputation": 0.5, "career": 0.4, "exposure": 0.4},
    "entrepreneurship": {"entrepreneurship": 1.0, "network": 0.7, "career": 0.5,
                         "financial": 0.5, "reputation": 0.5},
    "hobby": {"interest": 1.0, "skill": 0.4, "exposure": 0.3},
}

#: Personal Utility 档位（只给用户这三档，不输出裸分数）
UTILITY_BANDS = ("high", "medium", "low", "unknown")

#: 搜索意图（内部 steering，不暴露给用户）
INTENTS = ("discover", "urgent", "portfolio_building", "career_switch", "promotion",
           "research_path", "education_path", "income_growth", "low_commitment",
           "unknown_unknowns", "capability_backfill", "network_building",
           "entrepreneurship")

#: 允许在 `.opportunity-radar/` 下写入的本地状态文件（唯一事实来源）
#: 文档（SKILL.md / references/state-and-feedback.md）必须与此一致，由测试校验。
STATE_FILES = ("profile.json", "seen.json", "saved.json", "ignored.json",
               "last-run.json", "sources.json")

#: `sources.json` 只允许保存的字段（轻量来源产出记录）
#: 禁止：页面正文、搜索结果全文、用户个人信息、凭据
SOURCE_STATE_FIELDS = ("source", "category", "region", "runs", "last_checked",
                       "last_success", "historical_yield", "failure_type")

#: state 目录名
STATE_DIR = ".opportunity-radar"


TRACKED_FIELDS = (
    "deadline", "application_open", "cost", "compensation",
    "application_status", "graduation_window", "education_level", "student_year",
    "major_requirement", "language_requirement", "official_url", "verification_status",
    "country", "region", "city", "organization_size",
)

# ---------------------------------------------------------------- URL 规范化

#: 明确属于投放追踪、删除后不影响站点路由的参数（前缀匹配）
TRACKING_PREFIXES = ("utm_",)

#: 明确属于点击追踪的精确参数名（保守列表：ref / source / from 等可能承载路由语义，故不删）
TRACKING_EXACT = frozenset({
    "gclid", "gbraid", "wbraid", "dclid", "fbclid", "msclkid", "yclid",
    "mc_cid", "mc_eid", "igshid", "_ga", "_gl", "vero_id", "hsctatracking",
})

_CJK = r"\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af"
ID_RE = re.compile(rf"^[0-9a-z{_CJK}][0-9a-z{_CJK}._-]*$")
SLUG_KEEP = re.compile(rf"[^0-9a-z{_CJK}]+")

#: 合理的主机名：至少两级（或 localhost），只含字母数字、连字符、点
HOST_RE = re.compile(r"^(?:localhost|[a-z0-9]([a-z0-9-]*[a-z0-9])?"
                     r"(?:\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+)$")


def canonical_url(url) -> str | None:
    """把 URL 归一化为比较用的规范形式。

    规则（刻意为保守设计）：
      * scheme 不参与比较（http/https 视为同一资源）；host 转小写并去掉 www.
      * **path 大小写保留**——很多服务器路径大小写敏感，统一小写会破坏甚至误合并。
      * 只删除明确属于投放追踪的参数（utm_* 与少量精确名单）。
      * 保留其余 query 参数（按名值排序以保证稳定），丢弃 fragment，去尾斜杠。

    返回形如 `example.com/path?a=1` 的字符串；无 host 时返回 None。
    """
    if not url or not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    if not host or not HOST_RE.match(host):
        return None                    # 不是可识别的 URL（避免把普通文本当域名）
    if host.startswith("www."):
        host = host[4:]
    port = ""
    if parts.port and not ((parts.scheme == "http" and parts.port == 80)
                           or (parts.scheme == "https" and parts.port == 443)):
        port = f":{parts.port}"

    path = re.sub(r"/{2,}", "/", parts.path or "")
    path = path.rstrip("/")            # 保留大小写，仅去尾斜杠

    kept = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        lk = k.lower()
        if lk in TRACKING_EXACT or any(lk.startswith(p) for p in TRACKING_PREFIXES):
            continue
        kept.append((k, v))
    query = urlencode(sorted(kept), doseq=True)

    out = f"{host}{port}{path}"
    return f"{out}?{query}" if query else out


def is_same_url(a, b) -> bool:
    ca, cb = canonical_url(a), canonical_url(b)
    return bool(ca) and ca == cb


# ---------------------------------------------------------------- 国家/地区规范化

#: 国家/地区别名 → 规范值。只收录**含义无歧义**的写法：
#: 刻意不含 "no"/"in"/"it"/"at"/"be"/"is" 这类同时是常用英文单词的两字母代码，
#: 也不收录需要按"中国香港/中国台湾"表述的地区，避免任何主权表述风险。
COUNTRY_ALIASES = {
    "us": "us", "usa": "us", "u.s.": "us", "u.s.a.": "us", "united states": "us",
    "united states of america": "us", "america": "us", "美国": "us",
    "uk": "uk", "u.k.": "uk", "united kingdom": "uk", "britain": "uk",
    "great britain": "uk", "england": "uk", "英国": "uk",
    "japan": "japan", "jp": "japan", "日本": "japan", "日本国": "japan",
    "china": "china", "cn": "china", "中国": "china", "mainland china": "china",
    "germany": "germany", "de": "germany", "德国": "germany", "ドイツ": "germany",
    "korea": "korea", "south korea": "korea", "kr": "korea", "韩国": "korea", "한국": "korea",
    "singapore": "singapore", "sg": "singapore", "新加坡": "singapore", "シンガポール": "singapore",
    "canada": "canada", "ca": "canada", "加拿大": "canada", "カナダ": "canada",
    "australia": "australia", "au": "australia", "澳大利亚": "australia",
    "india": "india", "インド": "india", "印度": "india",
    "france": "france", "fr": "france", "法国": "france", "フランス": "france",
    "netherlands": "netherlands", "nl": "netherlands", "荷兰": "netherlands",
    "switzerland": "switzerland", "ch": "switzerland", "瑞士": "switzerland",
    "sweden": "sweden", "se": "sweden", "瑞典": "sweden",
    "denmark": "denmark", "dk": "denmark", "finland": "finland", "fi": "finland",
    "ireland": "ireland", "ie": "ireland", "spain": "spain", "es": "spain",
    "italy": "italy", "brazil": "brazil", "br": "brazil", "mexico": "mexico", "mx": "mexico",
    "remote": "remote", "worldwide": "remote", "global": "remote", "anywhere": "remote",
    "远程": "remote", "全球": "remote",
}


def canonical_country(value) -> str | None:
    """把国家/地区写法归一化为可比较的规范值（US / USA / United States → us）。

    只接受**整体匹配**（或最后一层逗号段、括号内段），绝不做子串匹配 ——
    否则 "US" 会命中 "Belarus"、"IN" 会命中 "Indonesia" 这类误判。
    无法识别时返回 None，由调用方按"地区信息不足"处理，而不是猜。
    """
    if value in (None, ""):
        return None
    s = re.sub(r"\s+", " ", str(value).strip().lower())
    if s in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[s]
    for part in re.split(r"[,，/|()（）]", s):
        p = part.strip()
        if p in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[p]
    return None


# ---------------------------------------------------------------- ID 生成

def slugify(text, max_len: int = 48) -> str:
    """把任意文本转成稳定、可读、schema 合法的 slug 片段。

    保留 ASCII 字母数字与 CJK（中日韩）字符——这类机会名很常见，直接丢弃会让
    中文/日文机会的 ID 变成空串。其余字符（空格、标点、emoji）折叠为单个连字符。
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text)).lower()
    s = SLUG_KEEP.sub("-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:max_len].strip("-")


#: 机构名后缀（比较与 ID 生成前统一剥离，避免 "Sony Inc." ≠ "Sony"）
ORG_SUFFIXES = (
    "incorporated", "inc", "limited", "ltd", "llc", "plc", "gmbh", "ag", "bv", "nv",
    "sa", "srl", "spa", "pty", "co", "corp", "corporation", "company", "holdings",
    "group", "株式会社", "有限会社", "合同会社", "有限公司", "股份有限公司", "集团",
)


def norm_org(text) -> str:
    """机构名归一化：转 slug、去后缀。dedupe 与 ID 生成共用同一实现。"""
    s = slugify(text, 64).replace("-", " ")
    return " ".join(t for t in s.split() if t not in ORG_SUFFIXES).strip()


#: 标题里对"身份"无贡献、只影响阅读的通用词（用于 ID 与去重比较）
_ID_NOISE = (
    "internship", "internships", "intern", "program", "programme", "position",
    "opening", "openings", "recruitment", "the", "and", "for", "of", "a", "an",
    "招募", "招聘", "计划", "项目", "实习", "選考", "採用", "募集", "インターン",
)

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def extract_years(text) -> list[str]:
    if not text:
        return []
    return sorted(set(m.group(0) for m in _YEAR_RE.finditer(str(text))))


def core_title(text, min_tokens: int = 2) -> str:
    """标题的"核心词"：去掉年份与通用项目词，用于 ID 与相似度比较。

    过度剥离保护：如果去掉通用词后剩余 token 少于 `min_tokens`（例如
    "2027 Summer Internship Program" 会只剩 "summer"），说明剥离已经丢掉信息，
    此时退回"只去年份"的保守版本，避免相似度比较失真。
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text)).lower()
    s = re.sub(r"\d{4}\s*年", " ", s)
    s = _YEAR_RE.sub(" ", s)
    s = re.sub(r"[（(][^）)]{0,14}[）)]", " ", s)
    s = SLUG_KEEP.sub(" ", s)
    tokens = [t for t in s.split() if t]
    filtered = [t for t in tokens if t not in _ID_NOISE]
    if len(filtered) < min_tokens and len(tokens) >= min_tokens:
        filtered = tokens
    return " ".join(filtered).strip()


#: 周期(cycle)标记：季节词
SEASON_TOKENS = {
    "spring": "spring", "summer": "summer", "autumn": "autumn", "fall": "autumn",
    "winter": "winter", "春": "spring", "夏": "summer", "秋": "autumn", "冬": "winter",
    "暑期": "summer", "寒假": "winter", "サマー": "summer", "ウィンター": "winter",
    "summerofcode": "summer",
}


def cycle_parts(rec: dict) -> tuple[tuple[str, ...], str | None]:
    """返回 (年份元组, 季节标识)。只使用**显式**信息，信息不足则返回空。"""
    if not isinstance(rec, dict):
        return (), None
    title = str(rec.get("title") or "")
    years = tuple(extract_years(title))
    if not years:
        for f in ("event_start", "event_end", "application_open", "deadline"):
            found = extract_years(rec.get(f))
            if found:
                years = tuple(found)
                break
    if not years:
        years = tuple(extract_years(rec.get("graduation_window")))
    norm = title.lower().replace(" ", "")
    seasons = sorted({v for k, v in SEASON_TOKENS.items() if k in norm})
    return years, (seasons[0] if seasons else None)


def cycles_conflict(a: dict, b: dict) -> tuple[bool, str]:
    """判断两条记录的申请周期是否**明确**冲突。

    只有证据足够时才判冲突，避免把"Summer 2027"和"2027"这种同一周期误判为冲突：
      * 主年份不同 → 冲突
      * 双方都写了季节且季节不同 → 冲突
    其余情况（任一方缺失年份/季节）一律不判冲突。
    """
    ya, sa = cycle_parts(a)
    yb, sb = cycle_parts(b)
    if ya and yb and ya[0] != yb[0]:
        return True, "year_differs"
    if sa and sb and sa != sb:
        return True, "season_differs"
    return False, ""


def extract_cycle(rec: dict) -> str | None:
    """周期标识（用于展示与 ID），形如 `2027`、`2027-summer`、`2026-2028`。"""
    years, season = cycle_parts(rec)
    if not years:
        return None
    base = years[0] if len(years) == 1 else "-".join([years[0], years[-1]])
    return f"{base}-{season}" if season else base


def derive_id(rec: dict) -> str:
    """生成稳定的 Opportunity ID。

    契约：
      * 同一机会 + 同一周期 → 同一 ID
      * 同一项目 + 不同年份/周期 → 不同 ID（周期信息写进 ID）

    形如 `sony-embedded-systems-2027`；信息不足时退化为 `org-title`，
    完全无法生成可读片段时使用确定性哈希兜底（不含随机成分）。
    """
    if not isinstance(rec, dict):
        return "unknown-opportunity"
    org = "-".join(norm_org(rec.get("organization")).split())[:32]
    core = core_title(rec.get("title")) or slugify(rec.get("title"), 32)
    core = "-".join(core.split())[:40].strip("-")
    years = extract_years(rec.get("title")) or extract_years(rec.get("deadline")) or extract_years(rec.get("event_start"))
    year_part = years[0] if years else ""

    parts = [p for p in (org, core) if p]
    # 标题里已经含机构名时不要再拼一次（避免 Tsinghua-清华大学-... 这类重复）
    if org and core and org.replace("-", "") in core.replace("-", ""):
        parts = [core]
    if year_part and year_part not in core:
        parts.append(year_part)
    oid = "-".join(parts).strip("-")
    oid = re.sub(r"-{2,}", "-", oid)
    if not oid:
        digest = hashlib.sha1(
            unicodedata.normalize("NFKC", f"{rec.get('organization')}|{rec.get('title')}").encode("utf-8")
        ).hexdigest()[:8]
        oid = f"opportunity-{digest}"
    return oid[:96].strip("-")


def ensure_id(rec: dict) -> dict:
    """若记录缺少 id 或 id 非法，就地补一个合规 ID，返回该记录。"""
    oid = rec.get("id")
    if not isinstance(oid, str) or not ID_RE.match(oid or ""):
        rec["id"] = derive_id(rec)
    return rec


# ---------------------------------------------------------------- 轻量 contract 校验

def _date_like(value) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return bool(re.match(r"^\d{4}-\d{2}(-\d{2})?([T ].*)?$", value.strip()))


def validate_opportunity(rec) -> list[str]:
    """最小必要的 contract 校验（stdlib）。返回错误信息列表，空列表表示通过。

    这不是完整 JSON Schema 校验（完整校验在 dev/test 环境用 jsonschema），
    而是运行时用来及早发现结构错误、并防止跨脚本字段漂移的轻量契约。
    """
    errs: list[str] = []
    if not isinstance(rec, dict):
        return ["记录不是 JSON 对象"]
    for f in ("id", "title", "organization", "primary_category"):
        if rec.get(f) in (None, ""):
            errs.append(f"缺少必填字段 {f}")
    oid = rec.get("id")
    if isinstance(oid, str) and oid and not ID_RE.match(oid):
        errs.append(f"id 不符合命名契约（小写字母数字/CJK + . _ -）：{oid!r}")
    pc = rec.get("primary_category")
    if pc is not None and pc not in CATEGORIES:
        errs.append(f"primary_category 非法：{pc!r}")
    for c in (rec.get("secondary_categories") or []):
        if c not in CATEGORIES:
            errs.append(f"secondary_categories 含非法值：{c!r}")
    if rec.get("trust_tier") not in TRUST_TIERS + (None,):
        errs.append(f"trust_tier 非法：{rec.get('trust_tier')!r}")
    if rec.get("verification_status") not in VERIFICATION_STATUSES + (None,):
        errs.append(f"verification_status 非法：{rec.get('verification_status')!r}")
    ev = rec.get("eligibility")
    if isinstance(ev, dict) and ev.get("verdict") not in ELIGIBILITY_VERDICTS + (None,):
        errs.append(f"eligibility.verdict 非法：{ev.get('verdict')!r}")
    for f in ("deadline", "application_open", "event_start", "event_end"):
        if not _date_like(rec.get(f)):
            errs.append(f"{f} 不是 YYYY-MM 或 YYYY-MM-DD：{rec.get(f)!r}")
    for f in EVIDENCE_FIELDS:
        e = (rec.get("evidence") or {}).get(f)
        if isinstance(e, dict) and e.get("status") not in EVIDENCE_STATUSES:
            errs.append(f"evidence.{f}.status 非法：{e.get('status')!r}")
    return errs


def validate_profile(prof) -> list[str]:
    errs: list[str] = []
    if not isinstance(prof, dict):
        return ["画像不是 JSON 对象"]
    ed = prof.get("education")
    if isinstance(ed, dict):
        degree = ed.get("degree")
        if isinstance(degree, list) and len(degree) > 1:
            errs.append("education.degree 应为单一值或单元素数组")
    for g in (prof.get("goals") or []):
        if isinstance(g, dict) and g.get("type") not in GOAL_TYPES:
            errs.append(f"goals[].type 非法：{g.get('type')!r}")
    return errs


def load_records(path) -> list[dict]:
    """读取机会记录数组：支持数组 / {opportunities|records|items} / dedupe 的 clusters[].merged。"""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for k in ("opportunities", "records", "items"):
            if isinstance(data.get(k), list):
                return [r for r in data[k] if isinstance(r, dict)]
        if isinstance(data.get("clusters"), list):
            out = []
            for c in data["clusters"]:
                if isinstance(c, dict) and isinstance(c.get("merged"), dict):
                    out.append(c["merged"])
            return out
    raise SystemExit(f"未在 {path} 中找到机会数组（支持 opportunities / clusters[].merged）")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="OpportunityRadar 共享工具与轻量 contract 校验")
    ap.add_argument("--validate", help="校验一个机会 JSON 文件（数组或单条）")
    ap.add_argument("--id", help="按标题生成 ID")
    ap.add_argument("--org", help="配合 --id 使用的机构名")
    ap.add_argument("--url", help="打印 URL 的规范形式")
    ap.add_argument("--cycle", help="打印 title 对应的周期标识（需配合 --id）")
    args = ap.parse_args(argv)

    if args.url:
        print(canonical_url(args.url) or "")
        return 0
    if args.id:
        rec = {"title": args.id, "organization": args.org}
        print(derive_id(rec))
        if args.cycle:
            print(extract_cycle(rec) or "")
        return 0
    if args.validate:
        with open(args.validate, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("opportunities"), list):
            recs = data["opportunities"]
        elif isinstance(data, list):
            recs = data
        else:
            recs = [data]
        total = 0
        for i, rec in enumerate(recs):
            errs = validate_opportunity(rec)
            if errs:
                total += len(errs)
                label = rec.get("id") if isinstance(rec, dict) else f"#{i}"
                for e in errs:
                    print(f"[{label}] {e}")
        print(f"checked={len(recs)} errors={total}")
        return 1 if total else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
