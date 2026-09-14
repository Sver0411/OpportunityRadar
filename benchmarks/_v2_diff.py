"""Round-2 diff helpers: per-persona overlap between bare and radar lists."""
import json
import re
import sys


def norm(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())[:60]


keys = json.load(open("benchmarks/_blind-keys-v2.json", encoding="utf-8"))
sc = json.load(open("benchmarks/judge-scores-v2.json", encoding="utf-8"))["personas"]

for pid in ["iot-embedded", "design"]:
    mapping = keys[pid]
    mode2lab = {v: k for k, v in mapping.items()}
    blind = json.load(open(f"benchmarks/runs/{pid}/blind-v2.json", encoding="utf-8"))
    out = {}
    for mode in ("bare", "opportunity-radar"):
        lab = mode2lab[mode]
        s = {x["item_id"]: x for x in sc[pid][lab]}
        out[mode] = []
        for it in blind["lists"][lab]:
            v = s.get(it["item_id"], {})
            useful = (v.get("relevance", 0) >= 2 and v.get("trust", 0) >= 2
                      and v.get("actionability", 0) >= 2)
            out[mode].append({"title": it["title"], "useful": useful,
                              "trust": v.get("trust"), "elig": v.get("eligibility"),
                              "rel": v.get("relevance"), "nov": v.get("novelty"),
                              "comment": (v.get("comment") or "")[:120],
                              "zone": it.get("zone"), "url": it.get("official_url")})
    b_titles = {norm(x["title"]) for x in out["bare"]}
    r_titles = {norm(x["title"]) for x in out["opportunity-radar"]}
    print(f"\n########## {pid} ##########")
    print(f"bare n={len(out['bare'])} useful={sum(x['useful'] for x in out['bare'])} | "
          f"radar n={len(out['opportunity-radar'])} "
          f"useful={sum(x['useful'] for x in out['opportunity-radar'])}")
    print("\n-- RADAR items --")
    for x in out["opportunity-radar"]:
        flag = "USEFUL" if x["useful"] else "not-useful"
        print(f"  [{flag:<10}] trust={x['trust']} elig={x['elig']} rel={x['rel']} zone={x['zone']} "
              f":: {str(x['title'])[:58]}")
        if not x["useful"]:
            print(f"               -> {x['comment']}")
    print("\n-- BARE-only useful (radar missed) --")
    for x in out["bare"]:
        if x["useful"] and norm(x["title"]) not in r_titles:
            print(f"  - {str(x['title'])[:70]} (trust={x['trust']} nov={x['nov']})")
    print("\n-- BOTH useful --")
    for x in out["opportunity-radar"]:
        if x["useful"] and norm(x["title"]) in b_titles:
            print(f"  - {str(x['title'])[:70]}")
