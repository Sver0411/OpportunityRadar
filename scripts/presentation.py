#!/usr/bin/env python3
"""presentation.py — 输出适配层（P1 Output & Decision UX）。

这一层**不做判断**，只把 V3 已有的判断结果翻译成用户能读的表达：

    Decision Confidence   → 决定"话能说多重"
    Participation wording  → 按机会类型换成人话（不是所有机会都叫"Eligible"）
    Recommendation card   → 统一暴露 为什么 / 补什么缺口 / 投入 / 留下什么 / 下一步价值
    Explore axes          → 无目标用户的试错维度（不是新 taxonomy）
    Self-directed fallback→ 与真实机会严格分开
    Precision guard       → 资源未知时不许给伪精确比例
    Output metrics        → 本轮的 8 个输出质量指标

**纪律**
  * 不引入新的评分；`decision_confidence` 只控制表达强度，不参与排序
  * 预算未知时**禁止**输出百分比 / "每天 X 小时"这类无依据的精确分配
  * Low confidence 禁止 "最优 / 最佳 / 你现在必须 / 唯一正确路线"
  * Self-directed fallback 永远不进入 recommended_now
  * Explore 维度只在 career_direction == explore 时启用，**达标才出现**，不为多样性塞弱结果
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    APPLICATION_STATUSES, OPPORTUNITY_APPLICATION_STATUSES, ELIGIBILITY_VERDICTS,
)

# ---------------------------------------------------------------- 1. Decision Confidence
CONFIDENCE_LEVELS = ("high", "medium", "low")

#: 决定置信度的信号（每项：已知 / 未知）
CONFIDENCE_SIGNALS = ("goal_clarity", "profile_completeness", "time_budget_known",
                      "financial_budget_known", "location_known", "eligibility_known",
                      "evidence_completeness")

#: 关键约束：这些未知会直接压低置信度
CRITICAL_SIGNALS = ("goal_clarity", "time_budget_known", "location_known")

#: 各置信度允许 / 禁止的说法（防止"信息不足却下强结论"）
CLAIM_WORDING = {
    "high": {
        "allowed": ("你的主线可以优先放在", "可以优先"),
        "forbidden": ("绝对", "保证", "唯一正确路线"),
    },
    "medium": {
        "allowed": ("从目前信息看", "更值得先验证", "值得先试"),
        "forbidden": ("最优", "最佳", "你现在必须", "唯一正确路线", "一定要"),
    },
    "low": {
        "allowed": ("目前值得试的几种方向", "如果你更在意", "仅供参考"),
        "forbidden": ("最优", "最佳", "你现在必须", "唯一正确路线", "一定要",
                      "建议你放弃", "你应该选择"),
    },
}

#: 任何置信度都不许出现的绝对化表述
GLOBAL_FORBIDDEN = ("最优", "最佳", "唯一正确路线", "录取概率", "预计薪资")


def _constraints(profile) -> dict:
    return (profile or {}).get("constraints") or {}


def _has(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in ("unknown", "n/a", "null")
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _goal_clarity(profile) -> tuple:
    """目标是否明确：有 goals 且方向不是 explore。"""
    goals = [g for g in ((profile or {}).get("goals") or []) if isinstance(g, dict)]
    if not goals:
        return False, "没有声明任何目标"
    if all(str(g.get("type")) in ("hobby", "explore") for g in goals):
        return False, "目标只有探索类意图，没有明确方向"
    return True, ""


def decision_confidence(profile, rows=None, gaps=None) -> dict:
    """把"信息够不够"变成一个档位，用来控制**最终表达强度**（不是新的排名分）。"""
    profile = profile or {}
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    signals, unknown, reasons = {}, [], []

    goal_ok, why = _goal_clarity(profile)
    signals["goal_clarity"] = goal_ok
    if not goal_ok:
        unknown.append("goal_clarity")
        reasons.append(f"目标清晰度：{why}")

    profile_fields = ("education", "skills", "interests", "life_stage", "career_stage")
    known = sum(1 for f in profile_fields if _has(profile.get(f)))
    signals["profile_completeness"] = round(known / len(profile_fields), 3)
    if signals["profile_completeness"] < 0.6:
        unknown.append("profile_completeness")
        reasons.append(f"画像完整度：{known}/{len(profile_fields)} 个基础字段有内容")

    cons = _constraints(profile)
    for key, name in (("weekly_time", "time_budget_known"),
                      ("budget", "financial_budget_known")):
        ok = _has(cons.get(key))
        signals[name] = ok
        if not ok:
            unknown.append(name)
    signals["location_known"] = not (profile.get("_location_unknown") or
                                     ("location" in (profile.get("_unknown") or [])))
    if not signals["location_known"]:
        unknown.append("location_known")

    # 资格与证据：按候选比例
    if rows:
        elig_known = sum(1 for r in rows
                         if str(r.get("eligibility_verdict") or "Unknown") != "Unknown")
        ev_known = sum(1 for r in rows if r.get("evidence_complete"))
        signals["eligibility_known"] = round(elig_known / len(rows), 3)
        signals["evidence_completeness"] = round(ev_known / len(rows), 3)
        if signals["eligibility_known"] < 0.6:
            unknown.append("eligibility_known")
            reasons.append(f"资格可判定的候选仅 {elig_known}/{len(rows)}")
        if signals["evidence_completeness"] < 0.5:
            unknown.append("evidence_completeness")
            reasons.append(f"证据完整的候选仅 {ev_known}/{len(rows)}")
    else:
        signals["eligibility_known"] = None
        signals["evidence_completeness"] = None

    if not goal_ok:
        level = "low"
    else:
        critical_unknown = [s for s in CRITICAL_SIGNALS if signals.get(s) is False] + \
                           [s for s in ("eligibility_known", "evidence_completeness")
                            if signals.get(s) not in (None,) and (signals.get(s) or 0) < 0.6]
        others_unknown = [s for s in ("time_budget_known", "financial_budget_known",
                                      "location_known", "profile_completeness")
                          if signals.get(s) is False or signals.get(s) == 0]
        level = "medium" if (critical_unknown or others_unknown or unknown) else "high"

    # 关键约束缺失时不允许 high
    if level == "high" and any(signals.get(s) is False for s in CRITICAL_SIGNALS):
        level = "medium"

    return {
        "level": level,
        "signals": signals,
        "unknown": sorted(set(unknown)),
        "reasons": reasons,
        "allowed_wording": CLAIM_WORDING[level]["allowed"],
        "forbidden_wording": CLAIM_WORDING[level]["forbidden"],
        "note": {
            "high": "目标、资源约束与关键资格基本明确 → 可以给出有主张的建议",
            "medium": "方向明确但仍有关键 Unknown → 用「从目前信息看…更值得先验证」的口气",
            "low": "目标/资源/背景高度未知 → 只给几种可试方向与对照，不下结论",
        }[level],
    }


# ---------------------------------------------------------------- 2. 伪精确防护
_PRECISION_PATTERNS = (
    # (正则, 类型, 需要哪些依据才算"有根据")
    (re.compile(r"\d{1,3}\s*%"), "percentage", ("weekly_time", "available_period")),
    (re.compile(r"\b\d{1,3}\s*/\s*\d{1,3}\s*/\s*\d{1,3}\b"), "ratio", ("available_period",)),
    (re.compile(r"每天\s*[约大概]?\s*\d+(?:\.\d+)?\s*(?:个)?小时"), "hours_per_day",
     ("weekly_time",)),
    (re.compile(r"每小时\s*\d+(?:\.\d+)?\s*小时"), "hours_per_day", ("weekly_time",)),
    # 加总式的精确投入："3h + 1h + 1h = 5h" —— 用户没给预算时，这个 5h 就是系统凭空造的
    (re.compile(r"\d+\s*(?:h|小时)\s*[+＋]\s*\d+\s*(?:h|小时)"), "hours_sum",
     ("weekly_time",)),
)

#: 预算未知时的定性档位（代替百分比）
QUALITATIVE_ALLOCATION = ("主线", "辅线", "低成本试错")

BUDGET_UNKNOWN_NOTE = "你的可用时间还未知，所以暂不做具体比例分配。"


def budget_known(profile) -> dict:
    """用户是否**明确**给出了资源约束（决定能否给精确分配）。"""
    cons = _constraints(profile)
    return {"weekly_time": _has(cons.get("weekly_time")),
            "available_period": _has(cons.get("available_period")),
            "budget": _has(cons.get("budget"))}


def scan_unsupported_precision(text, profile) -> list:
    """找出"没有依据的精确资源分配"。返回命中列表（空 = 合规）。

    按**依据**判定，而不是一概禁止：
      * `weekly_time` 已知 → 允许 `3h + 1h + 1h = 5h` 这种按小时分配
      * `available_period` 已知 → 才允许谈"占用整个周期的比例"
      * 依据缺失时，百分比 / 每天小时数 / 三段比例一律算无依据精度
    """
    known = budget_known(profile)
    hits, seen = [], set()
    for pattern, kind, basis in _PRECISION_PATTERNS:
        if all(known.get(b) for b in basis):
            continue                       # 有依据 → 允许这种精度
        for m in pattern.finditer(str(text or "")):
            key = (kind, m.group(0).strip())
            if key in seen:
                continue
            seen.add(key)
            hits.append({"text": m.group(0).strip(), "kind": kind,
                         "missing_basis": [b for b in basis if not known.get(b)],
                         "reason": f"{kind} 需要 {'/'.join(basis)} 作为依据"})
    return hits


def allocation_style(profile) -> dict:
    """预算已知 → 允许量化；未知 → 只给定性档位。"""
    known = budget_known(profile)
    if known["weekly_time"]:
        return {"mode": "quantitative", "allowed_levels": ("hours",),
                "note": "用户给出了每周可用时间 → 可以按小时分配（如 3h + 1h + 1h = 5h）"}
    return {"mode": "qualitative", "allowed_levels": QUALITATIVE_ALLOCATION,
            "note": BUDGET_UNKNOWN_NOTE, "forbid": ("percent", "hours_per_day")}


def format_allocation(profile, items=None) -> dict:
    """把一组机会翻译成"可执行的配置"，并遵守资源未知时的禁止项。"""
    style = allocation_style(profile)
    items = [i for i in (items or []) if isinstance(i, dict)]
    if style["mode"] == "qualitative":
        out = []
        for idx, it in enumerate(items):
            level = QUALITATIVE_ALLOCATION[min(idx, len(QUALITATIVE_ALLOCATION) - 1)]
            out.append({"level": level, "opportunity_id": it.get("id"),
                        "title": it.get("title")})
        return {"mode": "qualitative", "items": out, "note": BUDGET_UNKNOWN_NOTE,
                "total_note": "未按时间做比例分配"}
    total = sum(float(it.get("weekly_hours") or 0) for it in items)
    return {"mode": "quantitative",
            "items": [{"level": "主线" if idx == 0 else "辅线",
                       "opportunity_id": it.get("id"), "title": it.get("title"),
                       "hours": it.get("weekly_hours")}
                      for idx, it in enumerate(items)],
            "total_hours": round(total, 2),
            "note": f"合计约 {round(total, 1)}h/周，与你给出的每周可用时间对齐"}


# ---------------------------------------------------------------- 3. Category-aware participation
PARTICIPATION_FAMILIES = {
    "open_source": "open_source", "project": "open_source",
    "competition": "event", "event": "event",
    "networking": "community",
}

PARTICIPATION_WORDING = {
    "standard": {"Eligible": "Eligible", "Probably Eligible": "Probably Eligible",
                 "Unknown": "Unknown", "Probably Ineligible": "Probably Ineligible",
                 "Ineligible": "Ineligible"},
    "open_source": {"Eligible": "Open participation",
                    "Probably Eligible": "Open participation",
                    "Unknown": "Contribution prerequisites",
                    "Probably Ineligible": "Restricted",
                    "Ineligible": "Restricted"},
    "event": {"Eligible": "Registration open",
              "Probably Eligible": "Registration open",
              "Unknown": "Eligibility needs confirmation",
              "Probably Ineligible": "Eligibility needs confirmation",
              "Ineligible": "Not currently open"},
    # 用户规定 Community/Mentoring 只有三个标签（无 "Unknown"）→ 无法判定时用中间的
    # "Prerequisites apply"，比直接写 "Unknown" 更有信息量且不越界。
    "community": {"Eligible": "Open to join",
                  "Probably Eligible": "Prerequisites apply",
                  "Unknown": "Prerequisites apply",
                  "Probably Ineligible": "Invitation / selection required",
                  "Ineligible": "Invitation / selection required"},
}

PARTICIPATION_NOTES = {
    "open_source": {"Unknown": "官方页没有写参与门槛；开源贡献通常要求账号 / CLA / issue 认领等前置",
                    "Probably Eligible": "仍需满足贡献前置条件，例如 CLA、issue 认领"},
    "event": {"Unknown": "官网未给出明确的报名开放声明，需要先向主办方确认",
              "Eligibility needs confirmation": "官网未给出明确的报名开放声明，需要先向主办方确认"},
    "community": {"Probably Eligible": "可能需要既有贡献记录或成员推荐"},
}


def participation_family(category) -> str:
    return PARTICIPATION_FAMILIES.get(str(category or "").lower(), "standard")


#: 页面本身没核实清楚时，各 family 用的"待确认"说法
UNVERIFIED_LABEL = {"standard": "Unknown", "open_source": "Contribution prerequisites",
                    "event": "Eligibility needs confirmation",
                    "community": "Prerequisites apply"}

#: 这些 verification_status 不允许给出肯定式说法
UNCONFIRMED_VERIFICATION = ("unverified", "conflicting", "expired")


def participation_wording(category, verdict, freshness=None, verification_status=None) -> dict:
    """把资格判定翻译成该机会类型的人类可读语义（底层模型不变，只换说法）。

    两点纪律：
      * 周期已结束 → 一律 "Not currently open"（不管资格怎么样）
      * 页面本身没核实清楚（unverified / conflicting）→ **不许**说 "Registration open"，
        只能给待确认说法 —— 实测中发现官方页自相矛盾的机会被写成了 "Registration open"
    """
    family = participation_family(category)
    verdict = verdict if verdict in ELIGIBILITY_VERDICTS else "Unknown"
    if str(freshness or "") in ("closed", "expired"):
        return {"family": family, "label": "Not currently open", "verdict": verdict,
                "note": "本轮周期已结束"}
    if str(verification_status or "") in UNCONFIRMED_VERIFICATION:
        return {"family": family, "label": UNVERIFIED_LABEL[family], "verdict": verdict,
                "note": f"页面本身未核实清楚（verification_status={verification_status}），"
                        "所以只能给待确认说法"}
    label = PARTICIPATION_WORDING[family].get(verdict, verdict)
    return {"family": family, "label": label, "verdict": verdict,
            "note": (PARTICIPATION_NOTES.get(family) or {}).get(verdict, "")}


# ---------------------------------------------------------------- 4. 行动措辞（§10）
ACTION_LABELS = ("现在可以行动", "值得进一步核实", "值得先了解", "值得拿来试方向")


def action_label(row, confidence=None, goal_known=True) -> dict:
    """只有 actionable + evidence_complete + 关键约束已知，才允许说"现在可以行动"。"""
    row = row or {}
    level = (confidence or {}).get("level")
    constraints_known = (confidence or {}).get("signals", {}).get("time_budget_known") is not False
    if not goal_known or level == "low":
        return {"label": "值得拿来试方向",
                "reason": "目标或资源还不明确，先当作方向实验"}
    if not row.get("evidence_complete"):
        return {"label": "值得进一步核实",
                "reason": "关键信息（官方来源/报名状态）还没核实完整"}
    if not row.get("actionable") or not row.get("participation_open"):
        return {"label": "值得先了解",
                "reason": "本轮无法确认当前是否可参与"}
    if constraints_known:
        return {"label": "现在可以行动", "reason": "可参与、证据完整、资源约束已知"}
    return {"label": "值得进一步核实",
            "reason": "可参与且证据完整，但你的时间预算还没给出"}


# ---------------------------------------------------------------- 5. Explore 维度（不是新 taxonomy）
EXPLORE_AXES = ("build", "contribute", "research", "volunteer", "community",
                "creative", "entrepreneurship", "cross_domain")

#: 只保留"该类别必然意味着这个轴"的**无歧义**映射。
#: 有歧义的类别（competition / hobby / event / career / skill_development / funding /
#: language）**不直接授予轴** —— 一场诗歌比赛和一场创业比赛都是 competition，
#: 把它们都算作 build 正是上一轮把 Weimar 诗歌电影节标成 build 的原因。
AXIS_BY_CATEGORY = {
    "open_source": "contribute",
    "project": "build",
    "research": "research",
    "education": "research",
    "entrepreneurship": "entrepreneurship",
    "networking": "community",
}

#: 明确不授予轴的类别（必须由关键词证据支撑，否则这条机会就没有轴）
AXIS_NEUTRAL_CATEGORIES = ("competition", "hobby", "event", "career", "skill_development",
                           "funding", "language")

AXIS_LABELS = {"build": "Build 做一个东西", "contribute": "Contribute 贡献到真实项目",
               "research": "Research 接触研究/学术", "volunteer": "Volunteer 公益/国际志愿",
               "community": "Community 社区/组织/mentor", "creative": "Creative 表达/内容/设计",
               "entrepreneurship": "Entrepreneurship 创业/challenge/accelerator",
               "cross_domain": "Cross-domain 跨学科/社会议题"}

#: 轴信号：**精确 token 或规范化短语**（不是子串）。
#: 英文按 token 边界匹配（"art" 不会命中 "startup"）；中文按 ≥2 字的整段包含
#: （中文没有词边界，单字一律不匹配）。
AXIS_SIGNALS = {
    "build": ("hackathon", "build challenge", "maker", "makerspace", "prototype",
              "capstone", "open innovation challenge", "game jam", "demo day", "build",
              "robotics", "作品", "搭建"),
    "contribute": ("contributor", "contributing", "contribution", "maintainer", "committer",
                   "pull request", "good first issue", "open source", "upstream",
                   "贡献", "开源"),
    "research": ("research", "researcher", "laboratory", "lab", "paper", "publication",
                 "seminar", "symposium", "thesis", "academic", "poster",
                 "研究", "论文", "实验室"),
    "volunteer": ("volunteer", "volunteering", "nonprofit", "non-profit", "ngo", "charity",
                  "志愿者", "志愿", "公益"),
    "community": ("mentor", "mentorship", "mentoring", "community", "meetup", "chapter",
                  "alumni", "society", "association", "club", "network",
                  "导师", "社群", "社区", "学会"),
    "creative": ("art", "artist", "artistic", "film", "filmmaker", "poetry", "poem", "poet",
                 "design", "designer", "writing", "writer", "content", "podcast", "music",
                 "animation", "illustration", "photography", "photographer", "creative",
                 "storytelling", "创作", "设计", "写作", "内容", "影视", "摄影", "诗歌", "艺术"),
    "entrepreneurship": ("startup", "start-up", "accelerator", "incubator", "entrepreneur",
                         "entrepreneurship", "venture", "co-founder", "pitch",
                         "创业", "孵化"),
    "cross_domain": ("interdisciplinary", "cross-domain", "cross domain", "social impact",
                     "public policy", "sustainability", "climate", "public health", "civic",
                     "sdg", "social innovation", "跨学科", "社会议题", "公共政策", "社会创新"),
}

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_TOKEN_SPLIT_RE = re.compile(r"[^0-9a-z\u3400-\u9fff]+")


def _normalized(text) -> tuple:
    """→ (token 集合, token 序列串, 原文)。英文复数同时收单数（明确规则，不是词干化猜测）。"""
    raw = str(text or "").lower()
    toks = [t for t in _TOKEN_SPLIT_RE.split(raw) if t]
    extra = {t[:-1] for t in toks if len(t) > 4 and re.fullmatch(r"[a-z]+s", t)}
    tok_set = set(toks) | extra
    joined = " " + " ".join(toks) + " "
    return tok_set, joined, raw


def _match_signal(signal, tok_set, joined, raw) -> bool:
    # 规范化短语信号（例如 "open source"）也按**短语**处理，不逐 token 拆
    sig = str(signal or "").lower().strip()
    if not sig:
        return False
    if _CJK_RE.search(sig):
        compact = sig.replace(" ", "")
        return len(compact) >= 2 and compact in raw.replace(" ", "")   # 中文：≥2 字整段
    parts = sig.split()
    sig_tokens = [p for p in _TOKEN_SPLIT_RE.split(sig) if p]
    if not sig_tokens:
        return False
    if len(sig_tokens) == 1:
        return sig_tokens[0] in tok_set          # 英文：精确 token（含复数归一）
    return f" {' '.join(sig_tokens)} " in joined  # 英文短语：token 边界对齐，非子串


def _axis_text(row) -> str:
    """只看"这条机会**是什么**、以及**会产出什么**"。

    **不把 summary 算进来**：摘要常常顺带罗列一堆领域（例如"覆盖研究、写作、设计…"），
    那会让一条机会同时命中 4 个轴 —— 上一轮 UNV 一条命中 5 轴就是这么来的。
    """
    row = row or {}
    return " ".join([str(row.get("title") or ""),
                     " ".join(str(t) for t in (row.get("tags") or [])),
                     " ".join(str(x) for x in (row.get("produces") or [])),
                     " ".join(str(x) for x in (row.get("skills_preferred") or []))])


def explore_axes_explained(row) -> list:
    """每条轴都带**理由**：来自类别映射还是哪个信号词。"""
    row = row or {}
    tok_set, joined, raw = _normalized(_axis_text(row))
    out = []
    cat = str(row.get("primary_category") or "").lower()
    if cat in AXIS_BY_CATEGORY:
        out.append({"axis": AXIS_BY_CATEGORY[cat], "via": "category", "signal": cat})
    for axis, signals in AXIS_SIGNALS.items():
        hits = [sig for sig in signals if _match_signal(sig, tok_set, joined, raw)]
        if hits:
            out.append({"axis": axis, "via": "signal", "signal": hits[0],
                        "all_signals": hits[:4]})
    seen, dedup = set(), []
    for item in out:
        if item["axis"] in seen:
            continue
        seen.add(item["axis"])
        dedup.append(item)
    return sorted(dedup, key=lambda x: x["axis"])


def explore_axes_of(row) -> list:
    """一个候选属于哪些探索维度（可多个）。只返回轴名，理由见 explore_axes_explained。"""
    return [x["axis"] for x in explore_axes_explained(row)]


def explore_coverage(rows) -> dict:
    """探索覆盖了哪些维度。**达标才出现**，不为多样性塞弱结果；每条轴附来源理由。"""
    by_axis, reasons = {}, []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        for item in explore_axes_explained(r):
            by_axis.setdefault(item["axis"], []).append(r.get("id"))
            reasons.append({"opportunity_id": r.get("id"), **item})
    return {"axes": sorted(by_axis),
            "axis_count": len(by_axis),
            "by_axis": {k: v for k, v in sorted(by_axis.items())},
            "axis_reasons": reasons,
            "missing_axes": [a for a in EXPLORE_AXES if a not in by_axis],
            "note": "只列出真的达标了的维度；每条轴都能追溯到类别映射或具体信号词"}


def explore_focus(profile) -> dict:
    """仅在 career_direction == explore 时启用跨方向试错。"""
    try:
        import gaps as GP
        direction = GP.career_direction(profile or {})
    except Exception:
        direction = "explore"
    enabled = direction == "explore"
    return {"enabled": enabled, "career_direction": direction,
            "note": ("无明确方向 → 用跨维度试错代替单一路线"
                     if enabled else "有明确方向 → 不用跨维度试错，按方向收敛")}


def technical_share(rows) -> dict:
    """技术类占比：防止 explore 场景被系统自身的技术偏好占满。"""
    tech_cats = {"skill_development", "open_source", "project", "research", "competition"}
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        return {"tech": 0, "total": 0, "share": None}
    tech = sum(1 for r in rows if str(r.get("primary_category") or "") in tech_cats)
    return {"tech": tech, "total": len(rows), "share": round(tech / len(rows), 3),
            "note": "技术类不应占满全部主推荐（无目标用户尤其）"}


# ---------------------------------------------------------------- 6. Self-directed fallback
def self_directed_fallback(gap, reason="本轮没有找到足够合适的外部 Bridge") -> dict:
    """自建替代路径：**不是**机会，必须显式标注，永不进入 recommended_now。"""
    name = gap.get("name") if isinstance(gap, dict) else str(gap or "某项缺口")
    return {"kind": "self_directed", "gap": name, "always_label": "自建替代路径",
            "reason": reason,
            "not_an_opportunity": True,
            "note": "这是自己安排的做法，不是外部真实机会，因此不能与真实机会并列在推荐里"}


def split_recommendations(rows) -> dict:
    """把真实机会与自建路径分开（禁止混在一起）。"""
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    real = [r for r in rows if r.get("kind") != "self_directed"]
    selfdir = [r for r in rows if r.get("kind") == "self_directed"]
    return {"recommended_real": real, "self_directed": selfdir,
            "mixed": bool(real and selfdir and
                          any(r.get("zone") == "recommended_now" for r in selfdir)),
            "rule": "self_directed 不得出现在主推荐里，必须单独一段"}


# ---------------------------------------------------------------- 7. 推荐卡（最多 5 个用户可读字段）
CARD_FIELDS = ("why_fit", "gap_filled", "effort", "leaves_behind", "next_value")


def recommendation_card(row, profile=None, gaps=None, bridges=None, confidence=None,
                        action=None) -> dict:
    """一条机会 → 用户可读卡片。宁可少字段，也不机械模板化。"""
    row = row or {}
    cards_gap = _gap_for(row, gaps, bridges)
    card = {
        "opportunity_id": row.get("id"),
        "title": row.get("title"),
        "organization": row.get("organization"),
        "category": row.get("primary_category"),
        "official_url": row.get("official_url"),
        "participation": participation_wording(row.get("primary_category"),
                                               row.get("eligibility_verdict"),
                                               row.get("freshness"),
                                               row.get("verification_status")),
        "action": action or action_label(row, confidence),
    }
    card["why_fit"] = _why_fit(row, profile)
    card["gap_filled"] = cards_gap
    card["effort"] = _effort(row)
    card["leaves_behind"] = _leaves(row)
    card["next_value"] = _next_value(row)
    unknown = list(row.get("evidence_missing") or [])
    uncertain = _uncertain_eligibility_notes(row)
    unknown += [text for text, _raw in uncertain]
    if str(row.get("eligibility_verdict")) == "Unknown":
        unknown.append("资格条件未写明")
    if not _has(_weekly_commitment(row)) and not _has(row.get("time_commitment")):
        unknown.append("每周投入未写明")
    card["needs_confirmation"] = unknown[:4]
    card["needs_confirmation_details"] = {
        "uncertain_reasons_raw": [raw for _text, raw in uncertain],
        "note": "结构化原文仅供程序使用；展示用 needs_confirmation 的人话版本",
    }
    card["present_fields"] = [f for f in CARD_FIELDS if card.get(f)]
    return card


#: 判定"用户是否真的表达过这个偏好"——没说过就不能拿来当推荐理由
def _profile_signals(profile) -> dict:
    prof = profile or {}
    cons = prof.get("constraints") or {}
    edu = prof.get("education") or {}
    return {
        "interest_fit": bool(prof.get("interests")),
        "skill_fit": bool(prof.get("skills")),
        "goal_fit": bool(prof.get("goals")),
        "location_fit": bool(cons.get("preferred_country") or cons.get("preferred_city")
                             or edu.get("school_country") or edu.get("school_city")
                             or cons.get("remote") is not None),
    }


#: eligibility_reasons 里属于"我们判断不了"的措辞 → 归入"还需要确认"，不进推荐理由
_UNCERTAIN_MARKERS = ("无法判断", "未提供", "未写明", "无法量化", "不能推断", "未知")


def _why_fit(row, profile=None) -> str:
    """只写**用户真的表达过**的匹配理由；判断不了的项归到"还需要确认"。

    实测缺陷：这里曾把 `eligibility_reasons` 原文拼进来（"页面限定学历 … 画像未提供学历
    → 无法判断"），也在用户没说过任何偏好时写"与你的偏好相符"。
    """
    cats = row.get("components") or {}
    allowed = _profile_signals(profile)
    labels = {"interest_fit": "与你的兴趣方向一致",
              "skill_fit": "用的技能你已经具备",
              "location_fit": "地点/远程方式与你的偏好相符",
              "goal_fit": "与你的目标直接相关"}
    reasons = []
    for key, label in labels.items():
        if not allowed.get(key):
            continue
        try:
            if float(cats.get(key) or 0) >= 60:
                reasons.append(label)
        except (TypeError, ValueError):
            continue
    for r in (row.get("eligibility_reasons") or []):
        t = str(r)
        if not any(m in t for m in _UNCERTAIN_MARKERS):
            reasons.append(t)
    return "；".join(dict.fromkeys(reasons)) or "与你已说明的情况有交集"


def humanize_reason(text) -> str:
    """把内部推理文本变成能读的中文：去掉 Python 列表语法与内部术语。

    结构化原文仍然保留在 `needs_confirmation_details` 里，只是**展示**时不能带内部语法。
    """
    t = str(text or "")
    t = re.sub(r"\[([^\]]*)\]", lambda m: m.group(1).replace("'", "").replace('"', ""), t)
    t = t.replace(" → ", "，").replace("->", "，")
    t = t.replace("画像", "你的资料").replace("无法量化为可比较的等级", "无法换算成可比较的等级")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _uncertain_eligibility_notes(row) -> list:
    """返回 (可展示文本, 结构化原文) 两列。"""
    raws = [str(r) for r in (row.get("eligibility_reasons") or [])
            if any(m in str(r) for m in _UNCERTAIN_MARKERS)]
    return [(humanize_reason(r), r) for r in raws[:3]]


def _weekly_commitment(row):
    """投入可能是 dict（{weekly_commitment}）也可能是字符串（真实存档记录两种都有）。"""
    eff = row.get("effort")
    if isinstance(eff, dict):
        return eff.get("weekly_commitment")
    if isinstance(eff, str) and eff.strip():
        return eff.strip()
    return None


def _effort(row) -> str:
    weekly = _weekly_commitment(row)
    if weekly:
        txt = str(weekly)
        if re.search(r"\d", txt):
            return f"每周约 {txt}"
        return f"{txt}（官方未给出小时数）"
    if row.get("time_commitment"):
        return str(row["time_commitment"])
    return "官方页未写明投入强度"


def _leaves(row) -> str:
    produces = [str(p) for p in (row.get("produces") or [])]
    return "、".join(produces[:3]) if produces else "官方页未写明可留下的产出"


def _next_value(row) -> str:
    fo = row.get("future_optionality") if isinstance(row.get("future_optionality"), dict) else {}
    unlocks = [str(u.get("type")) for u in (row.get("unlocks") or []) if isinstance(u, dict)]
    if fo.get("reason"):
        return str(fo["reason"])
    if unlocks:
        return "可能打开：" + "、".join(unlocks[:2])
    return ""


def _gap_for(row, gaps, bridges) -> dict:
    """这个机会是被哪个缺口找出来的（让 Gap→Bridge 在产品上可见）。"""
    oid = row.get("id")
    for b in (bridges or []):
        if b.get("opportunity_id") == oid:
            for g in (gaps or []):
                if g.get("name") == b.get("gap") or g.get("id") == b.get("gap_id"):
                    return {"gap": g.get("name"), "type": g.get("type"),
                            "relevance": (g.get("relevance") or {}).get("relevance"),
                            "bridge_score": b.get("score")}
            return {"gap": b.get("gap"), "bridge_score": b.get("score")}
    return {}


def render_card(card) -> str:
    """把卡片渲染成用户可读文本（不是 JSON）。"""
    lines = [f"### {card.get('title')}"]
    if card.get("organization"):
        lines.append(f"*{card['organization']}*")
    body = [("为什么现在值得看", card.get("why_fit")), ("补的缺口", _render_gap(card)),
            ("投入", card.get("effort")), ("能留下什么", card.get("leaves_behind")),
            ("下一步价值", card.get("next_value"))]
    for label, value in body:
        if value:
            lines.append(f"- **{label}**：{value}")
    pw = card.get("participation") or {}
    if pw.get("label"):
        note = f"（{pw['note']}）" if pw.get("note") else ""
        lines.append(f"- **参与方式**：{pw['label']}{note}")
    act = card.get("action") or {}
    if act.get("label"):
        lines.append(f"- **建议动作**：{act['label']}（{act.get('reason', '')}）")
    if card.get("needs_confirmation"):
        lines.append(f"- **还需要确认**：{'；'.join(card['needs_confirmation'])}")
    return "\n".join(lines)


def _render_gap(card) -> str:
    g = card.get("gap_filled") or {}
    if not g or not g.get("gap"):
        return ""
    return f"你现在缺 **{g['gap']}** → 这条机会能补它"


# ---------------------------------------------------------------- 8. 最终回答骨架（含长度控制）
DEFAULT_MAIN_LIMIT = 5


def render_answer(profile, rows, gaps=None, bridges=None, portfolio=None,
                  confidence=None, max_main=DEFAULT_MAIN_LIMIT, mode="A") -> dict:
    """把整条链的结果渲染成用户最终回答（控制长度 + 置信度语气 + 精度防护）。"""
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    conf = confidence or decision_confidence(profile, rows, gaps)
    split = split_recommendations(rows)
    main = [r for r in split["recommended_real"] if r.get("zone") == "recommended_now"][:max_main]
    worth = [r for r in split["recommended_real"] if r.get("zone") == "worth_verifying"][:max_main]
    excluded = [r for r in split["recommended_real"] if r.get("zone") == "excluded"]

    blocks = {
        "confidence": {"level": conf["level"], "note": conf["note"],
                       "unknown": conf["unknown"], "reasons": conf["reasons"]},
        "main": [recommendation_card(r, profile, gaps, bridges, conf) for r in main],
        "worth_verifying": [recommendation_card(r, profile, gaps, bridges, conf) for r in worth],
        "excluded": [{"title": r.get("title"), "reason": r.get("exclusion_reason")
                      or r.get("freshness_reason")} for r in excluded],
        "self_directed": split["self_directed"],
        "allocation": format_allocation(profile, main or worth),
        "unknown": conf["unknown"],
    }
    presented = main + worth
    if str(mode).upper() == "E" or explore_focus(profile)["enabled"]:
        blocks["explore"] = explore_coverage(presented)
        blocks["technical_share"] = technical_share(presented)
    blocks["length_budget"] = {
        "main": len(blocks["main"]), "worth_verifying": len(blocks["worth_verifying"]),
        "limit": max_main,
        "note": "3–5 个主要机会 + 1 个简短 Portfolio/下一步 + 必要的 Unknown；不要写成人生规划论文",
    }
    blocks["violations"] = audit_answer(_to_text(blocks), profile, conf)
    blocks["ok"] = not blocks["violations"]
    return blocks


def _to_text(blocks) -> str:
    parts = []
    for c in blocks.get("main", []) + blocks.get("worth_verifying", []):
        parts.append(render_card(c))
    parts.append(json.dumps(blocks.get("allocation") or {}, ensure_ascii=False))
    parts.append(json.dumps(blocks.get("unknown") or [], ensure_ascii=False))
    parts.append(json.dumps(blocks.get("self_directed") or [], ensure_ascii=False))
    return "\n".join(parts)


def audit_answer(text, profile, confidence=None) -> list:
    """输出自检：伪精确 / 强结论 / 混入自建路径。空列表 = 合规。"""
    violations = []
    for hit in scan_unsupported_precision(text, profile):
        violations.append({"kind": "unsupported_precision", "detail": hit})
    level = (confidence or {}).get("level")
    forbidden = set(GLOBAL_FORBIDDEN) | set((CLAIM_WORDING.get(level) or {}).get("forbidden", ()))
    lowish = level in ("low", "medium")
    for phrase in forbidden:
        if phrase in str(text or ""):
            violations.append({"kind": "strong_claim" if lowish else "forbidden_claim",
                               "detail": phrase, "confidence": level})
    return violations


# ---------------------------------------------------------------- 9. 本轮指标
OUTPUT_METRICS = ("unsupported_precision_count", "strong_claim_with_low_confidence_count",
                  "visible_gap_bridge_rate", "visible_effort_rate",
                  "visible_evidence_output_rate", "explore_axis_count",
                  "self_directed_mixed_with_real_opportunity_count",
                  "persona_context_leakage_count")

#: 画像里"不该被其他 persona 继承"的标记字段（跨会话泄漏检测用）
LEAK_SENSITIVE_FIELDS = ("skills", "interests", "goals", "education", "experience",
                         "constraints", "career_state")


def context_leakage(profile, session_note="") -> list:
    """检测是否继承了不属于本 persona 的画像内容。

    约定：画像里带 `_session` 标记的字段才可信；`_inherited_from` 出现即视为泄漏。
    """
    leaks = []
    if (profile or {}).get("_inherited_from"):
        leaks.append({"kind": "profile_inherited",
                      "detail": str(profile["_inherited_from"])})
    for f in LEAK_SENSITIVE_FIELDS:
        v = (profile or {}).get(f)
        if isinstance(v, dict) and v.get("_inherited_from"):
            leaks.append({"kind": "field_inherited", "field": f,
                          "detail": str(v["_inherited_from"])})
    if session_note and "从上一个" in session_note:
        leaks.append({"kind": "note_mentions_inheritance", "detail": session_note[:60]})
    return leaks


def output_metrics(answers) -> dict:
    """对一组已渲染的回答统计本轮 8 个输出指标。"""
    answers = [a for a in (answers or []) if isinstance(a, dict)]
    up = sc = 0
    for a in answers:
        for v in (a.get("violations") or []):
            if v["kind"] == "unsupported_precision":
                up += 1
            if v["kind"] in ("strong_claim", "forbidden_claim"):
                sc += 1
    cards = [c for a in answers for c in (a.get("main") or []) + (a.get("worth_verifying") or [])]
    n = len(cards) or 1
    return {
        "answers": len(answers),
        "unsupported_precision_count": up,
        "strong_claim_with_low_confidence_count": sc,
        "visible_gap_bridge_rate": round(sum(1 for c in cards if c.get("gap_filled")) / n, 3),
        "visible_effort_rate": round(sum(
            1 for c in cards
            if (c.get("effort") or "").strip() and "未写明" not in (c.get("effort") or "")) / n, 3),
        "visible_evidence_output_rate": round(
            sum(1 for c in cards
                if (c.get("leaves_behind") or "").strip()
                and "未写明" not in (c.get("leaves_behind") or "")) / n, 3),
        "explore_axis_count": max([(a.get("explore") or {}).get("axis_count") or 0
                                   for a in answers] + [0]),
        "self_directed_mixed_with_real_opportunity_count": sum(
            1 for a in answers if (a.get("self_directed") and a.get("main"))),
        "persona_context_leakage_count": sum(len(a.get("leakage") or []) for a in answers),
    }


# ---------------------------------------------------------------- CLI
def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="输出适配层：置信度 / 参与措辞 / 卡片 / 探索维度 / 自检")
    ap.add_argument("--task", required=True,
                    choices=["confidence", "participation", "card", "explore", "scan", "answer"])
    ap.add_argument("--profile", help="画像 JSON")
    ap.add_argument("--rows", help="机会结果 JSON（列表或 {results:[...]}/{opportunities:[...]}）")
    ap.add_argument("--gaps", help="缺口 JSON（列表）")
    ap.add_argument("--bridges", help="桥接 JSON（列表，可含 gap 字段）")
    ap.add_argument("--category", help="参与措辞：机会类别")
    ap.add_argument("--verdict", help="参与措辞：资格判定")
    ap.add_argument("--freshness", help="参与措辞：时效状态")
    ap.add_argument("--text", help="scan：要检查的文本")
    ap.add_argument("--mode", default="A")
    args = ap.parse_args(argv)

    profile = _load(args.profile) if args.profile else {}
    rows = []
    if args.rows:
        data = _load(args.rows)
        rows = data if isinstance(data, list) else (data.get("results")
                                                    or data.get("opportunities") or [])
    gaps = _load(args.gaps) if args.gaps else []
    bridges = _load(args.bridges) if args.bridges else []

    if args.task == "confidence":
        out = decision_confidence(profile, rows, gaps)
    elif args.task == "participation":
        out = participation_wording(args.category, args.verdict, args.freshness)
    elif args.task == "card":
        out = [recommendation_card(r, profile, gaps, bridges) for r in rows]
    elif args.task == "explore":
        out = {"focus": explore_focus(profile), "coverage": explore_coverage(rows),
               "technical_share": technical_share(rows)}
    elif args.task == "scan":
        out = {"violations": scan_unsupported_precision(args.text or "", profile),
               "budget": budget_known(profile), "style": allocation_style(profile)}
    else:
        out = render_answer(profile, rows, gaps, bridges, mode=args.mode)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
