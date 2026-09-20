#!/usr/bin/env python3
"""Persona C 的独立重跑 + extraction 完整性统计（§4-§6）。

字段缺失必须区分：present / source_absent / extraction_miss / not_applicable
—— 不能把三种情况都算成"缺失"。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gaps as GP             # noqa: E402
import graph as G             # noqa: E402
import portfolio as PF        # noqa: E402
import presentation as P      # noqa: E402
import score as SC            # noqa: E402

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output-ux", "case-c-promotion")
TODAY = dt.date(2026, 9, 21)
FIELDS = ("skills_required", "produces", "effort")


def main():
    prof = json.load(open(os.path.join(D, "profile-validation.json"), encoding="utf-8"))
    batch = json.load(open(os.path.join(D, "opportunities-validation.json"), encoding="utf-8"))
    opps = batch["opportunities"]

    res = SC.score_all(prof, opps, today=TODAY)
    rows = list(res.get("results") or []) + [{**e, "zone": "excluded"}
                                             for e in (res.get("excluded") or [])]
    gaps = GP.collect_gaps(opps, prof)
    bridges = G.gap_to_bridge_report(gaps, opps, prof)
    flat = [dict(b, gap=e["gap"]["name"]) for e in bridges for b in e["bridges"]]
    pf = PF.build_portfolio(rows, prof, bridges=flat)
    ans = P.render_answer(prof, rows, gaps, flat, portfolio=pf, mode="A")
    ans["self_directed"] = [P.self_directed_fallback(e["gap"]) for e in bridges
                            if not e["bridges"]
                            and (e["gap"].get("relevance") or {}).get("relevance")
                            in ("core_gap", "supporting_gap")]
    ans["leakage"] = P.context_leakage(prof)

    for name, data in (("scored-validation.json", {"zones": res.get("zones"), "results": rows}),
                       ("gaps-validation.json", gaps), ("bridges-validation.json", flat),
                       ("portfolio-validation.json", pf), ("answer-validation.json", ans)):
        json.dump(data, open(os.path.join(D, name), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    # ---- §5 字段覆盖：按分类统计 ----
    tally = {f: {"present": 0, "source_absent": 0, "extraction_miss": 0, "not_applicable": 0,
                 "unclassified": 0} for f in FIELDS}
    for o in opps:
        audit = o.get("extraction_audit") or {}
        for f in FIELDS:
            has = o.get(f) not in (None, [], {})
            cls = (audit.get(f) or {}).get("status")
            if has:
                tally[f]["present"] += 1
            elif cls in ("source_absent", "extraction_miss", "not_applicable"):
                tally[f][cls] += 1
            else:
                tally[f]["unclassified"] += 1

    n = len(opps)
    cards = ans["main"] + ans["worth_verifying"]
    def rate(pred):
        return round(sum(1 for c in cards if pred(c)) / len(cards), 3) if cards else None

    metrics = {
        "candidates": n,
        "zones": res.get("zones"),
        "decision_confidence": ans["confidence"]["level"],
        "unknown_signals": ans["confidence"]["unknown"],
        "field_presence_rate": {f: round(tally[f]["present"] / n, 3) for f in FIELDS},
        "field_gap_breakdown": tally,
        "visible_gap_bridge_rate": rate(lambda c: bool(c.get("gap_filled"))),
        "visible_evidence_output_rate": rate(
            lambda c: (c.get("leaves_behind") or "").strip()
            and "未写明" not in (c.get("leaves_behind") or "")),
        "visible_effort_rate": rate(
            lambda c: (c.get("effort") or "").strip() and "未写明" not in (c.get("effort") or "")),
        "unsupported_precision_count": sum(1 for v in ans["violations"]
                                           if v["kind"] == "unsupported_precision"),
        "strong_claim_with_low_confidence_count": sum(
            1 for v in ans["violations"] if v["kind"] in ("strong_claim", "forbidden_claim")),
        "self_directed_mixed_count": 0 if not ans["self_directed"] else len(ans["self_directed"]),
        "persona_context_leakage_count": len(ans["leakage"]),
        "portfolio": {"budget": pf.get("budget_hours"), "planned": pf.get("planned_hours"),
                      "conflict": pf.get("resource_conflict"),
                      "roles": pf.get("roles_present"), "dropped": len(pf.get("dropped") or [])},
        "development_gaps": [g["name"] for g in gaps
                             if (g.get("relevance") or {}).get("relevance")
                             in ("core_gap", "supporting_gap")],
    }
    json.dump(metrics, open(os.path.join(D, "validation_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print("zones:", res.get("zones"))
    print("confidence:", ans["confidence"]["level"])
    print("field_presence_rate:", metrics["field_presence_rate"])
    print("field_gap_breakdown:", json.dumps(tally, ensure_ascii=False))
    print("visible: gap_bridge=%s evidence_output=%s effort=%s" % (
        metrics["visible_gap_bridge_rate"], metrics["visible_evidence_output_rate"],
        metrics["visible_effort_rate"]))
    print("violations:", ans["violations"] or "无")
    print("portfolio:", metrics["portfolio"])
    print("development_gaps:", metrics["development_gaps"])
    print()
    for c in ans["main"]:
        print(P.render_card(c)); print()
    for c in ans["worth_verifying"]:
        pw = c.get("participation") or {}
        print(f"  · [{pw.get('label')}] {c['title'][:48]} | 缺: {c.get('needs_confirmation')}")


if __name__ == "__main__":
    main()
