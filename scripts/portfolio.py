#!/usr/bin/env python3
"""portfolio.py - Opportunity Portfolio（V3 P1 ②）。

Portfolio 不是新的机会类别，而是**对用户有限时间与资源的一组配置**。

角色（候选，不是每次都要出现）：
    now / bridge / low_cost / high_upside / long_term / explore

两条硬纪律：
  1. **资源约束**：选中机会的每周投入之和不得超过画像的 `weekly_time`；
     超出时必须丢弃低优先项并记录 —— `portfolio_resource_conflict_rate` 必须为 0。
  2. **禁止为凑栏目塞弱机会**：角色不达标就不出现；不做 Top-N 堆砌。
另外不替用户做人生决定：只给"如果你优先 X → A+B / 如果 Y → A+C"的对照。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: 角色优先级（越小越先被保留）
ROLE_ORDER = ("bridge", "now", "high_upside", "low_cost", "long_term", "explore")
#: 低投入阈值（每周小时）
LOW_COST_HOURS = 2.0


def _hours(value, allow_bare=True):
    s = str(value or "").lower()
    nums = [float(x) for x in re.findall(r"(\d{1,3}(?:\.\d)?)", s)]
    if not nums:
        return None
    if not re.search(r"h\b|hour|hr|時間|小时|每周|week", s):
        return max(nums) if allow_bare else None
    return max(nums)


def weekly_hours(row) -> float | None:
    """从 opportunity/结果行里估算每周投入小时数（未知返回 None）。"""
    eff = row.get("effort")
    if isinstance(eff, dict):
        h = _hours(eff.get("weekly_commitment"))
        if h is None and eff.get("estimated_hours") is not None:
            try:
                h = float(eff["estimated_hours"])
            except (TypeError, ValueError):
                h = None
    elif isinstance(eff, str):
        h = _hours(eff)
    else:
        h = None
    if h is None:
        h = _hours(row.get("time_commitment"))
    return h


def _level(value):
    return str(value or "").lower()


def assign_roles(row, bridge_ids=None) -> list:
    """给一条机会分配角色（可多个；不达标就不分配）。"""
    roles = []
    oid = row.get("id")
    if bridge_ids and oid in bridge_ids:
        roles.append("bridge")
    if row.get("zone") == "recommended_now":
        roles.append("now")
    hours = weekly_hours(row)
    if hours is not None and hours <= LOW_COST_HOURS:
        roles.append("low_cost")
    fo = row.get("future_optionality")
    fo_level = (fo or {}).get("level") if isinstance(fo, dict) else fo
    outcomes = row.get("outcomes") or {}
    strong_outcome = any(_level(v) == "high" for v in outcomes.values()) if outcomes else False
    if _level(fo_level) == "high" or (row.get("small_bet_type") == "high_upside") or \
            (strong_outcome and str(row.get("time_to_value") or "") in ("months", "long_term")):
        roles.append("high_upside")
    if str(row.get("time_to_value") or "") in ("months", "long_term") or \
            (bridge_ids and oid in bridge_ids):
        roles.append("long_term")
    if row.get("layer") == "explore" or (row.get("novelty") or 0) >= 70:
        roles.append("explore")
    return [r for r in ROLE_ORDER if r in roles]


def build_portfolio(rows, profile=None, bridges=None, budget_hours=None) -> dict:
    """在资源约束下构建 Portfolio。rows 为 score.py 的结果行（含 zone/utility/match）。"""
    profile = profile or {}
    if budget_hours is None:
        budget_hours = _hours((profile.get("constraints") or {}).get("weekly_time"))
    bridge_ids = set()
    for b in (bridges or []):
        if isinstance(b, dict) and b.get("opportunity_id"):
            bridge_ids.add(b["opportunity_id"])

    candidates = []
    for r in rows or []:
        if not isinstance(r, dict) or r.get("zone") == "excluded":
            continue
        roles = assign_roles(r, bridge_ids)
        if not roles:
            continue
        hours = weekly_hours(r)
        candidates.append({"opportunity_id": r.get("id"), "title": r.get("title"),
                           "category": r.get("primary_category"),
                           "zone": r.get("zone"), "utility": r.get("utility"),
                           "match": r.get("match_score"), "roles": roles,
                           "primary_role": roles[0], "weekly_hours": hours,
                           "hours_known": hours is not None,
                           "official_url": r.get("official_url")})

    # 资源约束下的贪心选择：角色优先 → utility → match
    util_rank = {"high": 0, "medium": 1, "low": 2, "unknown": 3, None: 3}
    candidates.sort(key=lambda c: (ROLE_ORDER.index(c["primary_role"]),
                                   util_rank.get(c["utility"], 3),
                                   -(c["match"] or 0)))
    selected, dropped, planned = [], [], 0.0
    for c in candidates:
        h = c["weekly_hours"] if c["hours_known"] else 0.0
        if budget_hours is not None and planned + h > budget_hours + 1e-9:
            dropped.append({**c, "dropped_reason": f"超出每周预算（累计 {planned:g}h + {h:g}h > {budget_hours:g}h）"})
            continue
        selected.append(c)
        planned += h

    roles_present = {r for c in selected for r in c["roles"]}   # 全部角色，不是只看主角色
    cats = {str(c["category"]) for c in selected}
    unknown_hours = sum(1 for c in selected if not c["hours_known"])

    # 不替用户做决定：给出对照方案而不是单一答案
    alternatives = []
    if len(selected) >= 3:
        by_role = {r: [c for c in selected if c["primary_role"] == r] for r in ROLE_ORDER}
        cap = [c for c in selected if {"bridge", "high_upside"} & set(c["roles"])]
        learn = [c for c in selected if {"low_cost", "explore"} & set(c["roles"])]
        if cap and learn:
            alternatives.append({"if_priority": "升职 / 职业资本", "combo": [c["opportunity_id"] for c in cap[:2]]})
            alternatives.append({"if_priority": "转方向 / 学习", "combo": [c["opportunity_id"] for c in learn[:2]]})

    return {
        "budget_hours": budget_hours,
        "planned_hours": round(planned, 2),
        # 预算未知时**不能**报成"无冲突"：冲突与否未知
        "resource_conflict": (None if budget_hours is None
                              else bool(planned > budget_hours + 1e-9)),
        "budget_unknown": budget_hours is None,
        "items": selected,
        "dropped": dropped,
        "roles_present": [r for r in ROLE_ORDER if r in roles_present],
        "diversity": {"roles": len(roles_present), "categories": len(cats)},
        "unknown_hours_items": unknown_hours,
        "alternatives": alternatives,
        "note": "；".join(x for x in (
            "每周可用时间未知 → 无法校验资源约束，请先确认 constraints.weekly_time"
            if budget_hours is None else "",
            ("部分机会未写明每周投入，未计入总和（已在 unknown_hours_items 标注）"
             if unknown_hours else "")) if x),
    }


def metrics(portfolios) -> dict:
    """P1 指标：资源冲突率必须为 0。"""
    if not portfolios:
        return {}
    known = [p for p in portfolios if p.get("budget_hours") is not None]
    conflicts = sum(1 for p in known if p.get("resource_conflict"))
    return {
        "portfolios": len(portfolios),
        # 只统计**预算已知**的组合；预算未知的不算"无冲突"
        "portfolios_with_known_budget": len(known),
        "portfolio_resource_conflict_rate": (round(conflicts / len(known), 3) if known else None),
        "portfolio_diversity_avg_roles": round(
            sum(p["diversity"]["roles"] for p in portfolios) / len(portfolios), 2),
        "portfolio_diversity_avg_categories": round(
            sum(p["diversity"]["categories"] for p in portfolios) / len(portfolios), 2),
        "dropped_for_budget_total": sum(len(p["dropped"]) for p in portfolios),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="在资源约束下构建 Opportunity Portfolio")
    ap.add_argument("--scored", required=True, help="score.py 输出 JSON")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--bridges", help="gap→bridge 报告 JSON（可选）")
    ap.add_argument("--budget-hours", type=float, default=None)
    args = ap.parse_args(argv)
    scored = json.load(open(args.scored, encoding="utf-8"))
    profile = json.load(open(args.profile, encoding="utf-8"))
    bridges = []
    if args.bridges:
        data = json.load(open(args.bridges, encoding="utf-8"))
        for entry in (data if isinstance(data, list) else data.get("report", [])):
            bridges.extend(entry.get("bridges") or [])
    p = build_portfolio(scored.get("results", []), profile, bridges, args.budget_hours)
    print(json.dumps({"portfolio": p, "metrics": metrics([p])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
