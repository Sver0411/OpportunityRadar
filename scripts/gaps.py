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


def _tokens(text):
    return {t for t in re.split(r"[^0-9a-z\u4e00-\u9fff]+", str(text or "").lower()) if t}


def _covered(requirement, profile) -> bool:
    """要求是否被画像覆盖（保守：token 有交集才算覆盖）。"""
    req = _tokens(requirement)
    if not req:
        return True
    have = set()
    for s in (profile.get("skills") or []):
        have |= _tokens(s.get("name") if isinstance(s, dict) else s)
    exp = profile.get("experience") or {}
    for key in ("projects", "research", "internships", "competitions", "open_source",
                "certificates", "portfolio"):
        for item in (exp.get(key) or []):
            have |= _tokens(item)
    return bool(req & have)


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
    for o in opportunities or []:
        if not isinstance(o, dict):
            continue
        oid = o.get("id")
        for field, gtype in (("skills_required", "skill"), ("prerequisites", "skill"),
                             ("required_materials", "portfolio")):
            for req in (o.get(field) or []):
                if _covered(req, profile):
                    continue
                req_counter.setdefault((gtype, str(req)), []).append(oid)
        lang = o.get("language_requirement")
        for item in (lang if isinstance(lang, list) else [lang] if lang else []):
            if isinstance(item, dict):
                gap_name = f"{item.get('language')} {item.get('min_level') or ''}".strip()
                if not _language_covered(item, profile):
                    req_counter.setdefault(("language", gap_name), []).append(oid)
        if o.get("school_requirement") and not profile.get("education", {}).get("school"):
            req_counter.setdefault(("credential", str(o["school_requirement"])), []).append(oid)
        if o.get("nationality_requirement") and not profile.get("nationality"):
            req_counter.setdefault(("location_visa", str(o["nationality_requirement"])), []).append(oid)

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
