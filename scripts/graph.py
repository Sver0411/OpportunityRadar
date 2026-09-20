#!/usr/bin/env python3
"""graph.py - Opportunity Graph：一个机会完成后产生什么、打开什么（V3）。

核心：
  produces（成果） → unlocks（后续机会类型 / 真实机会） → goal_contribution（对哪个目标有贡献）

纪律（避免新幻觉源）：
  * `unlocks[].opportunity_id` **只在已发现真实机会时填写**；未发现必须 null，用 `type` 表达类型
  * gap → bridge：优先推荐**真实的学习型机会**（开源 issue、真实项目、社群），不是课程列表
  * 不预测结果，只描述"完成 A 之后通常能获得什么通道"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def as_list(v):
    if v in (None, "", [], {}):
        return []
    return v if isinstance(v, list) else [v]


def tokens(text):
    return {t for t in "".join(
        c.lower() if c.isalnum() else " " for c in str(text or "")).split() if len(t) > 1}


def _hours(expr):
    s = str(expr or "").lower()
    nums = [float(x) for x in re.findall(r"(\d{1,3}(?:\.\d)?)", s)]
    if not nums or not re.search(r"h\b|hour|hr|時間|小时", s):
        return None
    return max(nums)


def build_graph(opps) -> dict:
    """把 opportunities 组装成 graph：节点 + 已发现的真实后续链接。"""
    nodes, edges = [], []
    by_id = {o.get("id"): o for o in opps if isinstance(o, dict)}
    cat_index = {}
    for o in opps:
        if not isinstance(o, dict):
            continue
        for tag in as_list(o.get("tags")) + [o.get("primary_category")]:
            cat_index.setdefault(str(tag).lower(), []).append(o.get("id"))

    for o in opps:
        if not isinstance(o, dict):
            continue
        produces = [str(x) for x in as_list(o.get("produces"))]
        unlocks = []
        for u in as_list(o.get("unlocks")):
            if isinstance(u, dict):
                uid = u.get("opportunity_id")
                utype = u.get("type") or "opportunity"
                label = u.get("label") or utype
            else:
                uid, utype, label = None, str(u), str(u)
            matched = None
            if not uid:
                # 用 type/tags 在已发现机会里找同类的真实机会（只做保守的同名匹配）
                key = str(utype).lower()
                for tag, ids in cat_index.items():
                    if key and (key in tag or tag in key):
                        for i in ids:
                            if i and i != o.get("id"):
                                matched = i
                                break
                    if matched:
                        break
            unlocks.append({"type": utype, "label": label, "opportunity_id": uid or matched})
            if uid or matched:
                edges.append({"from": o.get("id"), "to": uid or matched, "type": utype})

        nodes.append({
            "id": o.get("id"), "title": o.get("title"),
            "primary_category": o.get("primary_category"),
            "produces": produces,
            "unlocks": unlocks,
            "goal_contribution": [str(x) for x in as_list(o.get("goal_contribution"))],
            "outcomes": o.get("outcomes") or {},
            "effort_hours": _hours((o.get("effort") or {}).get("weekly_commitment")),
            "public_output": any(k in " ".join(produces).lower()
                                 for k in ("repo", "github", "public", "公开", "paper", "论文",
                                           "talk", "演讲", "post", "文章")),
        })

    return {"nodes": nodes, "edges": edges,
            "goals": sorted({g for n in nodes for g in n["goal_contribution"]})}


def bridges_for_gap(gap, opps, limit: int = 5) -> list:
    """缺口 → 桥接机会（真实学习型机会优先）。"""
    gt = tokens(gap)
    if not gt:
        return []
    scored = []
    for n in build_graph(opps)["nodes"]:
        hay = " ".join([str(n.get("title") or "")] + [str(u.get("type") or "") for u in n.get("unlocks", [])])
        overlap = len(gt & tokens(hay))
        if not overlap:
            continue
        effort = n.get("effort_hours")
        low_cost = (effort is None) or (effort <= 8)
        score = overlap + (2 if n.get("public_output") else 0) + (1 if low_cost else 0)
        scored.append((score, n, low_cost))

    scored.sort(key=lambda x: -x[0])
    out = []
    for _s, n, low_cost in scored[:limit]:
        out.append({
            "id": n["id"], "title": n["title"],
            "produces": n.get("produces", []),
            "unlocks": [u["type"] for u in n.get("unlocks", [])],
            "low_commitment": low_cost,
            "public_output": n.get("public_output", False),
        })
    return out


def gap_to_bridge_report(gaps, opps) -> list:
    """缺口列表 → [缺口 → 桥接机会 → 产出 → 后续通道]。"""
    report = []
    for g in gaps:
        bridges = bridges_for_gap(g, opps)
        report.append({"gap": g, "bridges": bridges,
                       "note": "优先真实学习型机会（开源/真实项目/社群），不是课程列表"
                               if bridges else "本轮未发现可作桥接的真实机会"})
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Opportunity Graph / gap→bridge")
    ap.add_argument("--opportunities", required=True)
    ap.add_argument("--graph", action="store_true", help="输出 graph")
    ap.add_argument("--gaps", default="", help="逗号分隔的缺口，如 'FreeRTOS,TinyML'")
    args = ap.parse_args(argv)
    data = json.load(open(args.opportunities, encoding="utf-8"))
    opps = data.get("opportunities", [data]) if isinstance(data, dict) else data
    if args.gaps:
        gaps = [g.strip() for g in args.gaps.split(",") if g.strip()]
        print(json.dumps(gap_to_bridge_report(gaps, opps), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_graph(opps), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
