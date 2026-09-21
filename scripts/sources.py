#!/usr/bin/env python3
"""sources.py - 最小版 Source Intelligence（V3 P1，真实失败驱动）。

只解决三个已确认的召回缺口：research bridge / language bridge / OSS foundation entry。
**不是**全球来源数据库，**不是**白名单搜索器。

链路：
    Gap Type → Bridge Intent → Source Family → Targeted Query → general search fallback

纪律（硬要求）：
  * registry 里没有的来源 ≠ 不搜索它；未知来源照常走 general discovery
  * 候选来源不会因为"来自 known source"而变可信 —— 后续仍走同一套 gate
  * 用户阶段参与 query 规划（undergrad 与 working professional 的 research Bridge 不同）
  * `historical_yield` 只用于"相同预算下先扫出过成果的来源"，不能用来停止搜索其他来源
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- Source families
#: 每个 family：适用的 gap 类型、页面类型、query intent 模板、领域/地区是否敏感
SOURCE_FAMILIES = {
    # ---- Research Bridge ----
    "university_lab": {
        "gap_types": ("research", "network", "experience"),
        "page_types": ("lab homepage", "lab openings", "faculty research page"),
        "intents": ("{topic} laboratory open positions students",
                    "{topic} lab visiting student"),
        "canonical_hint": "大学/机构域名（.edu/.ac.jp/.ac.uk/.edu.cn）+ 实验室页面",
        "domain_sensitive": True,
    },
    "professor_page": {
        "gap_types": ("network", "research"),
        "page_types": ("faculty profile", "advisor recruiting note"),
        "intents": ("professor {topic} recruiting students",),
        "canonical_hint": "教授个人主页 / 院系教員紹介",
        "domain_sensitive": True,
    },
    "research_seminar": {
        "gap_types": ("network", "research"),
        "page_types": ("open seminar", "lab tour", "workshop"),
        "intents": ("{topic} open seminar registration students",),
        "canonical_hint": "院系/实验室公告页",
        "domain_sensitive": True,
    },
    "summer_research": {
        "gap_types": ("research", "experience"),
        "page_types": ("summer programme", "research internship", "visiting student"),
        "intents": ("summer research programme {topic} international students",
                    "{topic} research internship visiting student programme"),
        "canonical_hint": "项目官方页（大学/研究所）",
        "domain_sensitive": True,
    },
    "research_institute": {
        "gap_types": ("research", "network"),
        "page_types": ("institute programme", "internship", "visiting researcher"),
        "intents": ("{topic} research institute internship programme",),
        "canonical_hint": "研究所官方页",
        "domain_sensitive": True,
    },
    "academic_society": {
        "gap_types": ("network", "public_reputation", "research"),
        "page_types": ("society programme", "student chapter", "committee"),
        "intents": ("{topic} professional society student member programme",),
        "canonical_hint": "学会官方页",
        "domain_sensitive": False,
    },
    "graduate_school": {
        "gap_types": ("education", "language", "research"),
        "page_types": ("admissions", "part-time programme", "research student system"),
        "intents": (" graduate school part-time programme admissions international",
                    " graduate school entrance requirements"),
        "canonical_hint": "大学院官方招生页",
        "domain_sensitive": True,
    },
    "research_funding_body": {
        "gap_types": ("research", "portfolio"),
        "page_types": ("grant", "fellowship", "travel grant"),
        "intents": ("{topic} research grant students apply",),
        "canonical_hint": "资助机构官方页",
        "domain_sensitive": True,
    },
    # ---- Language Bridge ----
    "official_exam_body": {
        "gap_types": ("language",),
        "page_types": ("test dates", "sample questions", "official mock"),
        "intents": ("{exam} official test dates registration",),
        "canonical_hint": "考试主办方官方页",
        "domain_sensitive": True,
    },
    "university_language_center": {
        "gap_types": ("language", "education"),
        "page_types": ("language centre course", "short programme"),
        "intents": ("university language centre {lang} short programme",),
        "canonical_hint": "大学语言中心官方页",
        "domain_sensitive": True,
    },
    "government_cultural_body": {
        "gap_types": ("language", "network"),
        "page_types": ("cultural institute course", "exchange programme"),
        "intents": ("{country} cultural institute {lang} course programme",),
        "canonical_hint": "官方文化机构页",
        "domain_sensitive": True,
    },
    "language_exchange_program": {
        "gap_types": ("language", "network"),
        "page_types": ("exchange", "language partner programme"),
        "intents": ("{lang} language exchange programme university",),
        "canonical_hint": "大学/机构项目页",
        "domain_sensitive": True,
    },
    "speech_contest": {
        "gap_types": ("language", "public_reputation", "portfolio"),
        "page_types": ("speech contest", "translation contest"),
        "intents": ("{lang} speech contest students apply",),
        "canonical_hint": "主办方官方页",
        "domain_sensitive": True,
    },
    # ---- Open-source Foundation / Contributor Entry ----
    "foundation": {
        "gap_types": ("portfolio", "public_reputation", "leadership"),
        "page_types": ("foundation programmes", "community pages"),
        "intents": ("{ecosystem} foundation contributor programme students",
                    "{ecosystem} foundation mentorship programme"),
        "canonical_hint": "基金会官方页",
        "domain_sensitive": False,
    },
    "mentorship_program": {
        "gap_types": ("portfolio", "network", "experience"),
        "page_types": ("mentorship page", "application round"),
        "intents": ("{ecosystem} mentorship programme apply",),
        "canonical_hint": "项目官方页",
        "domain_sensitive": False,
    },
    "working_group": {
        "gap_types": ("public_reputation", "leadership", "network"),
        "page_types": ("working group", "SIG", "technical committee"),
        "intents": ("{ecosystem} working group SIG join", "{ecosystem} technical committee participate"),
        "canonical_hint": "基金会/项目官方页",
        "domain_sensitive": False,
    },
    "contributor_guide": {
        "gap_types": ("portfolio", "experience"),
        "page_types": ("contributor guide", "good first issue", "contributor ladder"),
        "intents": ("{ecosystem} contributor guide good first issue",),
        "canonical_hint": "项目仓库/官方文档页",
        "domain_sensitive": False,
    },
    "community_event": {
        "gap_types": ("network", "public_reputation"),
        "page_types": ("community calendar", "meetup", "conference CFP"),
        "intents": ("{ecosystem} community event CFP open",),
        "canonical_hint": "社区活动官方页",
        "domain_sensitive": False,
    },
    "maintainer_program": {
        "gap_types": ("leadership", "public_reputation"),
        "page_types": ("maintainer pathway", "governance"),
        "intents": ("{ecosystem} maintainer pathway governance",),
        "canonical_hint": "项目治理页面",
        "domain_sensitive": False,
    },
}

#: Gap Type → Bridge Intent（不要 Gap → query 字符串直连）
GAP_TO_BRIDGE_INTENT = {
    "research": "hands-on research evidence",
    "network": "professor / community contact",
    "language": "certified language evidence",
    "portfolio": "public, verifiable artefact",
    "public_reputation": "visible public impact",
    "leadership": "visible ownership",
    "management": "people / programme ownership",
    "experience": "hands-on experience",
    "education": "formal admission readiness",
    "credential": "recognised credential",
    "location_visa": "location / eligibility path",
}

#: Bridge Intent → Source Family（按缺口细分，不用同一个 query 打天下）
INTENT_TO_FAMILIES = {
    "hands-on research evidence": ("summer_research", "research_institute", "university_lab",
                                   "research_funding_body"),
    "professor / community contact": ("research_seminar", "professor_page", "academic_society",
                                      "community_event"),
    "certified language evidence": ("official_exam_body", "university_language_center",
                                    "speech_contest"),
    "visible public impact": ("community_event", "maintainer_program", "working_group",
                              "speech_contest"),
    "visible ownership": ("working_group", "maintainer_program", "foundation"),
    "public, verifiable artefact": ("contributor_guide", "mentorship_program", "foundation",
                                    "speech_contest"),
    "hands-on experience": ("mentorship_program", "summer_research", "contributor_guide"),
    "formal admission readiness": ("university_language_center", "graduate_school"),
    "people / programme ownership": ("foundation", "working_group", "mentorship_program"),
}

#: 阶段敏感的 query 变体（不能补完职场支持后又退回学生视角）
STAGE_INTENT_OVERRIDES = {
    "working": {
        "hands-on research evidence": ("{topic} part-time research programme working professionals",
                                       "{topic} industry-academia collaborative project"),
        "professor / community contact": ("{topic} open seminar working professionals",),
        "certified language evidence": ("{lang} evening course university language centre",),
    },
    "undergraduate": {
        "hands-on research evidence": ("{topic} summer research programme undergraduate",
                                       "{topic} undergraduate research internship"),
        "professor / community contact": ("{topic} lab tour undergraduate students",
                                          "{topic} undergraduate seminar open"),
    },
    "founder": {
        "visible ownership": ("{ecosystem} working group join", "{ecosystem} governance participate"),
    },
}

# ---------------------------------------------------------------- 页面新鲜度（≠ 机会新鲜度）
#: source_freshness 回答"这个页面/公告是不是当前信息"；
#: opportunity freshness 回答"这个机会现在是否开放"。**两者语义不同，不要混用。**
SOURCE_FRESHNESS = ("current", "likely_current", "stale", "historical", "unknown")

STALE_MARKERS = ("archive", "archived", "previous years", "past programme", "past program",
                 "過去の", "閉講", "終了しました", "no longer offered", "見送り",
                 "had been", "was held")
#: 表示"当前/下一周期"的措辞（**不要写死年份**；年份判断用 today.year 动态完成）
CURRENT_MARKERS = ("accepting applications", "now open", "currently open", "受付中",
                   "募集中", "応募受付", "next cycle", "次回", "next year")


def _years(text):
    import re
    return [int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", str(text or ""))]


def source_freshness(page, today=None) -> dict:
    """页面是否是"当前信息"。`page` 可以是 opportunity dict 或字符串。

    判据（任一命中即给出结论，保守优先）：
      1. archive / 已结束 措辞 → historical
      2. 标题 / URL / 摘要里出现的年份：最晚年份 < 今年 → historical / stale
      3. 最晚年份 == 今年 或 出现"下次/次年" → current / likely_current
      4. 无法判断 → unknown
    """
    import datetime as _dt
    today = today or _dt.date.today()
    if isinstance(page, dict):
        text = " ".join(str(page.get(k) or "") for k in
                        ("title", "summary", "url", "official_url", "notes"))
        updated = page.get("last_updated") or page.get("updated_at")
    else:
        text, updated = str(page or ""), None
    low = text.lower()
    years = _years(text)
    max_year = max(years) if years else None
    if any(m in low for m in STALE_MARKERS):
        return {"source_freshness": "historical", "years": years,
                "signal": "页面含已归档/已结束措辞"}
    if updated:
        try:
            age = (today - _dt.date.fromisoformat(str(updated)[:10])).days
            if age <= 365:
                return {"source_freshness": "current", "years": years,
                        "signal": f"页面标注最近更新 {updated}"}
            return {"source_freshness": "stale", "years": years,
                    "signal": f"最后更新在 {age} 天前"}
        except (TypeError, ValueError):
            pass
    if max_year is not None and max_year < today.year:
        return {"source_freshness": "historical", "years": years,
                "signal": f"页面最晚年份 {max_year} 早于今年 {today.year}"}
    next_year = str(today.year + 1)
    if max_year is not None and max_year >= today.year:
        if max_year > today.year or next_year in low or any(m in low for m in CURRENT_MARKERS):
            return {"source_freshness": "current", "years": years,
                    "signal": f"页面提到 {max_year} 或当前/下一周期"}
        return {"source_freshness": "likely_current", "years": years,
                "signal": f"页面年份为 {max_year}（今年）"}
    return {"source_freshness": "unknown", "years": years, "signal": "无法判断页面时效"}


#: 失败类型（沿用 process / fact / infrastructure 三分类）—— 不要全塞进 worth_verifying
SOURCE_FAILURE_TYPES = {
    "source_not_found": "process",
    "source_found_current": "fact",
    "source_found_not_current": "fact",
    "source_found_no_opportunity": "fact",
    "source_found_not_applicable": "fact",
    "page_not_verifiable": "infrastructure",
    "js_rendered": "infrastructure",
    "blocked": "infrastructure",
}

#: 候选来源（用于 provenance 统计，不是白名单）
CANDIDATE_ORIGINS = ("known_source", "source_family_query", "general_search", "adjacent_discovery")



#: 阶段适配度（**只影响搜索优先级与预算**，不决定用户有没有资格）
#:   high  = 该阶段的主力来源
#:   medium= 视情况（depends）
#:   low   = 通常不值得为该阶段花预算
#:   never = 默认跳过（除非官方明确接受该阶段 —— 由 eligibility 层覆盖）
STAGE_FIT = {
    # family: {stage: high|medium|low|never}
    "summer_research":       {"undergraduate": "high", "unknown": "medium",
                              "working": "low", "founder": "low"},
    "university_lab":        {"undergraduate": "high", "working": "medium", "unknown": "medium"},
    "professor_page":        {"undergraduate": "high", "working": "medium", "unknown": "medium"},
    "research_seminar":      {"undergraduate": "medium", "working": "high", "unknown": "medium"},
    "research_institute":    {"undergraduate": "medium", "working": "high", "unknown": "medium"},
    "graduate_school":       {"undergraduate": "medium", "working": "high", "unknown": "medium"},
    "academic_society":      {"undergraduate": "medium", "working": "high", "unknown": "medium"},
    "research_funding_body": {"undergraduate": "medium", "working": "medium", "unknown": "medium"},
    "official_exam_body":    {"undergraduate": "high", "working": "high", "unknown": "high"},
    "university_language_center": {"undergraduate": "high", "working": "high", "unknown": "medium"},
    "government_cultural_body":   {"undergraduate": "medium", "working": "high", "unknown": "medium"},
    "language_exchange_program":  {"undergraduate": "high", "working": "medium", "unknown": "medium"},
    "speech_contest":        {"undergraduate": "medium", "working": "medium", "unknown": "medium"},
    "scholarship_language_program": {"undergraduate": "high", "working": "medium", "unknown": "medium"},
    "foundation":            {"undergraduate": "high", "working": "high", "founder": "high",
                              "unknown": "medium"},
    "mentorship_program":    {"undergraduate": "high", "working": "high", "unknown": "high"},
    "working_group":         {"undergraduate": "medium", "working": "high", "founder": "high",
                              "unknown": "medium"},
    "contributor_guide":     {"undergraduate": "high", "working": "high", "unknown": "high"},
    "community_event":       {"undergraduate": "high", "working": "high", "unknown": "high"},
    "maintainer_program":    {"undergraduate": "medium", "working": "high", "founder": "high",
                              "unknown": "medium"},
    "project_repository":    {"undergraduate": "high", "working": "high", "unknown": "high"},
    "bounty_program":        {"undergraduate": "medium", "working": "high", "unknown": "medium"},
}

STAGE_FIT_WEIGHT = {"high": 3, "medium": 2, "low": 1, "never": 0}


def family_stage_fit(family, stage) -> str:
    return STAGE_FIT.get(family, {}).get(stage or "unknown", "medium")


def applicabity_note(family, stage) -> str:
    """给用户/日志看的解释：**这是搜索优先级，不是资格判定**。"""
    fit = family_stage_fit(family, stage)
    return {"high": "该阶段的主力来源", "medium": "视情况可搜", "low": "通常优先级低",
            "never": "默认跳过（若官方明确接受该阶段仍可命中）"}[fit]

def bridge_intent_for(gap) -> str:
    if isinstance(gap, str):
        return GAP_TO_BRIDGE_INTENT.get("skill", "hands-on experience")
    return GAP_TO_BRIDGE_INTENT.get(gap.get("type") or "", "hands-on experience")


def families_for_gap(gap) -> list:
    """Gap → Bridge Intent → Source Families（按 gap 类型细分）。"""
    return list(INTENT_TO_FAMILIES.get(bridge_intent_for(gap), ()))


#: family → 查询里应出现的领域词（用于判断一条 query 真正属于哪个 family）
FAMILY_QUERY_MARKERS = {
    # 注意：不要收录过于泛化的 "research programme" —— 会把在职者的 part-time 查询误匹配进来
    "summer_research": ("summer research", "undergraduate research", "research internship",
                        "visiting student", "サマー"),
    "university_lab": ("laboratory", "lab ", "研究室", "实验室", "课题组"),
    "professor_page": ("professor", "教授", "faculty", "招生"),
    "research_seminar": ("seminar", "見学", "open seminar", "workshop", "开放讲座"),
    "research_institute": ("institute", "研究所", "research institute"),
    "graduate_school": ("graduate school", "大学院", "pt programme", "part-time programme"),
    "academic_society": ("society", "学会", "committee", "学生会员"),
    "research_funding_body": ("grant", "fellowship", "助成", "stipend", "资助", "科研"),
    "official_exam_body": ("test dates", "registration", "模擬試験", "exam", "考试"),
    "university_language_center": ("language centre", "language center", "語学", "语言中心"),
    "government_cultural_body": ("cultural institute", "文化機構", "文化", "文化机构"),
    "language_exchange_program": ("language exchange", "言語交換", "exchange programme", "语言交换"),
    "speech_contest": ("speech contest", "speech", "翻訳", "スピーチ", "演讲比赛"),
    "scholarship_language_program": ("scholarship", "奖学金", "給付"),
    "foundation": ("foundation", "基金会"),
    "mentorship_program": ("mentorship", "mentor", "メンター", "导师"),
    "working_group": ("working group", "sig ", "committee", "ワーキング"),
    "contributor_guide": ("contributor guide", "good first issue", "contribute", "コントリビュート", "贡献指南"),
    "community_event": ("community event", "meetup", "勉強会", "cfp", "社区 活动", "社区活动"),
    "maintainer_program": ("maintainer", "governance", "メンテナー", "维护者"),
    "project_repository": ("repository", "contributors wanted", "repo"),
    "bounty_program": ("bounty", "賞金"),
}


#: 非英语 query 模板：只在**目标地区真的需要该语言**时才发出。
#: 语言由 locales.resolve_locales() 在运行时解析，不在这里推断、也不写死地区。
LOCALE_INTENTS = {
    # ---- Research ----
    "university_lab": {
        "ja": ("研究室 学生 募集 {topic}",),
        "zh": ("{topic} 实验室 学生 招募", "{topic} 课题组 招 学生"),
    },
    "professor_page": {
        "ja": ("{topic} 教授 研究室 見学 学生",),
        "zh": ("{topic} 教授 招生 学生 联系",),
    },
    "research_seminar": {
        "ja": ("{topic} 研究室 オープン 見学会 社会人",),
        "zh": ("{topic} 开放讲座 报名 学生",),
    },
    "research_institute": {
        "ja": ("{topic} 研究所 インターン 社会人",),
        "zh": ("{topic} 研究所 实习 招募 学生",),
    },
    "academic_society": {
        "ja": ("{topic} 学会 学生会員 参加",),
        "zh": ("{topic} 学会 学生会员 加入",),
    },
    "research_funding_body": {
        "ja": ("{topic} 研究助成 学生 公募",),
        "zh": ("{topic} 科研 资助 学生 申请",),
    },
    # ---- Language ----
    "official_exam_body": {
        "ja": ("{exam} 公式 模擬試験",),
        "zh": ("{exam} 官方 考试 时间 报名",),
    },
    "university_language_center": {
        "ja": ("大学 語学センター {lang} 短期 プログラム",),
        "zh": ("大学 语言中心 {lang} 短期 课程",),
    },
    "government_cultural_body": {
        "ja": ("{country} 文化機構 {lang} 講座 プログラム",),
        "zh": ("{country} 文化机构 {lang} 课程 项目",),
    },
    "language_exchange_program": {
        "ja": ("{lang} 言語交換 プログラム 大学",),
        "zh": ("{lang} 语言交换 项目 大学",),
    },
    "speech_contest": {
        "ja": ("{lang} スピーチコンテスト 学生 応募",),
        "zh": ("{lang} 演讲比赛 学生 报名",),
    },
    # ---- Open source ----
    "mentorship_program": {
        "ja": ("{ecosystem} メンターシップ 応募",),
        "zh": ("{ecosystem} 导师 计划 申请 学生",),
    },
    "contributor_guide": {
        "ja": ("{ecosystem} コントリビュート 方法",),
        "zh": ("{ecosystem} 贡献指南 新手 任务",),
    },
    "community_event": {
        "ja": ("{ecosystem} コミュニティ 勉強会 登壇",),
        "zh": ("{ecosystem} 社区 活动 报名 演讲",),
    },
    "maintainer_program": {
        "ja": ("{ecosystem} メンテナー なるには",),
        "zh": ("{ecosystem} 维护者 路径 治理",),
    },
}

#: 阶段 × 意图 的语言变体
STAGE_INTENT_LOCALES = {
    "working": {
        "hands-on research evidence": {
            "ja": ("{topic} 社会人 研究 プログラム",),
            "zh": ("{topic} 在职 研究 项目 参与",),
        },
        "professor / community contact": {
            "ja": ("{topic} 研究室 見学会 社会人 参加",),
            "zh": ("{topic} 开放讲座 在职 参加",),
        },
        "certified language evidence": {
            "ja": ("{lang} 社会人 講座 大学",),
            "zh": ("{lang} 在职 语言 课程 大学",),
        },
    },
}

#: locale 代码 → 模板语言（未知 locale 一律按 en 处理）
LOCALE_TEMPLATE_LANG = {"zh-CN": "zh", "zh-TW": "zh", "zh": "zh", "ja-JP": "ja", "ja": "ja",
                        "en": "en", "en-US": "en", "en-GB": "en"}


def query_languages(profile=None, request_text: str = "") -> list:
    """本次运行应该发哪些语言的 query（顺序 = 优先级，由 locales 解析决定）。

    未收录地区 / 无法解析时回落到 ["en"]（语言中立的底座）。
    """
    codes = []
    try:
        import locales as L
        loc = L.resolve_locales(profile or {}, request_text or "")
        codes = list(loc.get("primary_locales") or []) + list(loc.get("optional_locales") or [])
    except Exception:
        codes = []
    langs = []
    for c in codes:
        lg = LOCALE_TEMPLATE_LANG.get(str(c))
        if lg and lg not in langs:
            langs.append(lg)
    if "en" not in langs:                     # en 是语言中立底座，始终保留
        langs.append("en")
    return langs


def _lang_variants(family, intent, stage, langs) -> list:
    """某 family/意图在当前语言下应该发出的非英语模板。"""
    out = []
    for lg in langs:
        if lg == "en":
            continue
        for tpl in (LOCALE_INTENTS.get(family) or {}).get(lg, ()):
            out.append(tpl)
        for tpl in ((STAGE_INTENT_LOCALES.get(stage) or {}).get(intent) or {}).get(lg, ()):
            out.append(tpl)
    return out


def _family_for_query(query, candidates) -> str | None:
    """一条 query 真正属于哪个 family；匹配不到就返回 None（不要为了指标好看强挂）。"""
    low = str(query or "").lower()
    for fam in candidates or ():
        for marker in FAMILY_QUERY_MARKERS.get(fam, ()):
            if marker in low:
                return fam
    return None


def stage_of(profile) -> str:
    """用于 query 规划的阶段（决定 Bridge 的形态，不只是文案）。

    顺序很重要：**在职者优先**（在职读研的人要的是"在职友好"的 Bridge，
    不能被 career_stage=graduate_student 拉回学生视角）。
    """
    stages = profile.get("life_stage") or []
    if isinstance(stages, str):
        stages = [stages]
    if "working" in stages or "self_employed" in stages:
        return "working"
    if "founder" in stages:
        return "founder"
    career = profile.get("career_stage") or []
    if isinstance(career, str):
        career = [career]
    if "undergraduate" in career or "pre_college" in career:
        return "undergraduate"
    if "student" in stages:
        return "undergraduate"
    return "unknown"


def plan_queries(gap, profile=None, topic=None, region=None, limit=6,
                 request_text="", languages=None) -> list:
    """Gap → 具体 query（带来源 family / provenance / 阶段变体 / 语言）。

    **语言由运行时 locale 决定**：不在模板里写死任何非英语语言。
    """
    profile = profile or {}
    topic = topic or (gap.get("name") if isinstance(gap, dict) else str(gap)) or "opportunity"
    intent = bridge_intent_for(gap)
    fams = families_for_gap(gap)
    stage = stage_of(profile)
    langs = list(languages) if languages else query_languages(profile, request_text)
    lang = ((profile.get("constraints") or {}).get("language_constraint")
            or ("Japanese" if ("japan" in str(region or "").lower() or "日本" in str(topic))
                else "language"))
    out = []
    selected, downweighted, skipped = [], [], []
    # family 按阶段适配度排序（high 先搜），适配度为 never 的默认跳过
    ordered = sorted(fams, key=lambda f: -STAGE_FIT_WEIGHT.get(family_stage_fit(f, stage), 2))
    for fam in fams:
        fit = family_stage_fit(fam, stage)
        if fit == "never":
            skipped.append({"family": fam, "stage": stage, "reason": "stage_inapplicable"})
        elif fit == "low":
            downweighted.append({"family": fam, "stage": stage, "reason": "low_stage_fit"})
        else:
            selected.append({"family": fam, "stage": stage, "fit": fit})
    def _fmt(tpl):
        return tpl.format(topic=topic, lang=lang, exam=lang, ecosystem=topic,
                          country=region or "")

    def _emit(q, fam, lang=None):
        # 语言来自模板表（已知），不靠字符启发式猜 —— 纯汉字日语无法与中文区分
        out.append({"query": q, "family": fam if fam else _family_for_query(q, fams),
                    "bridge_intent": intent, "origin": "source_family_query", "stage": stage,
                    "lang": lang or _query_lang(q), "languages": list(langs),
                    "stage_fit": family_stage_fit(fam or "", stage)})

    # 1) 阶段专用 query：语言变体优先（主 locale 先），英文模板兜底 → 目标语言先出
    for lg in langs:
        for tpl in (((STAGE_INTENT_LOCALES.get(stage) or {}).get(intent) or {}).get(lg) or ()):
            _emit(_fmt(tpl), None, lang=lg)
    for tpl in STAGE_INTENT_OVERRIDES.get(stage, {}).get(intent, ()):
        _emit(_fmt(tpl), None)
    # 2) family 模板（按阶段排序；low 的排在后面，预算耗尽自然被截掉）
    for fam in ordered:
        spec = SOURCE_FAMILIES.get(fam)
        if not spec:
            continue
        for tg in langs:                      # 目标语言（zh/ja…）先，英文底座后
            if tg == "en":
                continue
            for tpl in (LOCALE_INTENTS.get(fam) or {}).get(tg, ()):
                _emit(_fmt(tpl), fam, lang=tg)
                if len(out) >= limit:
                    return _finalize(out, limit, selected, downweighted, skipped, stage)
        for tpl in spec["intents"]:
            if _query_lang(tpl) != "en":      # 语言中立的契约：非英语必须走 LOCALE_INTENTS
                continue
            _emit(_fmt(tpl), fam)
            if len(out) >= limit:
                return _finalize(out, limit, selected, downweighted, skipped, stage)
    # 3) 兜底：通用搜索（未知来源照常被发现）
    if not out:
        out.append({"query": f"{topic} opportunity apply", "family": None,
                    "bridge_intent": intent, "origin": "general_search", "stage": stage,
                    "lang": "en"})
    return _finalize(out, limit, selected, downweighted, skipped, stage)


_KANA_RE = re.compile(r"[\u3040-\u30ff]")
_HAN_RE = re.compile(r"[\u3400-\u9fff]")


def _query_lang(text) -> str:
    """模板/query 的语言：kana → ja；纯汉字 → zh；否则 en。"""
    t = str(text or "")
    if _KANA_RE.search(t):
        return "ja"
    if _HAN_RE.search(t):
        return "zh"
    return "en"


def _finalize(out, limit, selected, downweighted, skipped, stage) -> list:
    """补齐 stage_fit / family_selected 等 provenance 字段并截断。"""
    for q in out:
        q.setdefault("lang", _query_lang(q.get("query")))   # 仅兜底；语言变体自带 lang
        q.setdefault("stage_fit", family_stage_fit(q.get("family") or "", stage))
    for q in out[:limit]:
        q["family_selected"] = any(s["family"] == q.get("family") for s in selected)
        q["family_downweighted"] = any(d["family"] == q.get("family") for d in downweighted)
        q["family_skipped"] = any(k["family"] == q.get("family") for k in skipped)
    return out[:limit]


# ---------------------------------------------------------------- Explore 查询镜头（Mode C）
#: Explore 镜头：与 13 类 taxonomy **正交**的表达维度（不是新类别）。
#: 每个镜头给几条**field-neutral** 的 query 模板 —— 空画像时不该从 CS 世界出发。
#: 技术机会仍然可以出现（contribute / build / research 都是镜头之一）；这里只是保证
#: 搜索预算不天然全落在同一类上 —— 不是"反技术偏置"。
EXPLORE_QUERY_LENSES = {
    "build": ("open innovation challenge build something open call anyone worldwide",
              "build challenge make a prototype open call participants"),
    "volunteer": ("remote volunteer program open call anyone can join nonprofit",
                  "online volunteering opportunities open worldwide no experience needed"),
    "creative": ("open call creative writing film art design competition anyone can enter",
                 "open call poetry photography music exhibition prize anyone"),
    "community": ("online mentorship program applications open community for beginners",
                  "community programme open application join members mentor"),
    "research": ("citizen science project join open research volunteers",
                 "open research programme public participation call"),
    "contribute": ("open source contribution beginner friendly project community welcome",
                   "public contribution programme open call anyone"),
    "entrepreneurship": ("student startup competition accelerator applications open worldwide",
                         "innovation challenge open call early stage idea"),
    "cross_domain": ("social impact programme open call sustainability education health",
                     "sustainability climate education programme volunteers open"),
}

#: 默认覆盖几个镜头（§9 要求 ≥3；默认 4，不是"结果必须有 8 类"）
EXPLORE_LENS_LIMIT = 4


def explore_lens_enabled(profile, mode="C") -> dict:
    """严格限定触发：Mode C + 没有明确 goal + career_direction == explore。

    有明确目标的用户（A/B/C/D）**完全不受影响** —— 他们走原来的 category planner。
    """
    prof = profile or {}
    mode = str(mode or "A").upper()
    goals = [g for g in (prof.get("goals") or []) if g]
    if mode != "C":
        return {"enabled": False, "reason": f"模式 {mode} 不启用 explore 镜头"}
    if goals:
        return {"enabled": False, "reason": "用户声明了目标 → 用原来的类别规划"}
    try:
        import gaps as GP
        direction = GP.career_direction(prof)
    except Exception:
        direction = "explore"
    if direction != "explore":
        return {"enabled": False, "reason": f"career_direction={direction} ≠ explore"}
    return {"enabled": True, "reason": "空画像 + 无目标 + explore 方向 → 跨镜头铺开搜索预算",
            "lens_limit": EXPLORE_LENS_LIMIT}


def plan_explore_queries(profile=None, mode="C", lens_limit=None) -> list:
    """跨镜头的 query 批次（至少 3 个镜头）。返回 [{query, lens, origin, source_family}]。

    这是**查询覆盖**，不是结果配额：拿到真实结果后由 explore_coverage 决定最终呈现几个轴，
    不够就不凑。技术类镜头（contribute/build/research）照样在列表里。
    """
    gate = explore_lens_enabled(profile, mode)
    if not gate.get("enabled"):
        return []
    limit = int(lens_limit or gate.get("lens_limit") or EXPLORE_LENS_LIMIT)
    limit = max(3, limit)
    out = []
    for lens, templates in EXPLORE_QUERY_LENSES.items():
        if len(out) >= limit:
            break
        out.append({"query": templates[0], "lens": lens, "origin": "explore_lens",
                    "source_family": None, "stage": None})
    return out


def select_verification_targets(candidates, budget, axis_fn=None, mode="C") -> list:
    """决定**先核实谁**：Explore 模式下优先覆盖不同镜头，而不是按中性 match 取前 N。

    这不改验证门槛（canonical source / freshness / application_status / verified_official
    全部不变），只改"预算花在谁身上"。每条都带 `verification_selected_because`：
    `top_in_axis` / `global_top` / `urgency` / `fallback`。
    """
    cands = [c for c in (candidates or []) if isinstance(c, dict)]
    if not cands or int(budget) <= 0:
        return []

    def key(c):
        return (-float(c.get("match_score") or 0), str(c.get("id") or ""))

    def rec(c, why, axis=None):
        return {"opportunity_id": c.get("id"), "title": c.get("title"),
                "match_score": c.get("match_score"), "axis": axis,
                "days_remaining": c.get("days_remaining"),
                "verification_selected_because": why}

    budget = int(budget)
    out, picked = [], set()

    if str(mode).upper() == "C" and axis_fn is not None:
        groups = {}
        for c in cands:
            for a in (axis_fn(c) or ["(no_axis)"]):
                groups.setdefault(a, []).append(c)
        # 每个镜头的 Top1 先占位；镜头之间按"该镜头最好候选的 match"排序。
        # `(no_axis)` 不占镜头名额 —— 没有轴说明它不属于任何探索维度，交给全局补位。
        groups.pop("(no_axis)", None)
        ordered = sorted(groups, key=lambda a: key(min(groups[a], key=key)))
        for axis in ordered:
            if len(out) >= budget:
                break
            top = min(groups[axis], key=key)
            if id(top) in picked:
                continue
            picked.add(id(top))
            out.append(rec(top, "top_in_axis", axis))

    for c in sorted(cands, key=key):
        if len(out) >= budget:
            break
        if id(c) in picked:
            continue
        picked.add(id(c))
        why = "urgency" if float(c.get("urgency") or 0) > 0 else "global_top"
        if not (str(mode).upper() == "C"):
            why = "global_top"
        out.append(rec(c, why, (axis_fn(c) or [None])[0] if axis_fn else None))
    if not out:
        out.append(rec(min(cands, key=key), "fallback"))
    return out


def registry_coverage(profile=None) -> dict:
    """registry 只是种子：报告它与通用搜索的关系，不制造白名单。"""
    return {"families": len(SOURCE_FAMILIES), "gap_types_covered": sorted(GAP_TO_BRIDGE_INTENT),
            "note": "未收录的来源照常通过 general_search / adjacent_discovery 发现，不会被排除"}


# ---------------------------------------------------------------- local state（可选、轻量）
def yield_state_path(state_dir=".opportunity-radar"):
    return os.path.join(state_dir, "sources.json")


def record_yield(state_dir, source, category=None, region=None, outcome=None,
                 failure_type=None):
    """记录极轻的来源产出（只用于同预算下优先扫历史有效的来源）。"""
    path = yield_state_path(state_dir)
    data = {"entries": {}}
    if os.path.exists(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            data = {"entries": {}}
    from common import SOURCE_STATE_FIELDS as ALLOWED_FIELDS
    key = str(source)
    e = data["entries"].setdefault(key, {f: (key if f == "source" else
                                             category if f == "category" else
                                             region if f == "region" else
                                             0 if f in ("runs", "historical_yield") else None)
                                         for f in ALLOWED_FIELDS})
    e["runs"] += 1
    import datetime as _dt
    today = _dt.date.today().isoformat()
    e["last_checked"] = today
    if outcome == "actionable":
        e["historical_yield"] += 1
        e["last_success"] = today
    if failure_type:
        e["failure_type"] = failure_type
    os.makedirs(state_dir, exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return e


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gap → Bridge Intent → Source Family → queries")
    ap.add_argument("--gap", required=True, help="缺口名或类型，如 research / language / portfolio")
    ap.add_argument("--gap-type", default=None)
    ap.add_argument("--topic", default=None)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--region", default=None)
    args = ap.parse_args(argv)
    profile = json.load(open(args.profile, encoding="utf-8")) if args.profile else {}
    gap = {"name": args.gap, "type": args.gap_type or ("research" if args.gap in
                                                       GAP_TO_BRIDGE_INTENT else "skill")}
    print(json.dumps({"gap": gap, "bridge_intent": bridge_intent_for(gap),
                      "families": families_for_gap(gap),
                      "stage": stage_of(profile),
                      "queries": plan_queries(gap, profile, args.topic, args.region)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
