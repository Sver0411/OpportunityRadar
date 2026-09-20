#!/usr/bin/env python3
"""统一统计（§10）+ 机械独立性检查（§8）。

独立性不能只靠"记得不要引用"，所以对五个画像逐字段做**禁止词**检查：
用户原话里没说过、又被用户点名禁止出现的词，出现在画像里就算泄漏。
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import presentation as P  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output-ux")

CASES = {
    "A": "case-a-iot-undergrad",
    "B": "case-b-japan-masters",
    "C": "case-c-promotion",
    "D": "case-d-ai-switch",
    "E": "case-e-unknown",
}

#: 用户点名的禁止词（§8）：出现在某个 persona 的画像里且其原话没有 → 泄漏
FORBIDDEN = {
    "B": ["大三", "ESP32", "Python", "嵌入式"],
    "C": ["ESP32", "embedded", "Python", "嵌入式"],
    "D": ["ESP32", "embedded"],
    "E": ["后端五年", "AI 工程", "AI工程", "6 小时", "6小时", "不辞职", "Python", "ESP32", "嵌入式"],
    "A": ["不辞职", "AI 工程"],
}

BACKGROUND_FIELDS = ("skills", "interests", "education", "experience", "languages",
                     "nationality", "life_stage", "constraints", "career_state")


def background_blob(profile) -> str:
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
    for f in BACKGROUND_FIELDS:
        if f in (profile or {}):
            walk({f: profile[f]})
    return " ".join(out).lower()


def load_profile(case):
    d = os.path.join(OUT, CASES[case])
    for name in ("profile-validation.json", "profile.json"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8")), p
    return {}, "(missing)"


def load_answer(case):
    d = os.path.join(OUT, CASES[case])
    for name in ("answer-validation.json", "answer.json"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8")), p
    return {}, "(missing)"


def load_report(case):
    d = os.path.join(OUT, CASES[case])
    p = os.path.join(d, "validation_report.json")
    return (json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}), p


def main():
    leakage = []
    rows = []
    for case in ("A", "B", "C", "D", "E"):
        prof, ppath = load_profile(case)
        ans, apath = load_answer(case)
        rep, _ = load_report(case)
        blob = background_blob(prof)
        said = str(prof.get("user_input") or "").lower()
        for bad in FORBIDDEN.get(case, []):
            if bad.lower() in blob and bad.lower() not in said:
                leakage.append({"case": case, "forbidden_token": bad,
                                "profile": os.path.basename(ppath)})
        # 程序化泄漏检查（presentation.context_leakage）
        leakage += [{"case": case, "forbidden_token": f"context_leakage:{x['kind']}"}
                    for x in (P.context_leakage(prof) or [])]

        conf = (ans.get("confidence") or {}).get("level")
        # zones：优先取 answer，其次该 case 的 scored.json
        zones = ans.get("_zones") or rep.get("zones") or ans.get("zones")
        if not isinstance(zones, dict):
            sp = os.path.join(OUT, CASES[case], "scored.json")
            if os.path.exists(sp):
                zones = json.load(open(sp, encoding="utf-8")).get("zones")
        if not isinstance(zones, dict):     # C 的验证批次
            sp = os.path.join(OUT, CASES[case], "scored-validation.json")
            if os.path.exists(sp):
                zones = json.load(open(sp, encoding="utf-8")).get("zones")
        if not isinstance(zones, dict):     # 表达层对照：从已判定行的 zone 统计
            for name in ("opportunities.json", "opportunities-validation.json"):
                op = os.path.join(OUT, CASES[case], name)
                if not os.path.exists(op):
                    continue
                oo = json.load(open(op, encoding="utf-8")).get("opportunities") or []
                if oo and any(o.get("zone") for o in oo):
                    from collections import Counter
                    c = Counter(o.get("zone") for o in oo)
                    zones = {"recommended_now": c.get("recommended_now", 0),
                             "worth_verifying": c.get("worth_verifying", 0),
                             "excluded": c.get("excluded", 0)}
                break
        # verified_rate：从该 case 的机会批次直接算
        verified = rep.get("verified_rate")
        if verified is None:
            for name in ("opportunities.json", "opportunities-validation.json"):
                op = os.path.join(OUT, CASES[case], name)
                if os.path.exists(op):
                    oo = json.load(open(op, encoding="utf-8")).get("opportunities") or []
                    if oo:
                        verified = round(sum(1 for o in oo
                                             if o.get("verification_status") == "verified_official")
                                         / len(oo), 3)
                    break
        cards = (ans.get("main") or []) + (ans.get("worth_verifying") or [])
        def rate(pred):
            return round(sum(1 for c in cards if pred(c)) / len(cards), 3) if cards else None
        rows.append({
            "case": case,
            "decision_confidence": conf,
            "recommended_now": (zones or {}).get("recommended_now") if isinstance(zones, dict) else None,
            "worth_verifying": (zones or {}).get("worth_verifying") if isinstance(zones, dict) else None,
            "explore_axis_count": ((ans.get("explore") or {}).get("axis_count")
                                   or rep.get("explore_axis_count")),
            "technical_share": rep.get("technical_share"),
            "verified_rate": verified,
            # visible_* 一律从卡片直接算，避免不同 case 的 report 字段不一致
            "visible_gap_bridge_rate": rate(lambda c: bool(c.get("gap_filled"))),
            "visible_evidence_output_rate": rate(
                lambda c: (c.get("leaves_behind") or "").strip()
                and "未写明" not in (c.get("leaves_behind") or "")),
            "visible_effort_rate": rate(
                lambda c: (c.get("effort") or "").strip()
                and "未写明" not in (c.get("effort") or "")),
            "unsupported_precision_count": len([v for v in (ans.get("violations") or [])
                                                if v.get("kind") == "unsupported_precision"]),
            "strong_claim_with_low_confidence_count": len(
                [v for v in (ans.get("violations") or [])
                 if v.get("kind") in ("strong_claim", "forbidden_claim")]),
            "persona_context_leakage_count": 0,
            "self_directed_mixed_count": (len(ans.get("self_directed") or [])
                                          if ans.get("self_directed") and ans.get("main") else 0),
            "method": ("表达层对照（未重跑 gate）" if ans.get("expression_only")
                       else ("本轮独立重跑" if case in ("C", "E")
                             else "上一轮本会话内跑")),
        })

    for r in rows:
        r["persona_context_leakage_count"] = len([x for x in leakage if x["case"] == r["case"]])

    print("=== §10 统一统计 ===")
    cols = ["case", "decision_confidence", "recommended_now", "worth_verifying",
            "explore_axis_count", "verified_rate", "visible_gap_bridge_rate",
            "visible_evidence_output_rate", "visible_effort_rate",
            "unsupported_precision_count", "strong_claim_with_low_confidence_count",
            "persona_context_leakage_count", "self_directed_mixed_count", "method"]
    print(" | ".join(cols))
    for r in rows:
        print(" | ".join(str(r.get(c)) for c in cols))
    print()
    print("E 单独：technical_share =", rows[4]["technical_share"])
    print()
    print("=== §8 机械独立性检查 ===")
    print("leakage:", leakage or "通过（0 处）")
    json.dump({"unified": rows, "leakage": leakage},
              open(os.path.join(OUT, "VALIDATION_UNIFIED.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
