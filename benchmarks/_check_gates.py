"""Generate benchmarks/gates.json from the round-2 metrics + declared known failures.

Kept in-repo so the gate numbers can be regenerated and audited (used by
tests/test_benchmark_consistency.py). Run: python3 benchmarks/_check_gates.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
THRESHOLDS = {
    "expired_leakage_max": 0,
    "unverified_actionable_leakage_max": 0,
    "final_verification_pct_min": 80,
    "radar_only_useful_min": 2,
}


def main() -> None:
    metrics = json.load(open(os.path.join(HERE, "_metrics-v2.json"), encoding="utf-8"))
    gates = {}
    for pid, row in metrics.items():
        g = row.get("gates", {})
        rec_n = g.get("rec_n", 0)
        gates[pid] = {
            "expired_leakage": g.get("rec_expired", 0),
            "unverified_actionable_leakage": g.get("rec_unverified", 0),
            "final_verification_pct": round(100.0 * g.get("rec_verified", 0) / rec_n) if rec_n else 0,
            "radar_only_useful": row.get("radar_only_useful", 0),
            "recommended_now": rec_n,
        }

    # PASS / FAIL per gate
    results = {}
    failures = []
    for pid, g in gates.items():
        per = {}
        checks = [
            ("expired_leakage", g["expired_leakage"] <= THRESHOLDS["expired_leakage_max"], "<="),
            ("unverified_actionable_leakage",
             g["unverified_actionable_leakage"] <= THRESHOLDS["unverified_actionable_leakage_max"], "<="),
            ("final_verification_pct",
             g["final_verification_pct"] >= THRESHOLDS["final_verification_pct_min"], ">="),
            ("radar_only_useful", g["radar_only_useful"] >= THRESHOLDS["radar_only_useful_min"], ">="),
        ]
        for name, ok, op in checks:
            per[name] = {"value": g[name if name != "final_verification_pct" else "final_verification_pct"],
                         "threshold": THRESHOLDS[name + ("_min" if op == ">=" else "_max")],
                         "operator": op, "status": "PASS" if ok else "FAIL"}
            if not ok:
                failures.append({"persona": pid, "gate": name, **per[name]})
        results[pid] = per

    # 标注哪些失败后来已被解决（历史数值不改；关闭需要实测通过值，由测试校验）
    known_path = os.path.join(HERE, "known_failures.json")
    resolved = set()
    if os.path.exists(known_path):
        kd = json.load(open(known_path, encoding="utf-8"))
        resolved = {(f["persona"], f["gate"]) for f in kd.get("resolved_failures", [])}
    for f in failures:
        f["status"] = "resolved" if (f["persona"], f["gate"]) in resolved else "active"
    json.dump({"thresholds": THRESHOLDS, "gates": gates, "results": results,
               "all_pass": not failures, "failures": failures},
              open(os.path.join(HERE, "gates.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("gates.json written; all_pass =", not failures)
    for f in failures:
        print("  FAIL:", f["persona"], f["gate"], f["value"], f["operator"], f["threshold"])


if __name__ == "__main__":
    main()
