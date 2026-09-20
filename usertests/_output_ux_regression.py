#!/usr/bin/env python3
"""P1 Output & Decision UX 回归：把 5 个 persona 的真实候选过一遍新的输出适配层。

数据来源
  * A / B：本轮新做的真实检索与官方页核验（2026-09-21）
  * C / D / E：各自已存档的 record-si.json（真实候选、真实验证），只换成新输出层 ——
    这正好隔离出本轮要测的东西：**同一批输入，换表达层**

对每个 case 都做：真实 gate（score.py）→ gaps → bridges → portfolio → presentation.render_answer
→ 8 个输出指标 → 跨 persona context leakage 检查。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import common as C            # noqa: E402
import gaps as GP             # noqa: E402
import graph as G             # noqa: E402
import portfolio as PF        # noqa: E402
import presentation as P      # noqa: E402
import score as SC            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output-ux")
TODAY = dt.date(2026, 9, 21)

CASES = {
    "A": {"dir": "case-a-iot-undergrad", "mode": "A", "source": "fresh"},
    "B": {"dir": "case-b-japan-masters", "mode": "A", "source": "fresh"},
    "C": {"dir": "case-c-promotion", "mode": "A", "source": "record",
          "record": "usertests/case-c-promotion/record-si.json",
          "profile": "usertests/case-c-promotion/profile.json"},
    # 本轮 D 的 prompt（5 年后端转 AI）没有存档会话；最接近的真实 baseline 是
    # case-b-professional（3 年嵌入式转 Edge AI，6h/周）。该记录没有 evidence 块，
    # 因此对它做**表达层对照**（沿用记录里已判定的 zone），不重跑 gate。
    "D": {"dir": "case-d-ai-switch", "mode": "A", "source": "expression",
          "record": "usertests/case-b-professional/record.json"},
    "E": {"dir": "case-e-unknown", "mode": "E", "source": "record",
          "record": "usertests/case-e-unknown/record-si.json",
          "profile": "usertests/case-e-unknown/profile.json"},
}

CATEGORY_BY_FAMILY = {"university_lab": "research", "professor_page": "research",
                      "research_seminar": "research", "research_institute": "research",
                      "graduate_school": "education", "academic_society": "networking",
                      "official_exam_body": "language", "university_language_center": "education",
                      "foundation": "open_source", "mentorship_program": "open_source",
                      "working_group": "open_source", "contributor_guide": "open_source",
                      "community_event": "event", "maintainer_program": "open_source",
                      "project_repository": "open_source", "speech_contest": "competition"}


def slug(text, idx):
    s = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "-", str(text or "").lower()).strip("-")
    return (s[:48] or f"item-{idx}")


def norm_candidate(c, idx):
    """存档候选 → opportunity 形状（只搬运真实存在的字段，不补造）。"""
    app = c.get("application_status")
    if app not in C.OPPORTUNITY_APPLICATION_STATUSES:
        app = "unknown" if app else None
    prov = c.get("provenance")
    verified = c.get("verification_status") == "verified_official"
    effort = c.get("effort")
    if not effort and c.get("weekly_commitment"):
        effort = {"weekly_commitment": c["weekly_commitment"]}
    o = {
        "id": c.get("id") or slug(c.get("title"), idx),
        "title": c.get("title"),
        "organization": c.get("organization"),
        "primary_category": c.get("category")
                            or CATEGORY_BY_FAMILY.get(c.get("source_family")) or "career",
        "official_url": c.get("official_url"),
        "application_status": app,
        "deadline": (c.get("gate_computed") or {}).get("deadline_iso"),
        "deadline_type": c.get("deadline_type"),
        "verification_status": c.get("verification_status") or "unverified",
        "evidence": c.get("evidence"),
        "trust_tier": "A" if verified else ("B" if prov in ("known_source",
                                                            "source_family_query") else "C"),
        "effort": effort,
        "produces": c.get("produces") or [],
        "required_materials": c.get("prerequisites") or [],
        "skills_required": [],
        "last_verified": c.get("verified_at") or "2026-09-20",
        "layer": c.get("layer") or "exploit",
        "notes": list(c.get("notes") or []),
    }
    if c.get("source_family"):
        o["_source_family"] = c["source_family"]
    return o


def load_case(letter, spec):
    d = os.path.join(OUT, spec["dir"])
    os.makedirs(d, exist_ok=True)
    if spec["source"] == "fresh":
        return d, json.load(open(os.path.join(d, "profile.json"), encoding="utf-8")), \
            json.load(open(os.path.join(d, "opportunities.json"), encoding="utf-8"))["opportunities"]
    parent = os.path.dirname(HERE)
    prof = json.load(open(os.path.join(parent, spec["profile"]), encoding="utf-8"))
    rec = json.load(open(os.path.join(parent, spec["record"]), encoding="utf-8"))
    prof = dict(prof)
    prof["_session"] = letter
    # 用户原话必须进画像：否则无法判断某个字段是"用户说过"还是"被继承来的"
    if rec.get("user_input"):
        prof["user_input"] = rec["user_input"]
    if letter == "E":
        # §9：E 必须使用全新画像（不继承任何背景）。旧画像另存 profile-previous.json 供对照。
        fresh = os.path.join(d, "profile-previous.json")
        if not os.path.exists(fresh):
            json.dump(prof, open(fresh, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        prof = {"_note": "只写用户原话；其余一律 Unknown。",
                "_session": "E", "user_input": prof.get("user_input"),
                "profile_version": 1, "updated_at": "2026-09-21",
                "life_stage": [], "career_stage": None, "education": {}, "skills": [],
                "interests": [], "experience": {}, "constraints": {}, "goals": []}
    opps = [norm_candidate(c, i) for i, c in enumerate(rec.get("candidates") or [])]
    json.dump(prof, open(os.path.join(d, "profile.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"_note": f"来自 {spec['record']} 的已核验候选，归一化为 opportunity 形状后重新过真实 gate。",
               "opportunities": opps},
              open(os.path.join(d, "opportunities.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return d, prof, opps


def load_expression_only(letter, spec):
    """表达层对照：沿用记录里已判定的 zone，只为渲染补齐适配层需要的字段。

    记录缺 `evidence` 块，无法重跑 gate —— 这一点在报告里明确说明，不假装重跑过。
    """
    parent = os.path.dirname(HERE)
    rec = json.load(open(os.path.join(parent, spec["record"]), encoding="utf-8"))
    d = os.path.join(OUT, spec["dir"])
    os.makedirs(d, exist_ok=True)
    rows = []
    for i, x in enumerate(rec.get("results") or []):
        zone = x.get("zone")
        rows.append({
            "id": slug(x.get("title"), i), "title": x.get("title"),
            "organization": x.get("organization"),
            "primary_category": x.get("category") or "career",
            "official_url": x.get("official_url"), "zone": zone,
            "eligibility_verdict": x.get("eligibility_verdict") or "Unknown",
            "freshness": x.get("freshness"), "effort": x.get("effort"),
            "produces": [],                      # 存档记录未捕获该字段
            "evidence_complete": zone == "recommended_now",
            "actionable": zone == "recommended_now",
            "participation_open": zone == "recommended_now",
            "exclusion_reason": x.get("note") if zone == "excluded" else None,
            "_expression_only": True,
        })
    prof = {"_session": letter, "user_input": "（本轮 D 的 prompt 无存档会话；此处使用最接近的"
            "真实 baseline：3 年嵌入式工程师想转 Edge AI，每周 6h）",
            "life_stage": ["working"], "career_stage": ["early_career"],
            "constraints": {"weekly_time": "6", "preferred_country": ["Japan"]},
            "goals": [{"type": "skill", "priority": "high"}],
            "_note": "表达层对照用画像；仅用于渲染，不用于重新判定资格。"}
    out = {"_note": "来自 " + spec["record"] + " 的已判定结果（表达层对照，未重跑 gate）。",
           "opportunities": rows}
    json.dump(prof, open(os.path.join(d, "profile.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(out, open(os.path.join(d, "opportunities.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"zones": "（表达层对照：沿用记录 zone）", "results": rows},
              open(os.path.join(d, "scored.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return d, prof, rows


def run_case(letter, spec):
    if spec["source"] == "expression":
        d, prof, rows = load_expression_only(letter, spec)
        g, flat, pf = [], [], {}
        json.dump(g, open(os.path.join(d, "gaps.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        json.dump(flat, open(os.path.join(d, "bridges.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        json.dump({}, open(os.path.join(d, "portfolio.json"), "w", encoding="utf-8"))
        answer = P.render_answer(prof, rows, g, flat, portfolio=pf, mode=spec["mode"])
        answer["self_directed"] = []
        answer["case"] = letter
        answer["leakage"] = P.context_leakage(prof)
        answer["expression_only"] = True
        json.dump(answer, open(os.path.join(d, "answer.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return {"letter": letter, "dir": spec["dir"], "profile": prof, "rows": rows,
                "gaps": g, "bridges": flat, "portfolio": pf, "answer": answer,
                "zones": "（表达层对照）"}

    d, prof, opps = load_case(letter, spec)
    res = SC.score_all(prof, opps, today=TODAY)
    rows = list(res.get("results") or [])
    for e in (res.get("excluded") or []):
        rows.append({**e, "zone": "excluded"})
    json.dump({"zones": res.get("zones"), "results": rows},
              open(os.path.join(d, "scored.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    g = GP.collect_gaps(opps, prof)
    json.dump(g, open(os.path.join(d, "gaps.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    br = G.gap_to_bridge_report(g, opps, prof)
    flat = [dict(b, gap=e["gap"]["name"]) for e in br for b in e["bridges"]]
    json.dump(flat, open(os.path.join(d, "bridges.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    pf = PF.build_portfolio(rows, prof, bridges=flat)
    json.dump(pf, open(os.path.join(d, "portfolio.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 自建替代路径：研究型/技能型缺口找不到外部 Bridge 时，必须单独成段
    self_dir = []
    for e in br:
        if not e["bridges"] and (e["gap"].get("relevance") or {}).get("relevance") in (
                "core_gap", "supporting_gap"):
            self_dir.append(P.self_directed_fallback(e["gap"]))

    answer = P.render_answer(prof, rows, g, flat, portfolio=pf, mode=spec["mode"])
    answer["self_directed"] = self_dir
    answer["case"] = letter
    answer["leakage"] = P.context_leakage(prof)
    json.dump(answer, open(os.path.join(d, "answer.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return {"letter": letter, "dir": spec["dir"], "profile": prof, "rows": rows, "gaps": g,
            "bridges": flat, "portfolio": pf, "answer": answer, "zones": res.get("zones")}


def leakage_matrix(results):
    """跨 persona 泄漏检查：画像里不得出现用户**没说过**的内容。

    判断要跨语言：画像存的是英文字段值（working / esp32），用户原话是中文
    （「工作三年」/「ESP32」），只看英文 key 会误报。
    """
    suspects = {
        "在职假设": {"profile_keys": ("self_employed", "working"),
                     "user_keys": ("工作", "在职", "上班", "跳槽", "工程", "任职")},
        "ESP32": {"profile_keys": ("esp32",), "user_keys": ("esp32",)},
        "Python": {"profile_keys": ("python",), "user_keys": ("python",)},
        "日语背景": {"profile_keys": ("japanese", "日语"), "user_keys": ("日语", "日本語")},
        "研究经历": {"profile_keys": ("research",), "user_keys": ("研究", "科研")},
        "大学生身份": {"profile_keys": ("undergraduate", "大三", "bachelor"),
                       "user_keys": ("大学", "本科", "大三", "大四", "研究生", "硕士")},
    }
    #: 只检查"关于用户背景的字段"。不查 goals / career_stage 等**派生**枚举 ——
    #: 那些是从用户目标推导出来的，出现某个枚举值不等于继承了背景。
    BACKGROUND_FIELDS = ("skills", "interests", "education", "experience", "languages",
                         "nationality", "life_stage", "constraints", "certifications")

    def values_only(profile):
        """只取背景字段的**取值**，忽略 null / 说明性文本。"""
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
                out.append(str(node).lower())
        for f in BACKGROUND_FIELDS:
            if f in (profile or {}):
                walk({f: profile[f]})
        return " ".join(out)

    findings = []
    for r in results:
        blob = values_only(r["profile"])
        stated = str(r["profile"].get("user_input") or "").lower()
        for label, keys in suspects.items():
            has = any(k in blob for k in keys["profile_keys"])
            said = any(k in stated for k in keys["user_keys"])
            if has and not said:
                findings.append({"case": r["letter"], "field": label,
                                 "note": "画像里出现了用户原话里没有的内容"})
        if r["profile"].get("_inherited_from"):
            findings.append({"case": r["letter"], "field": "_inherited_from",
                             "note": "画像标注为继承自其他会话"})
    return findings


def inferred_fields(results):
    """`inferred_pending` 字段是允许的（可驱动搜索与排序，但不参与资格判定）—— 单独列出而非算泄漏。"""
    out = []
    for r in results:
        for key, value in (r["profile"] or {}).items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, dict) and item.get("_provenance") == "inferred_pending":
                    out.append({"case": r["letter"], "field": key,
                                "value": item.get("name"),
                                "note": "推断值，不得参与资格判定"})
    return out


def before_after(letter, r):
    """before = 该 case 上一轮的最终回答（若有）；after = 新输出层。"""
    prev = {"C": "usertests/case-c-promotion/transcript-si.md",
            "D": "usertests/case-d-japan-masters/transcript-si.md",
            "E": "usertests/case-e-unknown/transcript-si.md"}.get(letter)
    path = os.path.join(os.path.dirname(HERE), prev) if prev else None
    return path if path and os.path.exists(path) else None


def main():
    results = [run_case(l, s) for l, s in CASES.items()]
    leaks = leakage_matrix(results)
    metrics = P.output_metrics([r["answer"] for r in results])

    lines = ["# 五 Persona 输出回归（P1 Output & Decision UX）", "",
             f"日期：2026-09-21　|　数据：A/B 本轮新核验，C/D/E 用已存档真实候选",
             "同一批输入过**新输出适配层**，真实 gate 未被绕过。", ""]
    for r in results:
        a = r["answer"]
        conf = a["confidence"]
        lines += [f"## Case {r['letter']}　（{r['dir']}）", "",
                  f"- 分区：{r['zones']}",
                  f"- decision_confidence：**{conf['level']}** — {conf['note']}",
                  f"- 未知信号：{', '.join(conf['unknown']) or '（无）'}",
                  f"- 发展缺口：{[g['name'] for g in r['gaps'] if (g.get('relevance') or {}).get('relevance') in ('core_gap','supporting_gap')] or '（无）'}",
                  f"- 资源分配：{a['allocation']['mode']} — {a['allocation'].get('note','')}",
                  f"- 输出自检违规：{a['violations'] or '无'}",
                  f"- 长度：主推荐 {len(a['main'])} 条 / 需确认 {len(a['worth_verifying'])} 条 / 排除 {len(a['excluded'])} 条",
                  ""]
        for c in a["main"]:
            lines.append(P.render_card(c))
            lines.append("")
        if a["worth_verifying"]:
            lines.append("### 需先确认")
            for c in a["worth_verifying"]:
                pw = c.get("participation") or {}
                lines.append(f"- **{c['title']}**（{pw.get('label','')}）— "
                             f"{'; '.join(c.get('needs_confirmation') or []) or '无'}")
            lines.append("")
        if a["excluded"]:
            lines.append("### 已排除")
            for e in a["excluded"]:
                lines.append(f"- {e.get('title')} — {e.get('reason')}")
            lines.append("")
        if a.get("self_directed"):
            lines.append("### 自建替代路径（不是外部机会）")
            for s in a["self_directed"]:
                lines.append(f"- 缺口「{s['gap']}」：{s['reason']}")
            lines.append("")
        if a.get("explore"):
            lines.append(f"### 探索维度：{a['explore']['axis_count']} 类 "
                         f"{a['explore']['axes']}")
            lines.append("")
        lines.append(f"（未在主推荐里的缺口/准备项不在此展开）")
        lines.append("")

    lines += ["## 输出指标", "", "| 指标 | 值 |", "|---|---|"]
    for k, v in metrics.items():
        lines.append(f"| `{k}` | {v} |")
    inf = inferred_fields(results)
    lines += ["", f"## 跨 persona 泄漏检查：{'通过（0 处）' if not leaks else leaks}",
              f"## 推断值（允许，不参与资格判定）：{inf or '（无）'}", ""]
    open(os.path.join(OUT, "REGISTRY.md"), "w", encoding="utf-8").write("\n".join(lines))

    print("zones / confidence / violations:")
    for r in results:
        print(f"  {r['letter']}  {r['zones']}  conf={r['answer']['confidence']['level']}"
              f"  main={len(r['answer']['main'])} worth={len(r['answer']['worth_verifying'])}"
              f" excl={len(r['answer']['excluded'])}  viol={len(r['answer']['violations'])}"
              f"  explore={len((r['answer'].get('explore') or {}).get('axes') or [])}")
    print("metrics:", json.dumps(metrics, ensure_ascii=False))
    print("leakage:", leaks or "none")


if __name__ == "__main__":
    main()
