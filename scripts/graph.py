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


def time_to_evidence(opp) -> dict:
    """这个机会多久能产生**用户未来可展示的真实证据**？

    3 小时的普通 certificate 与 15 小时的公开 GitHub PR 不是同一类：
    关键是"投入 → 产生什么 evidence → 对目标机会有多大作用"。
    """
    hours = _hours((opp.get("effort") or {}).get("weekly_commitment")) \
        if isinstance(opp.get("effort"), dict) else _hours(opp.get("effort"))
    produces = [str(x) for x in as_list(opp.get("produces"))]
    public_markers = ("repo", "pr", "github", "public", "paper", "talk", "演讲", "论文",
                      "documentation", "writeup", "demo", "release", "certificate", "证书")
    public = [pr for pr in produces if any(m in pr.lower() for m in public_markers)]
    if public and any(m in " ".join(public).lower() for m in
                      ("pr", "github", "repo", "paper", "论文", "talk", "演讲")):
        strength = "strong"
    elif public:
        strength = "medium"
    else:
        strength = "weak"
    return {"hours": hours, "produces": produces, "public_evidence": public,
            "strength": strength,
            "rationale": ("产出可公开验证的成果" if strength == "strong"
                          else "产出可展示材料" if strength == "medium"
                          else "未写明可展示产出")}


#: 非技能类缺口用**意图信号**匹配（中文缺口名与英文 tag 之间没有 token 交集）
GAP_TYPE_SIGNALS = {
    "public_reputation": {"categories": ("event", "open_source", "networking", "competition"),
                          "tags": ("speaker", "cfp", "talk", "conference", "maintainer",
                                   "award", "public", "演讲", "开源")},
    "leadership": {"categories": ("open_source", "project", "entrepreneurship", "networking"),
                   "tags": ("maintainer", "owner", "lead", "committee", "organizer",
                            "mentor", "负责", "主导")},
    "management": {"categories": ("networking", "entrepreneurship", "event"),
                   "tags": ("leadership", "management", "mentor", "programme", "管理")},
    "network": {"categories": ("networking", "event", "research", "open_source"),
                "tags": ("community", "mentor", "alumni", "seminar", "meetup", "professor",
                         "社群", "导师", "教授")},
    "research": {"categories": ("research", "education"),
                 "tags": ("lab", "professor", "research", "paper", "seminar", "实验室", "论文")},
    "language": {"categories": ("language", "education"),
                 "tags": ("jlpt", "ielts", "toefl", "language", "日语", "英语")},
    "portfolio": {"categories": ("project", "competition", "open_source"),
                  "tags": ("demo", "portfolio", "build", "writeup", "作品")},
    "credential": {"categories": ("skill_development", "education"),
                   "tags": ("certificate", "certification", "cert", "证书")},
    "experience": {"categories": ("career", "project", "open_source"),
                   "tags": ("internship", "hands-on", "experience", "实习")},
    "location_visa": {"categories": ("career", "education"),
                      "tags": ("remote", "visa", "relocation", "远程")},
    "education": {"categories": ("education",), "tags": ("master", "programme", "degree")},
    "skill": {"categories": (), "tags": ()},
}

BRIDGE_WEIGHTS = {"gap_coverage": 0.26, "time_to_evidence": 0.22, "readiness": 0.16,
                  "future_optionality": 0.12, "evidence_quality": 0.10,
                  "effort_fit": 0.08, "trust": 0.06}
_LEVEL_V = {"high": 1.0, "medium": 0.6, "low": 0.3, "unknown": 0.5, None: 0.5}
_READY_V = {"ready_now": 1.0, "minor_preparation": 0.8, "short_preparation": 0.6,
            "major_preparation": 0.35, "blocked": 0.05, "unknown": 0.5}


def bridges_for_gap(gap, opps, profile=None, limit: int = 3) -> list:
    """缺口 → 真实 Bridge 机会（按 gap_coverage / time_to_evidence / readiness / … 评分）。

    Bridge 必须是**真实机会**（有 canonical source 的 opportunity），不是教程列表。
    """
    profile = profile or {}
    if isinstance(gap, str):
        gap = {"name": gap, "type": "skill"}
    gt = tokens(gap.get("name"))
    weekly_limit = _hours(profile.get("constraints", {}).get("weekly_time"))
    out = []
    for o in opps or []:
        if not isinstance(o, dict):
            continue
        hay = " ".join([str(o.get("title") or ""), str(o.get("summary") or ""),
                        " ".join(str(x) for x in as_list(o.get("tags"))),
                        " ".join(str(x) for x in as_list(o.get("produces"))),
                        " ".join(str(x) for x in as_list(o.get("unlocks")) if not isinstance(x, dict))
                        + " " + " ".join(str(u.get("type") or "") for u in as_list(o.get("unlocks"))
                                         if isinstance(u, dict))])
        overlap = len(gt & tokens(hay)) if gt else 0
        # 非技能类缺口：用意图信号（类别 / 标签）判断，而不是名字 token
        signals = GAP_TYPE_SIGNALS.get(gap.get("type") or "skill", {})
        cat = str(o.get("primary_category") or "").lower()
        otags = {str(t).lower() for t in as_list(o.get("tags"))}
        signal_hit = (cat in signals.get("categories", ())
                      or bool(otags & set(signals.get("tags", ()))))
        if not overlap and not signal_hit:
            continue
        if not overlap and signal_hit:
            overlap = 1
        ttv = time_to_evidence(o)
        hours = ttv["hours"]
        effort_fit = 1.0 if (hours is None or weekly_limit is None or hours <= weekly_limit) else 0.3
        from readiness import readiness as _readiness
        rd = _readiness(o, profile)
        coverage = "high" if overlap >= 2 else "medium"
        factors = {
            "gap_coverage": 1.0 if overlap >= 2 else 0.6,
            "time_to_evidence": {"strong": 1.0, "medium": 0.7, "weak": 0.35}[ttv["strength"]],
            "readiness": _READY_V.get(rd["status"], 0.5),
            "future_optionality": _LEVEL_V.get(
                str((o.get("future_optionality") or {}).get("level")
                    if isinstance(o.get("future_optionality"), dict)
                    else o.get("future_optionality")), 0.5),
            "evidence_quality": 1.0 if o.get("verification_status") == "verified_official" else 0.5,
            "effort_fit": effort_fit,
            "trust": {"A": 1.0, "B": 0.8, "C": 0.5, "D": 0.3}.get(o.get("trust_tier"), 0.6),
        }
        score = round(100 * sum(BRIDGE_WEIGHTS[k] * v for k, v in factors.items()))
        out.append({"opportunity_id": o.get("id"), "title": o.get("title"),
                    "category": o.get("primary_category"),
                    "official_url": o.get("official_url"),
                    "gap_coverage": coverage,
                    "time_to_evidence": ttv,
                    "readiness": rd["status"],
                    "effort": o.get("effort"), "cost": o.get("cost"),
                    "future_optionality": (o.get("future_optionality") or {}).get("level"),
                    "evidence_complete": bool(o.get("verification_status") == "verified_official"
                                              and (o.get("evidence") or {}).get("application_status")),
                    "factors": factors, "score": score})
    out.sort(key=lambda b: (-b["score"], str(b["opportunity_id"])))
    return out[:limit]


def gap_to_bridge_report(gaps, opps, profile=None) -> list:
    """缺口列表 → [缺口 → 桥接机会 → 产出 → 后续通道]；无桥时如实说明（Source 需求）。"""
    report = []
    for g in gaps:
        if isinstance(g, str):                      # 兼容旧调用：字符串也当 gap 处理
            g = {"id": f"gap-{g}", "type": "skill", "name": g, "source": "user_stated",
                 "sample": "用户明确提出的缺口", "priority": "medium"}
        bridges = bridges_for_gap(g, opps, profile)
        entry = {"gap": g, "bridges": bridges,
                 "note": ("优先真实学习型机会（开源/真实项目/社群），不是课程列表" if bridges
                          else "本轮未发现可作桥接的真实机会 —— 记为 Source Intelligence 需求")}
        if not bridges:
            entry["source_gap"] = {"reason": "no_real_bridge_found",
                                   "query_hint": f"{g.get('name')} 真实机会（开源/项目/社区）"}
        report.append(entry)
    return report


def bridge_graph(gaps, opps, profile=None, goal=None) -> dict:
    """统一图：User → Gap → Bridge → Produced Evidence → Target/Goal。"""
    nodes, edges = [], []
    nodes.append({"id": "user", "kind": "user", "label": "user"})
    if goal:
        nodes.append({"id": f"goal:{goal}", "kind": "goal", "label": goal})
        edges.append({"from": "user", "to": f"goal:{goal}", "type": "pursues"})
    for g in gaps or []:
        gid = g.get("id") or f"gap:{g.get('name')}"
        nodes.append({"id": gid, "kind": "gap", "label": g.get("name"), "gap_type": g.get("type"),
                      "source": g.get("source"), "sample": g.get("sample")})
        edges.append({"from": "user", "to": gid, "type": "has_gap"})
        for b in bridges_for_gap(g, opps, profile):
            bid = f"bridge:{b['opportunity_id']}"
            nodes.append({"id": bid, "kind": "bridge", "label": b["title"],
                          "score": b["score"], "evidence_complete": b["evidence_complete"],
                          "time_to_evidence": b["time_to_evidence"]})
            edges.append({"from": gid, "to": bid, "type": "bridged_by"})
            for prod in (b["time_to_evidence"].get("public_evidence") or [])[:2]:
                pid = f"evidence:{b['opportunity_id']}:{prod}"
                nodes.append({"id": pid, "kind": "evidence", "label": prod})
                edges.append({"from": bid, "to": pid, "type": "produces"})
                if goal:
                    edges.append({"from": pid, "to": f"goal:{goal}", "type": "contributes_to"})
    return {"nodes": nodes, "edges": edges,
            "connected": any(e["type"] == "bridged_by" for e in edges)}


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
