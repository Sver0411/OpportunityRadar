#!/usr/bin/env python3
"""utility.py - Personal Utility：值不值得把资源投入进去（V3）。

三个概念必须分离：
  Match     → 适不适合
  Priority  → 急不急
  Utility   → **值不值得现在投入资源**

内部可以计算数值，但对用户只输出 High / Medium / Low（+ Unknown）并给理由。
**禁止输出 "83.7214 分" 这种伪精确分数**，也禁止输出录取概率。

至少考虑：eligibility、goal fit、readiness、outcome value、effort、cost、
time-to-value、future optionality、trust、urgency。
"""

from __future__ import annotations

import argparse
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from readiness import effort_of, readiness  # noqa: E402

LEVEL_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.3, "unknown": 0.5, None: 0.5}

#: 权重（内部使用，不展示）
FACTOR_WEIGHTS = {
    "eligibility": 0.20, "goal_fit": 0.16, "readiness": 0.14, "outcome_value": 0.16,
    "effort_fit": 0.10, "cost_fit": 0.06, "time_to_value": 0.06,
    "optionality": 0.06, "trust": 0.06,
}

ELIGIBILITY_SCORE = {
    "Eligible": 1.0, "Probably Eligible": 0.75, "Unknown": 0.5,
    "Probably Ineligible": 0.2, "Ineligible": 0.0, None: 0.5,
}
READINESS_SCORE = {
    "ready_now": 1.0, "minor_preparation": 0.8, "short_preparation": 0.6,
    "major_preparation": 0.35, "blocked": 0.05, "unknown": 0.5, None: 0.5,
}


def _level(v):
    return LEVEL_SCORE.get(str(v or "").lower(), 0.5)


def _goal_fit(opp, profile) -> float:
    """用 outcomes 与用户目标维度的重合度估计（没有 outcomes 时按 GOAL_TO_VALUE_DIM 退化）。"""
    outcomes = opp.get("outcomes") or {}
    goals = profile.get("goals") or []
    dims = set()
    try:
        from common import GOAL_TO_VALUE_DIM
        for g in goals:
            if isinstance(g, dict):
                dims |= set(GOAL_TO_VALUE_DIM.get(g.get("type"), []))
    except Exception:
        pass
    if not dims:
        return 0.5
    if not outcomes:
        return 0.5
    hits = [ _level(outcomes.get(d)) for d in dims if d in outcomes ]
    return round(sum(hits) / len(hits), 3) if hits else 0.5


def _outcome_value(opp) -> float:
    outcomes = opp.get("outcomes") or {}
    if not outcomes:
        return 0.5
    vals = [_level(v) for v in outcomes.values() if v]
    return round(sum(vals) / len(vals), 3) if vals else 0.5


def _effort_fit(opp, profile) -> tuple:
    cons = profile.get("constraints") or {}
    eff = effort_of(opp)
    weekly = str(eff.get("weekly_commitment") or "")
    limit = str(cons.get("weekly_time") or "")
    import re
    def hours(s):
        n = [float(x) for x in re.findall(r"(\d{1,3}(?:\.\d)?)", s)]
        if not n or not re.search(r"h|hour|hr|時間|小时", s.lower()):
            return None
        return max(n)
    need, cap = hours(weekly), hours(limit)
    if need and cap:
        if need <= cap:
            return 1.0, None
        if need <= cap * 1.5:
            return 0.5, f"略超你的时间上限（{need:g}h vs {cap:g}h）"
        return 0.15, f"明显超出时间上限（{need:g}h vs {cap:g}h）"
    return 0.5, None

def _cost_fit(opp, profile) -> tuple:
    pref_paid = (profile.get("decision_preferences") or {}).get("prefer_paid")
    cost = opp.get("cost")
    if not isinstance(cost, dict):
        cost = {} if cost in (None, "") else {"participation_cost": str(cost)}
    blob = " ".join(str(v or "") for v in cost.values()).lower()
    if not blob and opp.get("compensation") is None:
        return 0.5, None
    paid = ("paid" in str(opp.get("compensation") or "").lower()
            or any(k in blob for k in ("stipend", "salary", "funded", "津贴", "薪")))
    free = ("free" in blob or "0" in blob or "免费" in blob)
    if pref_paid == "high":
        return (0.9, None) if paid else (0.4, "你偏好有报酬，但这条没有明确报酬信息")
    if free:
        return 1.0, None
    return 0.6, None


def personal_utility(opp, profile, scored_row=None) -> dict:
    """返回 {band, factors, reasons, readiness}。scored_row 可传入 score.py 结果行。"""
    row = scored_row or {}
    rd = readiness(opp, profile)
    verdict = row.get("eligibility_verdict") or opp.get("eligibility", {}).get("verdict")
    trust = row.get("components", {}).get("trust") if row.get("components") else None
    trust_score = (trust / 100.0) if isinstance(trust, (int, float)) else 0.5
    urgency = row.get("urgency")
    urgency_score = (urgency / 100.0) if isinstance(urgency, (int, float)) else 0.5

    effort_score, effort_note = _effort_fit(opp, profile)
    cost_score, cost_note = _cost_fit(opp, profile)
    ttv = str(opp.get("time_to_value") or "").lower()
    ttv_score = {"immediate": 1.0, "weeks": 0.8, "months": 0.6, "long_term": 0.45}.get(ttv, 0.5)
    opt = (opp.get("future_optionality") or {}).get("level")
    factors = {
        "eligibility": ELIGIBILITY_SCORE.get(verdict, 0.5),
        "goal_fit": _goal_fit(opp, profile),
        "readiness": READINESS_SCORE.get(rd["status"], 0.5),
        "outcome_value": _outcome_value(opp),
        "effort_fit": effort_score,
        "cost_fit": cost_score,
        "time_to_value": ttv_score,
        "optionality": _level(opt),
        "trust": round(trust_score, 3),
    }
    total = sum(FACTOR_WEIGHTS[k] * v for k, v in factors.items())
    # urgency 作为小幅调节（不单独成维度，避免"急的就值得"）
    total = min(1.0, total * (0.95 + 0.10 * urgency_score))

    if rd["status"] == "blocked" or verdict == "Ineligible":
        band = "low"
    elif total >= 0.72:
        band = "high"
    elif total >= 0.52:
        band = "medium"
    else:
        band = "low"
    # 只有"真的判断不了"才给 unknown：存在阻塞或明确不符合资格时，结论是明确的 low
    if (not opp.get("outcomes") and verdict in (None, "Unknown")
            and rd["status"] != "blocked" and verdict != "Ineligible"):
        band = "unknown"

    reasons = []
    if band == "high":
        reasons.append("资格与准备度都支撑现在开始，且产出/未来通道明确")
    elif band == "medium":
        reasons.append("值得考虑，但有一项成本或不确定性需要先确认")
    elif band == "low":
        reasons.append("当前不建议优先投入：存在阻塞、资格不符或投入产出不匹配")
    else:
        reasons.append("信息不足，无法判断投入价值")
    for note in (effort_note, cost_note):
        if note:
            reasons.append(note)
    for b in rd.get("blockers", []):
        reasons.append(b)
    if rd.get("missing_items"):
        clean = [re.sub(r"^(需要补|需准备材料)：", "", m) for m in rd["missing_items"][:3]]
        reasons.append("需补：" + "、".join(clean))

    return {"band": band, "factors": factors, "internal_score": round(total, 4),
            "reasons": reasons, "readiness": rd}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Personal Utility（只输出 High/Medium/Low + 理由）")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--opportunity", required=True)
    ap.add_argument("--scored", help="score.py 的输出 JSON（可选，用于取 verdict/trust/urgency）")
    args = ap.parse_args(argv)
    profile = json.load(open(args.profile, encoding="utf-8"))
    opp = json.load(open(args.opportunity, encoding="utf-8"))
    row = {}
    if args.scored:
        data = json.load(open(args.scored, encoding="utf-8"))
        for r in data.get("results", []):
            if r.get("id") == opp.get("id"):
                row = r
                break
    res = personal_utility(opp, profile, row)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
