"""Compute round-2 benchmark metrics + hard quality gates (temporary helper)."""
import json
import re
import statistics as st

DIMS = ("relevance", "eligibility", "trust", "novelty", "actionability")


def norm(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())[:60]


keys = json.load(open("benchmarks/_blind-keys-v2.json", encoding="utf-8"))
sc = json.load(open("benchmarks/judge-scores-v2.json", encoding="utf-8"))["personas"]
v1 = json.load(open("benchmarks/_metrics.json", encoding="utf-8"))["personas"]

rows = {}
for pid, mapping in keys.items():
    mode2lab = {v: k for k, v in mapping.items()}
    blind = json.load(open(f"benchmarks/runs/{pid}/blind-v2.json", encoding="utf-8"))
    per = {}
    for mode in ("bare", "opportunity-radar"):
        lab = mode2lab[mode]
        items = blind["lists"][lab]
        s = {x["item_id"]: x for x in sc[pid][lab]}
        useful = sum(1 for it in items
                     if s.get(it["item_id"], {}).get("relevance", 0) >= 2
                     and s.get(it["item_id"], {}).get("trust", 0) >= 2
                     and s.get(it["item_id"], {}).get("actionability", 0) >= 2)
        per[mode] = dict(
            n=len(items), useful=useful,
            avg_rel=round(st.mean([s.get(i["item_id"], {}).get("relevance", 0) for i in items] or [0]), 2),
            avg_nov=round(st.mean([s.get(i["item_id"], {}).get("novelty", 0) for i in items] or [0]), 2),
            avg_act=round(st.mean([s.get(i["item_id"], {}).get("actionability", 0) for i in items] or [0]), 2),
        )

    lab_r, lab_b = mode2lab["opportunity-radar"], mode2lab["bare"]
    b_keys = set()
    for it in blind["lists"][lab_b]:
        b_keys.add(norm(it["title"]))
        if it.get("official_url"):
            b_keys.add(norm(it["official_url"].split("//")[-1]))
    s_r = {x["item_id"]: x for x in sc[pid][lab_r]}
    ro = [it["title"] for it in blind["lists"][lab_r]
          if s_r.get(it["item_id"], {}).get("relevance", 0) >= 2
          and s_r.get(it["item_id"], {}).get("trust", 0) >= 2
          and s_r.get(it["item_id"], {}).get("actionability", 0) >= 2
          and norm(it["title"]) not in b_keys
          and norm((it.get("official_url") or "").split("//")[-1]) not in b_keys]

    radar = json.load(open(f"benchmarks/runs/{pid}/opportunity-radar.json", encoding="utf-8"))
    recs = [r for r in radar["results"] if r.get("zone") == "recommended_now"]
    allr = radar["results"]
    gates = dict(
        rec_n=len(recs),
        rec_expired=sum(1 for r in recs if r.get("freshness") in ("closed", "expired")),
        rec_unverified=sum(1 for r in recs if not str(r.get("official_url") or "").strip()),
        rec_verified=sum(1 for r in recs if r.get("verification_status") == "verified_official"),
        zones={z: sum(1 for r in allr if r.get("zone") == z)
               for z in ("recommended_now", "worth_verifying", "excluded")},
        excluded_total=len(radar.get("excluded", [])),
    )
    rows[pid] = dict(per, radar_only_useful=len(ro), radar_only_titles=ro[:6], gates=gates)

print("=== Persona v1 -> v2 ===")
for pid, r in rows.items():
    b1, o1 = v1[pid]["bare"], v1[pid]["opportunity-radar"]
    b2, o2 = r["bare"], r["opportunity-radar"]
    g = r["gates"]
    print(f"{pid:<14} bare  useful {b1['useful']}/{b1['n']} -> {b2['useful']}/{b2['n']}")
    print(f"{'':<14} radar useful {o1['useful']}/{o1['n']} -> {o2['useful']}/{o2['n']}")
    print(f"{'':<14} radar-only {v1[pid]['radar_only_useful']} -> {r['radar_only_useful']}")
    print(f"{'':<14} rec_now={g['rec_n']} verified={g['rec_verified']} "
          f"expired_leak={g['rec_expired']} unverified_leak={g['rec_unverified']} "
          f"zones={g['zones']} excluded={g['excluded_total']}")
    print(f"{'':<14} radar-only titles: {r['radar_only_titles'][:4]}")

json.dump(rows, open("benchmarks/_metrics-v2.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nwritten benchmarks/_metrics-v2.json")
