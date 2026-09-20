"""Apply the REAL deterministic gate (score.score_all) to the C/D/E case candidates.

Why: in the D/C/E runs the `zone` was assigned by hand. The actual gate (tightened in 59a43fb)
requires verified_official + application_status evidence + size_verified for `recommended_now`.
This script recomputes zones with score.py so a hand-written PASS cannot hide a gate violation.

Run: python3 usertests/_apply_gate.py
"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import score as S  # noqa: E402

CASES = {"D": "case-d-japan-masters", "C": "case-c-promotion", "E": "case-e-unknown"}
TODAY = dt.date(2026, 9, 20)


def opp_from_candidate(c, idx, case):
    return {
        "id": c.get("id") or f"{case}-{idx}",
        "title": c.get("title"),
        "organization": c.get("organization"),
        "primary_category": c.get("category") or "education",
        "official_url": c.get("official_url") or "",
        "discovery_url": c.get("discovery_url") or "",
        "deadline": c.get("deadline"),
        "verification_status": c.get("verification_status"),
        "remote": True,
        "effort": c.get("effort") or {},
        "prerequisites": c.get("prerequisites") or [],
        "application_status": c.get("application_status"),
        "deadline_type": c.get("deadline_type"),
        "event_end": c.get("event_end"),
        "cycle": c.get("cycle"),
        "summary": c.get("summary"),
        "notes": c.get("notes"),
        "evidence": c.get("evidence") or {},
        "outcomes": c.get("outcomes") or {},
        "produces": c.get("produces") or [],
        "tags": c.get("tags") or [],
        "secondary_categories": c.get("secondary_categories") or [],
        "country": c.get("country"),
    }


def main() -> None:
    for case, d in CASES.items():
        rec_path = os.path.join(HERE, d, "record.json")
        prof_path = os.path.join(HERE, d, "profile.json")
        if not (os.path.exists(rec_path) and os.path.exists(prof_path)):
            print(f"[Case {case}] 缺文件，跳过")
            continue
        record = json.load(open(rec_path, encoding="utf-8"))
        profile = json.load(open(prof_path, encoding="utf-8"))
        cands = record.get("candidates", [])
        opps = [opp_from_candidate(c, i, case) for i, c in enumerate(cands)]

        res = S.score_all(profile, opps, today=TODAY)
        by_id = {r.get("id"): r for r in res["results"]}
        excluded_by_id = {}
        for e in res["excluded"]:
            excluded_by_id[e.get("id")] = e.get("reason")

        missing_evidence = [c.get("title") for c in cands
                            if not (c.get("evidence") or {}).get("application_status")]
        mismatches = []
        for i, c in enumerate(cands):
            oid = opps[i]["id"]
            declared = c.get("zone")
            if oid in by_id:
                computed_zone = by_id[oid].get("zone")
                reason = by_id[oid].get("freshness_reason")
            else:
                computed_zone = "excluded"
                reason = excluded_by_id.get(oid, "")
            dem = None
            if oid in by_id:
                dem = by_id[oid].get("demotion")
            elif excluded_by_id.get(oid):
                dem = {"code": "closed_or_ineligible", "kind": "fact",
                       "detail": excluded_by_id.get(oid)}
            c["gate_computed"] = {"zone": computed_zone, "reason": reason, "demotion": dem}
            if dem:
                c["demotion"] = dem
            if declared and declared != computed_zone:
                mismatches.append({"title": c.get("title"),
                                   "declared": declared, "computed": computed_zone,
                                   "reason": reason})

        from collections import Counter
        dt_hist = Counter(str(c.get("deadline_type")) for c in cands)
        dem_hist = Counter((c.get("demotion") or {}).get("code") for c in cands
                           if c.get("demotion"))
        dem_kind = Counter((c.get("demotion") or {}).get("kind") for c in cands
                           if c.get("demotion"))
        ev_complete = sum(1 for c in cands if c.get("evidence", {}) or
                          (c.get("official_url") and c.get("application_status"))
                          and (c.get("evidence") or {}).get("application_status"))
        record["gate_computed_summary"] = {
            "today": TODAY.isoformat(),
            "deadline_type_histogram": dict(dt_hist),
            "rolling_or_evergreen": sum(1 for c in cands
                                        if str(c.get("deadline_type")) in ("rolling", "evergreen", "recurring")),
            "evidence_complete_candidates": ev_complete,
            "demotion_histogram": dict(dem_hist),
            "demotion_by_kind": dict(dem_kind),
            "recommended_now": sum(1 for c in cands
                                   if c["gate_computed"]["zone"] == "recommended_now"),
            "worth_verifying": sum(1 for c in cands
                                   if c["gate_computed"]["zone"] == "worth_verifying"),
            "excluded": sum(1 for c in cands if c["gate_computed"]["zone"] == "excluded"),
            "mismatches": mismatches,
            "missing_application_status_evidence": missing_evidence,
        }
        json.dump(record, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        s = record["gate_computed_summary"]
        print(f"[Case {case}] gate 重算: recommended={s['recommended_now']} "
              f"worth_verifying={s['worth_verifying']} excluded={s['excluded']} "
              f"| 手工标注与 gate 不一致: {len(mismatches)}")
        print(f"    缺 evidence.application_status 的候选: {len(missing_evidence)}/{len(cands)}")
        print(f"    deadline_type 分布: {dict(Counter(str(c.get('deadline_type')) for c in cands))}")
        print(f"    降级原因: {dict(Counter((c.get('demotion') or {}).get('code') for c in cands if c.get('demotion')))}")
        print(f"    降级性质(process=漏记/fact=页面无法确认/infrastructure=打不开): "
              f"{dict(Counter((c.get('demotion') or {}).get('kind') for c in cands if c.get('demotion')))}")
        for m in mismatches:
            print(f"    - {str(m['title'])[:44]}: 标注={m['declared']} → gate={m['computed']} "
                  f"({str(m['reason'])[:60]})")


if __name__ == "__main__":
    main()
