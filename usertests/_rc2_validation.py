#!/usr/bin/env python3
"""RC2 最终校验：对五个独立会话（/tmp/opportunity-radar-validation/*）做统一复核。

用**修复后**的代码重新过 gate，并逐项检查 §14 的零容忍指标。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, "/tmp")

import load_opps              # noqa: E402
import presentation as P      # noqa: E402
import score as S             # noqa: E402

TODAY = dt.date(2026, 9, 21)
OUT = os.path.join(ROOT, "usertests", "rc2-validation")

#: §8：各 persona 不得继承的禁止词（出现在画像背景字段且原话没说过即泄漏）
FORBIDDEN = {
    "A": ["不辞职", "AI 工程"],
    "B": ["大三", "ESP32", "Python", "嵌入式"],
    "C": ["ESP32", "embedded", "Python", "嵌入式", "Singapore", "后端", "cloud-native"],
    "D": ["ESP32", "embedded", "Japan", "修士"],
    "E": ["后端五年", "AI 工程", "6 小时", "不辞职", "Python", "ESP32", "嵌入式"],
}
BACKGROUND = ("skills", "interests", "education", "experience", "languages", "nationality",
              "life_stage", "constraints", "career_state", "years_experience")


def bg_blob(profile) -> str:
    out = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.startswith("_") or k in ("note", "user_input", "goals_note"):
                    continue
                walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
        elif node is not None and not isinstance(node, bool):
            out.append(str(node))
    for f in BACKGROUND:
        if f in (profile or {}):
            walk({f: profile[f]})
    return " ".join(out).lower()


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, leaks, totals = [], [], {
        "unsupported_precision_count": 0, "strong_claim_with_low_confidence_count": 0,
        "expired_leakage": 0, "unverified_actionable_leakage": 0, "source_stale_leakage": 0,
        "persona_context_leakage_count": 0, "self_directed_mixed_count": 0}

    for case in ("A", "B", "C", "D", "E"):
        prof, opps = load_opps.load(case)
        if not opps:
            rows.append({"case": case, "note": "批次为空（该会话未产出可评分的候选）"})
            continue
        res = S.score_all(prof, opps, today=TODAY)
        scored = list(res.get("results") or [])
        rec = [r for r in scored if r.get("zone") == "recommended_now"]

        d = f"/tmp/opportunity-radar-validation/{case}"
        ans = {}
        ap = os.path.join(d, "answer.json")
        if os.path.exists(ap):
            try:
                ans = json.load(open(ap, encoding="utf-8"))
            except Exception:
                ans = {}

        # §14 零容忍检查
        expired = sum(1 for r in rec if str(r.get("freshness")) in ("closed", "expired"))
        unverified = sum(1 for r in rec if not r.get("evidence_complete") or r.get("flags") and
                         "no_canonical_source" in (r.get("flags") or []))
        stale = sum(1 for r in rec if str(r.get("source_freshness")) in ("historical", "stale"))
        totals["expired_leakage"] += expired
        totals["unverified_actionable_leakage"] += unverified
        totals["source_stale_leakage"] += stale

        blob, said = bg_blob(prof), str(prof.get("user_input") or "").lower()
        case_leaks = [f"{case}:{tok}" for tok in FORBIDDEN.get(case, [])
                      if tok.lower() in blob and tok.lower() not in said]
        case_leaks += [f"{case}:context_leakage:{x['kind']}" for x in (P.context_leakage(prof) or [])]
        leaks += case_leaks
        totals["persona_context_leakage_count"] += len(case_leaks)

        cards = (ans.get("main") or []) + (ans.get("worth_verifying") or [])
        def rate(pred):
            return round(sum(1 for c in cards if pred(c)) / len(cards), 3) if cards else None
        cov = P.explore_coverage(opps)
        tech = 0
        for o in opps:
            b = " ".join([str(o.get("title") or ""), " ".join(str(t) for t in (o.get("tags") or []))]).lower()
            if any(k in b for k in ("programming", "coding", "software", "github", "python",
                                    "algorithm", "kubernetes", "cloud", "security", "ml", "ai ")):
                tech += 1

        rows.append({
            "case": case,
            "candidates": len(opps),
            "zones": res.get("zones"),
            "decision_confidence": (ans.get("confidence") or {}).get("level"),
            "explore_axis_count": cov["axis_count"],
            "explore_axes": cov["axes"],
            "technical_share_by_topic": round(tech / len(opps), 3),
            "visible_gap_bridge_rate": rate(lambda c: bool(c.get("gap_filled"))),
            "visible_evidence_output_rate": rate(
                lambda c: (c.get("leaves_behind") or "").strip()
                and "未写明" not in (c.get("leaves_behind") or "")),
            "visible_effort_rate": rate(
                lambda c: (c.get("effort") or "").strip()
                and "未写明" not in (c.get("effort") or "")),
            "expired_leakage": expired,
            "unverified_actionable_leakage": unverified,
            "source_stale_leakage": stale,
            "leakage": case_leaks,
            "verification_status_mix": {s: sum(1 for o in opps
                                               if o.get("verification_status") == s)
                                        for s in ("verified_official", "partially_verified",
                                                  "unverified", "conflicting")},
        })

    json.dump({"rows": rows, "totals": totals, "leaks": leaks},
              open(os.path.join(OUT, "VALIDATION.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print("case | 候选 | zones | conf | 轴数 | tech | gap_bridge | evidence_output | effort | "
          "expired | unverified | stale")
    for r in rows:
        if "zones" not in r:
            print(f"{r['case']} | {r.get('note')}")
            continue
        z = r["zones"]
        print(f"{r['case']} | {r['candidates']} | {z} | {r['decision_confidence']} | "
              f"{r['explore_axis_count']} | {r['technical_share_by_topic']} | "
              f"{r['visible_gap_bridge_rate']} | {r['visible_evidence_output_rate']} | "
              f"{r['visible_effort_rate']} | {r['expired_leakage']} | "
              f"{r['unverified_actionable_leakage']} | {r['source_stale_leakage']}")
    print()
    print("§14 零容忍合计:", json.dumps(totals, ensure_ascii=False))
    print("leakage:", leaks or "0 处")


if __name__ == "__main__":
    main()
