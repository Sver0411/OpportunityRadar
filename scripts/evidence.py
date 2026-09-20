#!/usr/bin/env python3
"""evidence.py - 主推荐的证据前置检查（V3，P0 修复）。

背景（C/D/E 真实验收）：三组运行的候选 **100% 缺 `evidence.application_status`**，
导致主推荐区名义存在、实际不可达。靠 SKILL.md 提醒 Agent"记得填"不可靠 ——
这里把它变成**结构化 precondition**：extraction 之后、gate 之前运行，缺关键证据就降级。

主推荐（actionable）需要的证据：

| 项 | 要求 |
|---|---|
| canonical source | `official_url` 非空 |
| 官方核实 | `verification_status == verified_official` |
| 当前状态证据 | `evidence.application_status = {status: explicit, source_url, verified_at}`，且 `verified_at` 在有效期内 |
| 可参与 | `application_status ∈ {open, rolling}`（evergreen/recurring 也靠它转 actionable） |

缺任何一项 → 不允许进入 actionable zone。**Match / Utility 不能绕过这一层。**

另外提供 `demotion_reason()`，明确区分两类失败：
  * `missing_evidence_structure` —— 系统没记录证据（可修：流程问题）
  * `page_cannot_confirm`        —— 官网本身无法确认（不可修：事实问题）
  * `page_not_verifiable`        —— 官网反爬/打不开（基础设施问题）
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os

import sources as SI
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: 证据有效期（天）。与 normalize_date 中 explicit_status 的窗口保持一致。
MAX_EVIDENCE_AGE_DAYS = 30

#: 表示"当前可参与"的官方状态值
PARTICIPATION_OPEN_STATUSES = ("open", "rolling")


def _age_days(value, today):
    try:
        return (today - dt.date.fromisoformat(str(value)[:10])).days
    except (TypeError, ValueError):
        return None


def application_status_evidence(opp, today=None) -> dict:
    """检查 evidence.application_status 是否完整、新鲜（不判断内容真假）。"""
    today = today or dt.date.today()
    ev = (opp.get("evidence") or {}).get("application_status") or {}
    stated = opp.get("application_status")
    age = _age_days(ev.get("verified_at"), today)
    missing = []
    if ev.get("status") != "explicit":
        missing.append("status=explicit")
    if not str(ev.get("source_url") or "").strip():
        missing.append("source_url")
    if age is None:
        missing.append("verified_at")
    elif not (0 <= age <= MAX_EVIDENCE_AGE_DAYS):
        missing.append(f"verified_at(过期 {age} 天 > {MAX_EVIDENCE_AGE_DAYS})")
    if stated is None:
        missing.append("application_status")
    present = not missing
    return {
        "present": present,
        "stated": stated,
        "verified_at": ev.get("verified_at"),
        "age_days": age,
        "source_url": ev.get("source_url"),
        "evidence_summary": ev.get("evidence_summary") or ev.get("quote"),
        "missing": missing,
        "participation_open": present and stated in PARTICIPATION_OPEN_STATUSES,
    }


def check(opp, today=None) -> dict:
    """主推荐前置检查（extraction 后、gate 前运行）。"""
    today = today or dt.date.today()
    missing = []
    if not str(opp.get("official_url") or "").strip():
        missing.append("official_url")
    if opp.get("verification_status") != "verified_official":
        missing.append("verification_status:verified_official")
    app = application_status_evidence(opp, today)
    if not app["present"]:
        missing.append("evidence.application_status(" + ",".join(app["missing"]) + ")")
    # 页面时效（≠ 机会时效）：历史/陈旧页面可用于 discovery，但**不能满足"当前可申请"证据**
    sf = SI.source_freshness(opp, today)
    if sf["source_freshness"] in ("historical", "stale"):
        missing.append(f"source_freshness:current(页面为 {sf['source_freshness']})")
    return {
        "complete": not missing,
        "missing": missing,
        "source_freshness": sf["source_freshness"],
        "source_freshness_signal": sf["signal"],
        "application_status": app,
        "participation_open": app["participation_open"],
        "checked_at": today.isoformat(),
        "max_age_days": MAX_EVIDENCE_AGE_DAYS,
    }


def demotion_reason(opp, row, evc) -> dict:
    """为什么没进 actionable zone —— 明确区分"系统忘了记"与"官网无法确认"。"""
    if evc.get("missing") and "official_url" in evc["missing"]:
        return {"code": "no_canonical_source", "kind": "process",
                "detail": "没有找到官方来源"}
    if opp.get("verification_status") != "verified_official":
        blob = " ".join(str(opp.get(k) or "") for k in ("notes", "fetch_error", "summary")).lower()
        blocked = any(k in blob for k in ("403", "401", "captcha", "cloudflare", "blocked",
                                          "timeout", "js 渲染", "js-rendered", "404", "打不开"))
        if blocked:
            return {"code": "page_not_verifiable", "kind": "infrastructure",
                    "detail": "官方页面无法读取（反爬 / JS 渲染 / 404 / 超时）"}
        return {"code": "verification_not_attempted", "kind": "process",
                "detail": "本轮没有去核实官方页面（预算/顺序问题，下一轮可补）"}
    sf = (evc.get("source_freshness") or "unknown")
    if sf in ("historical", "stale"):
        return {"code": "source_found_not_current", "kind": "fact",
                "detail": f"找到的页面不是当前信息（source_freshness={sf}）：{evc.get('source_freshness_signal','')}"}
    status = (row.get("freshness") or {}).get("status")
    if status in ("unknown", "evergreen", "recurring") and not row.get("participation_open"):
        # 页面本身无法确认"现在能参与" → 事实问题（不是我们忘了记录）
        return {"code": "page_cannot_confirm", "kind": "fact",
                "detail": f"页面无法确认当前是否可参与（freshness={status}，无参与入口证据）"}
    if not evc.get("application_status", {}).get("present"):
        return {"code": "missing_evidence_structure", "kind": "process",
                "detail": "官方页已核实但未记录当前状态证据（系统漏记，可补）"}
    if status in ("closed", "expired"):
        return {"code": "closed", "kind": "fact", "detail": "已截止/已结束"}
    if row.get("conflicts"):
        return {"code": "conflict", "kind": "fact", "detail": "时间/dealbreaker 冲突"}
    return {"code": "relevance_below_threshold", "kind": "relevance",
            "detail": "match/utility 未达门槛"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="主推荐的证据前置检查")
    ap.add_argument("--opportunity", required=True, help="单条 opportunity JSON")
    ap.add_argument("--today", default=None)
    args = ap.parse_args(argv)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    opp = json.load(open(args.opportunity, encoding="utf-8"))
    print(json.dumps(check(opp, today), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
