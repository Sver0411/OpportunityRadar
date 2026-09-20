"""Audit the C/D/E acceptance records: gate leakage, degeneration, hallucination.

Run: python3 usertests/_audit_cases.py
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = {
    "D": "case-d-japan-masters",
    "C": "case-c-promotion",
    "E": "case-e-unknown",
}


def load(case_dir):
    return json.load(open(os.path.join(HERE, case_dir, "record.json"), encoding="utf-8"))


def main() -> None:
    for case, d in CASES.items():
        path = os.path.join(HERE, d, "record.json")
        if not os.path.exists(path):
            print(f"[Case {case}] 缺少 record.json")
            continue
        r = load(d)
        cands = r.get("candidates", [])
        included = [c for c in cands if c.get("included")]
        # 真正的"主推荐区"看 zone；没有 zone 字段时退回 included
        rec = [c for c in included if c.get("zone") == "recommended_now"] or \
              [c for c in included if not c.get("zone")]
        verify = [c for c in included if c.get("zone") == "worth_verifying"]
        checks = r.get("acceptance_checks", {})
        print(f"\n===== Case {case} · {d} =====")
        print(f"  候选 {len(cands)} / 纳入 {len(included)} / 排除 {len(cands) - len(included)}")
        print("  类别分布(纳入):", dict(Counter(c.get("category") for c in included)))
        print(f"  [分区] recommended_now={len(rec)} / worth_verifying={len(verify)}")
        print("  searches/fetches:", r.get("searches_used"), "/", r.get("fetches_used"))
        print("  保持 Unknown 的字段数:", len(r.get("fields_left_unknown", [])))

        # --- gate 泄漏检查 ---
        # gate 只针对**主推荐区**判定（worth_verifying 允许未验证，这是设计）
        no_url = [c.get("title") for c in rec if not str(c.get("official_url") or "").strip()]
        expired = [c.get("title") for c in rec if str(c.get("freshness")) in ("closed", "expired")]
        unverified = [c.get("title") for c in rec
                      if str(c.get("verification_status")) not in ("verified_official", "partially_verified")]
        print("  [gate] 主推荐缺 official_url:", no_url or "无")
        print("  [gate] 主推荐含 closed/expired:", expired or "无")
        print("  [gate] 主推荐未验证:", unverified or "无")
        ok = sum(1 for c in rec if str(c.get("verification_status")) == "verified_official")
        print(f"  [gate] 主推荐官方验证率: {ok}/{len(rec)}")

        # --- 退化检查 ---
        cats = Counter(str(c.get("category")) for c in included)
        total = sum(cats.values()) or 1
        if case == "C":
            print(f"  [退化] career(招聘) 占比: {cats.get('career', 0)}/{total}")
        if case == "E":
            trad = sum(cats.get(k, 0) for k in ("career", "competition", "education"))
            print(f"  [退化] 实习+比赛+教育 占比: {trad}/{total}")
            print("  [探索] 覆盖相邻维度:", checks.get("adjacency_dimensions_covered"))
            print("  [探索] 小赌注类型:", dict(Counter(c.get("small_bet_type") for c in included)))

        # --- V3 字段是否真的用上 ---
        used = {
            "outcomes": sum(1 for c in cands if c.get("outcomes")),
            "readiness": sum(1 for c in cands if c.get("readiness")),
            "effort": sum(1 for c in cands if c.get("effort")),
            "unlocks": sum(1 for c in cands if c.get("unlocks")),
            "career_capital": sum(1 for c in cands if c.get("career_capital")),
            "future_optionality": sum(1 for c in cands if c.get("future_optionality")),
        }
        print("  [V3] 字段使用:", used)
        print("  [checks]", checks)
        probs = r.get("problems", [])
        print(f"  [问题] 共 {len(probs)} 条:",
              dict(Counter(p.get("severity") for p in probs)))


if __name__ == "__main__":
    main()
