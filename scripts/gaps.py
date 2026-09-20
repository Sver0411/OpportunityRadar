#!/usr/bin/env python3
"""gaps.py - Gap 模型（V3 P1 ①②）。

Gap 必须来自**真实证据**，优先级：
  1. `requirements`  —— 本轮扫描到的真实目标机会的硬性要求
  2. `user_stated`   —— 用户明确说出的目标岗位 / 项目要求
  3. `repeated`      —— 多个真实机会中重复出现的要求
  4. `semantic`      —— 语义判断（必须写明依据）

**禁止凭空创造 Gap**：每个 Gap 都必须能解释"本轮 N 个目标机会中 M 个要求 X"。
并且**不要把所有东西都算成技能**：
  缺论文 → research；缺 Staff 级 ownership 证据 → leadership/experience；
  缺教授接触 → network；缺签证/地点 → location_visa。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import SKILL_EQUIVALENTS  # noqa: E402

#: Gap 类型（不要都归类成 skill）
GAP_TYPES = ("skill", "experience", "portfolio", "research", "language", "credential",
             "network", "leadership", "management", "location_visa", "education",
             "public_reputation")

GOAL_TO_GAP_TYPES = {
    "internship": ("experience",), "career": ("experience", "public_reputation"),
    "research": ("research", "network"), "education": ("education", "language"),
    "skill": ("skill",), "competition": ("skill", "portfolio"),
    "open_source": ("portfolio", "public_reputation"), "project": ("portfolio",),
    "funding": ("portfolio",), "networking": ("network",), "event": ("network",),
    "entrepreneurship": ("portfolio", "network", "leadership"),
}


#: 手续/工具类前置（不是能力缺口）：不进入 Gap，单独记录以免污染覆盖率分母
LOGISTICS_PREREQUISITE_PATTERNS = (
    "slack", "discord", "github account", "github profile", "email", "e-mail", "form",
    "registration", "sign up", "signup", "account", "cv", "resume", "transcript",
    "motivation letter", "personal statement", "fee", "payment", "账号", "报名", "联系方式",
    "简历", "成绩单", "陈述", "费用", "邮箱",
    # 2026-09-20 实测补全：这些同样是"参与手续/身份材料"，不是成长缺口
    "passport", "id card", "national id", "online application", "application form",
    "approval", "signature", "recommendation letter", "photo", "enrolment",
    "enrollment", "proof of", "在读证明", "学籍", "身份证", "护照", "个人资料",
    "申请表", "申请书", "报名表", "推荐信", "照片", "签名", "材料", "证明",
)

#: 只有在材料**本身是公开产出物**时，才允许当作 portfolio 缺口；
#: 其余材料一律进 preparation_items（影响 readiness，不影响缺口分母与 Bridge 搜索）。
PORTFOLIO_ARTEFACT_MARKERS = (
    "portfolio", "showreel", "demo", "video", "writeup", "write-up", "publication",
    "paper", "poster", "github repo", "repository", "report", "作品集", "作品",
    "演示", "方案", "报告",
)


def is_portfolio_artefact(requirement) -> bool:
    low = str(requirement or "").lower()
    return any(m in low for m in PORTFOLIO_ARTEFACT_MARKERS)


def is_logistics(requirement) -> bool:
    low = str(requirement or "").lower()
    return any(p in low for p in LOGISTICS_PREREQUISITE_PATTERNS)


def _tokens(text):
    return {t for t in re.split(r"[^0-9a-z\u4e00-\u9fff]+", str(text or "").lower()) if t}


_CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff]")


def _has_cjk(text) -> bool:
    return bool(_CJK_CHAR_RE.search(str(text or "")))


def _canon_tokens(text) -> set:
    """token 归一化：中文能力词映射到英文同义 token（SKILL_EQUIVALENTS）。"""
    out = set()
    for t in _tokens(text):
        out.add(SKILL_EQUIVALENTS.get(t, t))
    return out


def _cjk_contains(a_tokens, b_tokens) -> bool:
    """中文子串互为包含也算覆盖（「嵌入式」⊂「嵌入式开发」，纯 token 相等会漏）。"""
    a = {t for t in a_tokens if _has_cjk(t) and len(t) >= 2}
    b = {t for t in b_tokens if _has_cjk(t) and len(t) >= 2}
    return any(x in y or y in x for x in a for y in b)


def _profile_tokens(profile) -> set:
    """画像里表示"我已经具备"的 token：技能 + **兴趣** + 经历。"""
    have = set()
    for s in (profile.get("skills") or []):
        have |= _tokens(s.get("name") if isinstance(s, dict) else s)
    for i in (profile.get("interests") or []):
        have |= _tokens(i.get("name") if isinstance(i, dict) else i)
    exp = profile.get("experience") or {}
    for key in ("projects", "research", "internships", "competitions", "open_source",
                "certificates", "portfolio"):
        for item in (exp.get(key) or []):
            have |= _tokens(item)
    return have


def _covered(requirement, profile) -> bool:
    """要求是否被画像覆盖（保守：token 有交集才算覆盖；支持中英互认与中文子串）。"""
    req = _tokens(requirement)
    if not req:
        return True
    have_raw = _profile_tokens(profile)
    if _canon_tokens(requirement) & _canon_tokens(" ".join(have_raw)):
        return True
    return _cjk_contains(req, have_raw)


#: 缺口相关性等级（先判相关性，再决定要不要为它花 Bridge 搜索预算）
GAP_RELEVANCE_LEVELS = ("core_gap", "supporting_gap", "contextual_gap", "irrelevant")

#: 职业方向 → 与之相关的发展缺口类型（相关性判据的骨架，不做关键词硬匹配）
DIRECTION_AFFINITY = {
    "promotion": ("public_reputation", "leadership", "management", "skill", "network",
                  "experience"),
    "switch": ("skill", "portfolio", "experience", "credential", "network"),
    "research": ("research", "network", "language", "education", "portfolio",
                 "public_reputation"),
    "education": ("education", "language", "research", "portfolio", "network"),
    "entrepreneurship": ("portfolio", "network", "leadership", "experience", "management"),
    "skill_upgrade": ("skill", "portfolio", "experience", "credential"),
    "income": ("skill", "credential", "experience"),
    "explore": (),
}

#: 学术味道的缺口标记：非 research/education 方向时，这类缺口最多算 contextual
ACADEMIC_MARKERS = ("教授", "professor", "lab", "实验室", "学会", "academic", "论文",
                    "paper", "publication", "研究", "research")

#: 目标类型 → 职业方向
GOAL_TO_DIRECTION = {
    "internship": "switch", "career": "promotion", "research": "research",
    "education": "education", "skill": "skill_upgrade", "competition": "skill_upgrade",
    "open_source": "skill_upgrade", "project": "skill_upgrade", "funding": "research",
    "networking": "promotion", "event": "promotion", "entrepreneurship": "entrepreneurship",
    "hobby": "explore",
}


def career_direction(profile) -> str:
    """从 goals + career_state 推出**当前**职业方向（用于相关性判据，不用于猜人生）。"""
    profile = profile or {}
    cs = profile.get("career_state") or {}
    if str(cs.get("switch_intent") or "").lower() == "high":
        return "switch"
    if str(cs.get("entrepreneurship_intent") or "").lower() == "high":
        return "entrepreneurship"
    if str(cs.get("management_intent") or "").lower() == "high":
        return "promotion"
    if cs.get("promotion_target"):
        return "promotion"
    if str(cs.get("compensation_growth_intent") or "").lower() == "high":
        return "income"
    for g in (profile.get("goals") or []):
        if isinstance(g, dict):
            d = GOAL_TO_DIRECTION.get(g.get("type"))
            if d and d != "explore":
                return d
    return "explore"


def _is_academic(gap) -> bool:
    blob = f"{gap.get('name','')} {gap.get('sample','')}".lower()
    return any(m in blob for m in ACADEMIC_MARKERS)


def _matches_target(gap, profile) -> bool:
    """缺口是否直接出现在用户声明的目标里（target_role / promotion_target / target_industry）。"""
    cs = (profile or {}).get("career_state") or {}
    target = " ".join(str(cs.get(k) or "") for k in
                      ("target_role", "promotion_target", "target_industry", "current_direction"))
    if not target.strip():
        return False
    gt = _tokens(gap.get("name"))
    return bool(gt & _tokens(target))


def gap_relevance(gap, profile=None) -> dict:
    """判断一个潜在缺口对用户**当前目标**的相关度。

    只看当前目标，不猜用户应该往哪走；目标模糊时一律不产生 core_gap。
    """
    profile = profile or {}
    direction = career_direction(profile)
    affinity = DIRECTION_AFFINITY.get(direction, ())
    gtype = gap.get("type") or "skill"
    n = len(gap.get("opportunity_ids") or [])
    source = gap.get("source")
    hard = source in ("requirements", "user_stated", "repeated")

    if direction == "explore":
        return {"relevance": "contextual_gap", "direction": direction,
                "reason": "用户没有明确方向，缺口只能作为探索参考（不产生 core_gap）"}
    if _is_academic(gap) and direction not in ("research", "education"):
        return {"relevance": "contextual_gap", "direction": direction,
                "reason": f"学术向缺口，与当前方向「{direction}」关系弱（只在部分机会中出现）"}
    if gtype not in affinity:
        return {"relevance": "contextual_gap", "direction": direction,
                "reason": f"缺口类型 {gtype} 不在方向「{direction}」的关联网内"}
    if hard and (n >= 2 or source == "user_stated" or _matches_target(gap, profile)):
        why = (f"在 {n} 个目标机会中构成硬要求" if n >= 2
               else "用户明确提出的目标里直接出现" if source == "user_stated"
               else "出现在用户声明的目标方向里")
        return {"relevance": "core_gap", "direction": direction,
                "reason": f"方向「{direction}」的核心缺口（{why}）"}
    return {"relevance": "supporting_gap", "direction": direction,
            "reason": f"与方向「{direction}」相关，但不是硬门槛（增强项）"}


def development_gaps(gaps) -> list:
    """真正应该驱动 Bridge 搜索的缺口（core + supporting）。"""
    return [g for g in (gaps or [])
            if (g.get("relevance") or {}).get("relevance") in ("core_gap", "supporting_gap")]


def contextual_gaps(gaps) -> list:
    return [g for g in (gaps or [])
            if (g.get("relevance") or {}).get("relevance") == "contextual_gap"]


def collect_gaps(opportunities, profile=None, goals=None, stated_target=None) -> list:
    """收集 Gap（每条都带来源与样本量）。"""
    profile = profile or {}
    goals = goals or profile.get("goals") or []
    gaps: dict = {}

    def add(gtype, name, source, sample, opp_ids=None, priority="medium"):
        key = (gtype, str(name).strip().lower())
        if key in gaps:
            return
        gaps[key] = {"id": f"gap-{gtype}-{re.sub(r'[^0-9a-z]+', '-', str(name).lower())[:24]}",
                     "type": gtype, "name": str(name), "source": source,
                     "sample": sample, "opportunity_ids": opp_ids or [], "priority": priority}

    # 1/3. 来自真实机会的硬性要求（重复出现 → 优先级更高）
    req_counter: dict = {}
    logistics: list = []
    preparation: list = []            # 影响 readiness，不影响缺口分母
    eligibility_constraints: list = []  # 机会侧的资格事实，不是用户的能力缺口
    for o in opportunities or []:
        if not isinstance(o, dict):
            continue
        oid = o.get("id")
        for field, gtype in (("skills_required", "skill"), ("prerequisites", "skill")):
            for req in (o.get(field) or []):
                if _covered(req, profile):
                    continue
                if is_logistics(req):            # 手续类前置不当作缺口
                    logistics.append(str(req))
                    continue
                req_counter.setdefault((gtype, str(req)), []).append(oid)
        # 参与材料：只有**本身是公开产出物**时才可能是 portfolio 缺口
        for mat in (o.get("required_materials") or []):
            if _covered(mat, profile):
                continue
            if is_logistics(mat):
                logistics.append(str(mat))
            elif is_portfolio_artefact(mat):
                req_counter.setdefault(("portfolio", str(mat)), []).append(oid)
            else:
                preparation.append(str(mat))
        lang = o.get("language_requirement")
        for item in (lang if isinstance(lang, list) else [lang] if lang else []):
            if isinstance(item, dict):
                gap_name = f"{item.get('language')} {item.get('min_level') or ''}".strip()
                if not _language_covered(item, profile):
                    req_counter.setdefault(("language", gap_name), []).append(oid)
        if o.get("school_requirement") and not profile.get("education", {}).get("school"):
            req_counter.setdefault(("credential", str(o["school_requirement"])), []).append(oid)
        if o.get("nationality_requirement"):
            # "仅限某国籍"是机会侧的资格事实 → 走资格判定，不是用户的缺口
            # （以前它会被当成 location_visa gap，实测里产出「缺 Non-Chinese citizens」这种荒谬缺口）
            eligibility_constraints.append(str(o["nationality_requirement"]))

    total = len([o for o in (opportunities or []) if isinstance(o, dict)]) or 1
    for (gtype, name), ids in sorted(req_counter.items(), key=lambda kv: -len(kv[1])):
        n = len(ids)
        source = "repeated" if n >= 3 else "requirements"
        priority = "high" if n >= 3 else "medium"
        add(gtype, name, source, f"本轮 {total} 个目标机会中 {n} 个要求「{name}」",
            ids, priority)

    # 2. 用户明确说出的目标方向 → 对应的非技能缺口
    stated = str(stated_target or "").strip()
    target_blob = " ".join([stated] + [str(g.get("type")) for g in goals if isinstance(g, dict)])
    have_public = bool((profile.get("experience") or {}).get("open_source")
                       or (profile.get("experience") or {}).get("portfolio"))
    have_research = bool((profile.get("experience") or {}).get("research"))
    career_stage = profile.get("career_stage") or []

    if stated:
        add("experience", f"{stated} 相关的可验证经历", "user_stated",
            f"用户在目标中明确提到「{stated}」，画像中没有对应经历", [], "high")
    if ("career" in target_blob or "promotion" in target_blob or "senior" in target_blob.lower()) \
            and not have_public:
        add("public_reputation", "公开影响力证据（演讲 / maintainer / 社区角色）", "semantic",
            "目标是晋升/职业进阶，但画像里没有公开产出", [], "high")
        add("leadership", "ownership / 跨团队项目证据", "semantic",
            "晋升评审关注 ownership，画像未见相关证据", [], "medium")
    if "research" in target_blob or "education" in target_blob:
        if not have_research:
            add("research", "研究经历 / 论文 / 实验室接触", "semantic",
                "目标包含研究或升学，画像中没有研究经历", [], "high")
        add("network", "教授 / 实验室联系人", "semantic",
            "升学或研究型目标通常需要教授接触，画像中没有该网络", [], "high")
    for lang in (profile.get("languages") or []):
        if isinstance(lang, dict) and not lang.get("level") and not lang.get("score"):
            continue
    if any(g.get("type") == "education" for g in goals if isinstance(g, dict)):
        add("language", "目标国家需要的语言成绩", "semantic",
            "升学目标通常有语言门槛，画像未提供成绩", [], "medium")

    # 管理路线
    cs = profile.get("career_state") or {}
    if str(cs.get("management_intent") or "").lower() == "high":
        add("management", "团队管理 / 带人经历", "user_stated",
            "用户明确表达管理路线意向，画像没有带人经历", [], "high")

    out = sorted(gaps.values(), key=lambda g: ({"high": 0, "medium": 1, "low": 2}[g["priority"]],
                                               g["type"], g["name"]))
    for gap in out:
        # 不做截断：这些"非缺口但必须记录"的项一旦被切掉就是静默丢弃，
        # 要精简应在展示层做（见 references/output-format.md）。
        gap["logistics_prerequisites"] = sorted(set(logistics))
        gap["preparation_items"] = sorted(set(preparation))
        gap["eligibility_constraints"] = sorted(set(eligibility_constraints))
        gap["relevance"] = gap_relevance(gap, profile)      # 相关性先于 Bridge 搜索
    order = {"core_gap": 0, "supporting_gap": 1, "contextual_gap": 2, "irrelevant": 3}
    out.sort(key=lambda g: (order.get(g["relevance"]["relevance"], 4),
                            {"high": 0, "medium": 1, "low": 2}[g["priority"]], g["name"]))
    return out


def _language_covered(item, profile) -> bool:
    want = str(item.get("language") or "").lower()
    min_level = str(item.get("min_level") or "").upper()
    for lang in (profile.get("languages") or []):
        if not isinstance(lang, dict):
            continue
        if str(lang.get("language") or "").lower() != want:
            continue
        level = str(lang.get("level") or "").upper()
        if min_level.startswith("N") and level.startswith("N"):
            try:
                return int(level[1]) <= int(min_level[1])
            except ValueError:
                return False
        if min_level in ("A1", "A2", "B1", "B2", "C1", "C2") and level in (
                "A1", "A2", "B1", "B2", "C1", "C2"):
            return level >= min_level
        if lang.get("score") or lang.get("level"):
            return True
    return False


def gap_summary(gaps) -> dict:
    by_type: dict = {}
    for g in gaps or []:
        by_type.setdefault(g["type"], 0)
        by_type[g["type"]] += 1
    return {"total": len(gaps or []), "by_type": by_type,
            "by_relevance": {lvl: sum(1 for g in (gaps or [])
                                      if (g.get("relevance") or {}).get("relevance") == lvl)
                             for lvl in GAP_RELEVANCE_LEVELS},
            "development_gaps": len(development_gaps(gaps)),
            "logistics_prerequisites": sorted({i for g in (gaps or [])
                                               for i in (g.get("logistics_prerequisites") or [])}),
            "preparation_items": sorted({i for g in (gaps or [])
                                         for i in (g.get("preparation_items") or [])}),
            "eligibility_constraints": sorted({i for g in (gaps or [])
                                               for i in (g.get("eligibility_constraints") or [])}),
            "sources": {s: sum(1 for g in gaps if g["source"] == s)
                        for s in ("requirements", "user_stated", "repeated", "semantic")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gap 模型：从真实机会/目标推导缺口")
    ap.add_argument("--opportunities", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--target", default=None, help="用户明确说出的目标方向")
    args = ap.parse_args(argv)
    data = json.load(open(args.opportunities, encoding="utf-8"))
    opps = data.get("opportunities", [data]) if isinstance(data, dict) else data
    profile = json.load(open(args.profile, encoding="utf-8"))
    gaps = collect_gaps(opps, profile, stated_target=args.target)
    print(json.dumps({"gaps": gaps, "summary": gap_summary(gaps)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
