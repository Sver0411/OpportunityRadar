#!/usr/bin/env python3
"""readiness.py - 资格之外的"离真正开始还有多远"（V3）。

Eligibility 回答：我有没有资格？
Readiness 回答：我现在离真正开始还有多远？

**Readiness 不是录取概率**。禁止输出"录取率 72%"这类数字；
只输出状态（ready_now / minor_preparation / short_preparation / major_preparation /
blocked / unknown）+ 已有项 / 缺项 / 阻塞项。

判定只用确定性信息：
  * opportunity 的 prerequisites / required_materials / effort
  * profile 的 skills / experience / constraints（weekly_time、dealbreakers）
缺口一律 Unknown，不猜。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import READINESS_STATUSES  # noqa: E402


def as_list(v):
    if v in (None, "", [], {}):
        return []
    return v if isinstance(v, list) else [v]


def _tokens(text):
    # 单字母技能是真实存在的（C / R），不能按长度过滤掉
    return {t for t in "".join(
        c.lower() if c.isalnum() else " " for c in str(text or "")).split() if t}


def _hours(expr, allow_bare=False):
    """从 '6-8 h' / '~10 h/week' / '每周 15 小时' 里取**上限**小时数；无法解析返回 None。

    `allow_bare=True` 时接受裸数字：画像的 `constraints.weekly_time` 常写成 "6"（单位就是小时/周）。
    """
    import re
    s = str(expr or "").lower()
    nums = [float(x) for x in re.findall(r"(\d{1,3}(?:\.\d)?)", s)]
    if not nums:
        return None
    if not re.search(r"h\b|hour|hr|時間|小时", s):
        return max(nums) if allow_bare else None
    return max(nums)


def effort_of(opp) -> dict:
    """`effort` 允许写成对象或字符串（真实抽取结果两种都有）。"""
    eff = opp.get("effort")
    if isinstance(eff, dict):
        return eff
    if isinstance(eff, str) and eff.strip():
        return {"weekly_commitment": eff}
    return {}


def readiness(opp, profile) -> dict:
    """返回 {status, ready_items, missing_items, blockers, estimated_preparation, notes}。"""
    ready, missing, blockers, notes = [], [], [], []

    prereq = as_list(opp.get("prerequisites")) + as_list(opp.get("skills_required"))
    have_tokens = set()
    for s in as_list(profile.get("skills")):
        if isinstance(s, dict):
            have_tokens |= _tokens(s.get("name"))
        else:
            have_tokens |= _tokens(s)
    exp = profile.get("experience") or {}
    for key in ("projects", "open_source", "research", "internships", "competitions",
                "certificates", "portfolio"):
        for item in as_list(exp.get(key)):
            have_tokens |= _tokens(item)

    for p in prereq:
        pt = _tokens(p)
        if not pt:
            continue
        if pt & have_tokens:
            ready.append(f"具备：{p}")
        else:
            missing.append(f"需要补：{p}")

    for m in as_list(opp.get("required_materials")):
        mt = _tokens(m)
        if mt & have_tokens:
            ready.append(f"材料已具备：{m}")
        else:
            missing.append(f"需准备材料：{m}")

    cons = profile.get("constraints") or {}
    weekly_limit = _hours(cons.get("weekly_time"), allow_bare=True)
    need = _hours(effort_of(opp).get("weekly_commitment"))
    if weekly_limit and need and need > weekly_limit * 1.5:
        blockers.append(f"时间冲突：机会约 {need:g}h/周，你的上限约 {weekly_limit:g}h/周")
        notes.append("heavy commitment conflict：不是 Ineligible，但不能当低投入机会推荐")

    for d in as_list(profile.get("dealbreakers")):
        dt = _tokens(d)
        if not dt:
            continue
        blob = " ".join(str(opp.get(k) or "") for k in
                        ("title", "summary", "compensation", "time_commitment", "cost",
                         "notes", "remote", "country", "city"))
        if len(dt & _tokens(blob)) >= max(1, len(dt) // 2):
            blockers.append(f"触碰你的 dealbreaker：{d}")
            notes.append("dealbreaker conflict：用户明确不接受，不得进入 Recommended now")

    # 状态判定（保守）
    if blockers:
        status = "blocked"
    elif not prereq and not as_list(opp.get("required_materials")) and (weekly_limit is None or need is None):
        status = "unknown"
        notes.append("页面未写明前置要求，且画像缺少可比对信息 → 准备度未知")
    elif not missing:
        status = "ready_now"
    elif len(missing) <= 2:
        status = "minor_preparation"
    elif len(missing) <= 4:
        status = "short_preparation"
    else:
        status = "major_preparation"

    est = {"ready_now": "可以直接开始",
           "minor_preparation": "几小时到 1–2 天",
           "short_preparation": "几天到两周",
           "major_preparation": "两周以上",
           "blocked": "存在阻塞项，先解决阻塞",
           "unknown": "无法估计"}.get(status)

    return {"status": status, "ready_items": ready, "missing_items": missing,
            "blockers": blockers, "estimated_preparation": est, "notes": notes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Readiness：离真正开始还有多远（不是录取概率）")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--opportunity", required=True, help="单条 opportunity JSON 文件")
    args = ap.parse_args(argv)
    profile = json.load(open(args.profile, encoding="utf-8"))
    opp = json.load(open(args.opportunity, encoding="utf-8"))
    res = readiness(opp, profile)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
