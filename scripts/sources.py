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
                    "研究室 学生 募集 {topic}", "{topic} lab visiting student"),
        "canonical_hint": "大学/机构域名（.edu/.ac.jp/.ac.uk/.edu.cn）+ 实验室页面",
        "domain_sensitive": True,
    },
    "professor_page": {
        "gap_types": ("network", "research"),
        "page_types": ("faculty profile", "advisor recruiting note"),
        "intents": ("professor {topic} recruiting students",
                    "{topic} 教授 研究室 見学 学生"),
        "canonical_hint": "教授个人主页 / 院系教員紹介",
        "domain_sensitive": True,
    },
    "research_seminar": {
        "gap_types": ("network", "research"),
        "page_types": ("open seminar", "lab tour", "workshop"),
        "intents": ("{topic} open seminar registration students",
                    "{topic} 研究室 オープン 見学会 社会人"),
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
        "intents": ("{topic} research institute internship programme",
                    "{topic} 研究所 インターン 社会人"),
        "canonical_hint": "研究所官方页",
        "domain_sensitive": True,
    },
    "academic_society": {
        "gap_types": ("network", "public_reputation", "research"),
        "page_types": ("society programme", "student chapter", "committee"),
        "intents": ("{topic} professional society student member programme",
                    "{topic} 学会 学生会員 参加"),
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
        "intents": ("{topic} research grant students apply",
                    "{topic} 研究助成 学生 公募"),
        "canonical_hint": "资助机构官方页",
        "domain_sensitive": True,
    },
    # ---- Language Bridge ----
    "official_exam_body": {
        "gap_types": ("language",),
        "page_types": ("test dates", "sample questions", "official mock"),
        "intents": ("{exam} official test dates registration", "{exam} 公式 模擬試験"),
        "canonical_hint": "考试主办方官方页",
        "domain_sensitive": True,
    },
    "university_language_center": {
        "gap_types": ("language", "education"),
        "page_types": ("language centre course", "short programme"),
        "intents": ("university language centre {lang} short programme",
                    "大学 語学センター {lang} 短期 プログラム"),
        "canonical_hint": "大学语言中心官方页",
        "domain_sensitive": True,
    },
    "government_cultural_body": {
        "gap_types": ("language", "network"),
        "page_types": ("cultural institute course", "exchange programme"),
        "intents": ("{country} cultural institute {lang} course programme",
                    "{country} 文化機構 {lang} 講座 プログラム"),
        "canonical_hint": "官方文化机构页",
        "domain_sensitive": True,
    },
    "language_exchange_program": {
        "gap_types": ("language", "network"),
        "page_types": ("exchange", "language partner programme"),
        "intents": ("{lang} language exchange programme university",
                    "{lang} 言語交換 プログラム 大学"),
        "canonical_hint": "大学/机构项目页",
        "domain_sensitive": True,
    },
    "speech_contest": {
        "gap_types": ("language", "public_reputation", "portfolio"),
        "page_types": ("speech contest", "translation contest"),
        "intents": ("{lang} speech contest students apply",
                    "{lang} スピーチコンテスト 学生 応募"),
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
        "intents": ("{ecosystem} mentorship programme apply", "{ecosystem} メンターシップ 応募"),
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
        "intents": ("{ecosystem} contributor guide good first issue", "{ecosystem} コントリビュート 方法"),
        "canonical_hint": "项目仓库/官方文档页",
        "domain_sensitive": False,
    },
    "community_event": {
        "gap_types": ("network", "public_reputation"),
        "page_types": ("community calendar", "meetup", "conference CFP"),
        "intents": ("{ecosystem} community event CFP open", "{ecosystem} コミュニティ 勉強会 登壇"),
        "canonical_hint": "社区活动官方页",
        "domain_sensitive": False,
    },
    "maintainer_program": {
        "gap_types": ("leadership", "public_reputation"),
        "page_types": ("maintainer pathway", "governance"),
        "intents": ("{ecosystem} maintainer pathway governance", "{ecosystem} メンテナー なるには"),
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
                                       "{topic} industry-academia collaborative project",
                                       "{topic} 社会人 研究 プログラム"),
        "professor / community contact": ("{topic} open seminar working professionals",
                                          "{topic} 研究室 見学会 社会人 参加"),
        "certified language evidence": ("{lang} evening course university language centre",
                                        "{lang} 社会人 講座 大学"),
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

#: 失败类型（沿用 process / fact / infrastructure 三分类）
SOURCE_FAILURE_TYPES = {
    "source_not_found": "process",
    "source_found_no_opportunity": "fact",
    "source_found_not_current": "fact",
    "page_not_verifiable": "infrastructure",
    "js_rendered": "infrastructure",
    "blocked": "infrastructure",
}

#: 候选来源（用于 provenance 统计，不是白名单）
CANDIDATE_ORIGINS = ("known_source", "source_family_query", "general_search", "adjacent_discovery")


def bridge_intent_for(gap) -> str:
    if isinstance(gap, str):
        return GAP_TO_BRIDGE_INTENT.get("skill", "hands-on experience")
    return GAP_TO_BRIDGE_INTENT.get(gap.get("type") or "", "hands-on experience")


def families_for_gap(gap) -> list:
    """Gap → Bridge Intent → Source Families（按 gap 类型细分）。"""
    return list(INTENT_TO_FAMILIES.get(bridge_intent_for(gap), ()))


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


def plan_queries(gap, profile=None, topic=None, region=None, limit=6) -> list:
    """Gap → 具体 query（带来源 family / provenance / 阶段变体）。"""
    profile = profile or {}
    topic = topic or (gap.get("name") if isinstance(gap, dict) else str(gap)) or "opportunity"
    intent = bridge_intent_for(gap)
    fams = families_for_gap(gap)
    stage = stage_of(profile)
    lang = ((profile.get("constraints") or {}).get("language_constraint")
            or ("Japanese" if ("japan" in str(region or "").lower() or "日本" in str(topic))
                else "language"))
    out = []
    # 1) 阶段专用 query 优先
    for tpl in STAGE_INTENT_OVERRIDES.get(stage, {}).get(intent, ()):
        out.append({"query": tpl.format(topic=topic, lang=lang, ecosystem=topic),
                    "family": fams[0] if fams else None, "bridge_intent": intent,
                    "origin": "source_family_query", "stage": stage})
    # 2) family 模板
    for fam in fams:
        spec = SOURCE_FAMILIES.get(fam)
        if not spec:
            continue
        for tpl in spec["intents"]:
            out.append({"query": tpl.format(topic=topic, lang=lang, exam=lang,
                                            ecosystem=topic, country=region or ""),
                        "family": fam, "bridge_intent": intent,
                        "origin": "source_family_query", "stage": stage})
            if len(out) >= limit:
                return out
    # 3) 兜底：通用搜索（未知来源照常被发现）
    if not out:
        out.append({"query": f"{topic} opportunity students apply", "family": None,
                    "bridge_intent": intent, "origin": "general_search", "stage": stage})
    return out[:limit]


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
    key = str(source)
    e = data["entries"].setdefault(key, {"source": key, "category": category, "region": region,
                                         "runs": 0, "last_checked": None, "last_success": None,
                                         "historical_yield": 0, "failure_type": None})
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
