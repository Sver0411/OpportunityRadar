#!/usr/bin/env python3
"""score.py - Opportunity 匹配度与优先级的确定性打分框架（决策辅助，不是结论）。

设计立场：
  * 只做确定性部分（资格预判、目标匹配、技能/兴趣重合、地点、时效、信任、新鲜度）。
  * 输出**分项**而不是一个"科学分数"；最终排序与解释由 Agent 在 references/ranking.md 上完成。
  * 未知不作 0 分处理（未知 → 中性分），避免错杀信息不全的真实机会。
  * Match 与 Priority 分开：Match 不含时间，Priority = 0.85*Match + 0.15*Urgency。

用法：
  python3 score.py --profile profile.json --opportunities opps.json
  python3 score.py --profile examples/profile.example.json \
                  --opportunities examples/opportunity.batch.example.json --format table
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

WEIGHTS = {
    "eligibility": 0.26,
    "goal_fit": 0.19,
    "skill_fit": 0.15,
    "interest_fit": 0.11,
    "location_fit": 0.10,
    "value_fit": 0.08,
    "trust": 0.06,
    "novelty": 0.05,
}

VERDICT_SCORE = {
    "Eligible": 100,
    "Probably Eligible": 82,
    "Unknown": 55,
    "Probably Ineligible": 25,
    "Ineligible": 0,
    None: 55,
}

TRUST_SCORE = {"A": 100, "B": 85, "C": 60, "D": 35, None: 50}

GOAL_TO_CATEGORY = {
    "internship": ["career"], "fulltime": ["career"], "research": ["research"],
    "competition": ["competition"], "education": ["education"], "language": ["language"],
    "skill": ["skill_development"], "open_source": ["open_source"], "hobby": ["hobby"],
    "funding": ["funding"], "event": ["event"], "project": ["project"],
    "entrepreneurship": ["entrepreneurship"], "networking": ["networking"],
}

PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.35, None: 0.5}

GOAL_TO_VALUE_DIM = {
    "internship": ["career", "portfolio"], "fulltime": ["career", "financial"],
    "research": ["research", "skill"], "competition": ["portfolio", "skill"],
    "education": ["research", "career"], "language": ["skill", "career"],
    "skill": ["skill"], "open_source": ["skill", "portfolio", "networking"],
    "hobby": ["interest"], "funding": ["financial"],
    "event": ["networking", "skill"], "project": ["portfolio", "skill"],
    "entrepreneurship": ["career", "networking"], "networking": ["networking"],
}

VALUE_LEVEL = {"high": 1.0, "medium": 0.6, "low": 0.3, "unknown": 0.5, None: 0.5}

INTEREST_ALIASES = {
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "llm", "生成"],
    "agent": ["agent", "agents", "multi-agent", "llm agent", "autonomous"],
    "iot": ["iot", "internet of things", "sensor network", "smart device", "スマート"],
    "embedded": ["embedded", "firmware", "mcu", "microcontroller", "rtos", "esp32", "stm32", "組み込み"],
    "robotics": ["robotics", "robot", "ros", "mechatronics", "ロボット"],
    "drone": ["drone", "uav", "quadcopter", "无人机", "ドローン"],
    "photography": ["photography", "camera", "photo", "写真", "摄影"],
    "game": ["game", "gamedev", "unity", "unreal", "esports", "ゲーム"],
    "design": ["design", "ui", "ux", "graphic", "industrial design", "デザイン"],
    "automotive": ["automotive", "vehicle", "adas", "automobile", "モビリティ"],
    "aviation": ["aviation", "aerospace", "space", "航空", "宇宙"],
    "maker": ["maker", "3d printing", "diy", "fabrication", "ものづくり"],
    "energy": ["energy", "climate", "sustainability", "renewable"],
    "data": ["data", "analytics", "statistics", "visualization"],
    "security": ["security", "ctf", "cybersecurity", "penetration"],
}

HARD_ELIGIBILITY_FIELDS = ("education_level", "student_year", "graduation_window",
                           "language_requirement", "nationality_requirement", "school_requirement")
"""硬性资格字段清单：用于文档说明确定性预判覆盖的范围（见 references/eligibility.md §2）。"""


# ------------------------------------------------------------------ 小工具

def norm(s):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u30ff]+", " ", str(s or "").lower()).strip()


def as_list(v):
    if v in (None, "", [], {}):
        return []
    return v if isinstance(v, list) else [v]


def skill_hit(skill, profile_skills):
    """技能匹配：归一化相等，或 token 包含（'c/c++' 命中 'c'；'python3' 命中 'python'）。"""
    ns = norm(skill)
    if not ns:
        return False
    st = set(ns.split())
    for ps in profile_skills:
        np_ = norm(ps)
        if not np_:
            continue
        if ns == np_:
            return True
        pt = set(np_.split())
        if st & pt:
            return True
        # 也允许整体子串（如 "esp32-s3" 命中 "esp32"）
        if len(np_) >= 3 and (np_ in ns or ns in np_):
            return True
    return False


def parse_hours(text):
    if text in (None, ""):
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"(\d{1,3})\s*(?:h\b|hr|hrs|hours?|時間|小时|時間/週|h/週)", str(text), re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{1,3})", str(text))
    return float(m.group(1)) if m else None


def days_until(date_str, today):
    if not date_str:
        return None
    try:
        d = dt.date.fromisoformat(str(date_str)[:10])
    except ValueError:
        return None
    return (d - today).days


# ------------------------------------------------------------------ 分项

def level_ok(required, achieved, exam=""):
    """粗略判断成绩/等级是否达标。方向：JLPT N 数越小越高；其余分数越大越高。"""
    r, a = norm(required), norm(achieved)
    if not r or not a:
        return False
    rt, at = set(r.split()), set(a.split())
    if rt & at:
        return True
    rn = re.search(r"n([1-5])", r)
    an = re.search(r"n([1-5])", a)
    if rn and an:                        # JLPT：N1 最高
        return int(an.group(1)) <= int(rn.group(1))
    rnum = re.findall(r"\d+\.?\d*", r)
    anum = re.findall(r"\d+\.?\d*", a)
    if rnum and anum:
        try:
            return float(anum[0]) >= float(rnum[0])
        except ValueError:
            return False
    return False


def language_ok(opp, profile):
    """返回 (verdict_hint, reason)。verdict_hint ∈ {ok, missing, unknown}。"""
    prof = [norm(f"{l.get('language','')} {l.get('exam','')} {l.get('score','')} {l.get('level','')}")
            for l in as_list(profile.get("languages")) if isinstance(l, dict)]
    prof = [p for p in prof if p]
    verdicts = []
    for item in as_list(opp.get("language_requirement")):
        if isinstance(item, dict):
            lang = norm(item.get("language"))
            exam = norm(item.get("exam"))
            lvl = norm(item.get("min_level"))
        else:
            lang, exam, lvl = norm(item), "", ""
        cands = [p for p in prof if lang and lang in p]
        if not cands:
            verdicts.append(("missing", f"页面要求 {lang or '语言能力'}，画像中未列出该语言"))
            continue
        if not (exam or lvl):
            verdicts.append(("ok", f"页面只要求 {lang}，画像已有该语言"))
            continue
        hit = any(
            (not exam or exam in p) and (not lvl or level_ok(lvl, p, exam))
            for p in cands
        )
        if hit:
            verdicts.append(("ok", f"语言要求（{lang} {exam} {lvl}）与画像成绩相符"))
        else:
            verdicts.append(("unknown", f"页面要求 {lang} {exam} {lvl}，但画像未提供对应成绩/等级，无法确认达标"))
    if not verdicts:
        return "ok", ""
    if any(v[0] == "missing" for v in verdicts):
        return "missing", verdicts[0][1]
    if any(v[0] == "unknown" for v in verdicts):
        return "unknown", verdicts[0][1]
    return "ok", verdicts[0][1]


def eligibility_component(opp, profile, today):
    """若 Agent 已给出 verdict 则采用；否则做确定性预判。返回 (score, verdict, reasons[], needs_llm)."""
    explicit = (opp.get("eligibility") or {}).get("verdict")
    reasons, needs_llm = [], False

    ed = profile.get("education") or {}
    degree = ed.get("degree")
    if isinstance(degree, list):
        degree = degree[0] if degree else None

    computed = None
    d = days_until(opp.get("deadline"), today)
    if d is not None and d < 0:
        computed, reasons = "Ineligible", ["截止日期已过"]

    if computed is None:
        levels = as_list(opp.get("education_level"))
        if levels and degree:
            if "any" not in levels and degree not in levels:
                computed = "Probably Ineligible"
                reasons.append(f"页面要求学历 {levels}，你的学历为 {degree}")
        elif levels and not degree:
            computed = "Unknown"
            reasons.append("页面限定了学历，但画像未提供学历")

    if computed is None:
        years = as_list(opp.get("student_year"))
        cy = ed.get("current_year")
        if years and cy:
            if int(cy) not in [int(y) for y in years if str(y).isdigit()]:
                computed = "Probably Ineligible"
                reasons.append(f"页面要求学年 {years}，你在 {cy} 年级")
        elif years and not cy:
            computed = "Unknown"
            reasons.append("页面限定了学年，但画像未提供年级")

    if computed is None and opp.get("graduation_window") and ed.get("expected_graduation"):
        gw, eg = norm(opp["graduation_window"]), norm(ed["expected_graduation"])
        if gw and eg and gw.split()[0][:4] != eg.split()[0][:4]:
            computed = "Probably Ineligible"
            reasons.append(f"页面要求毕业年度 {opp['graduation_window']}，你预计 {ed['expected_graduation']}")

    if computed is None and opp.get("language_requirement"):
        hint, reason = language_ok(opp, profile)
        reasons.append(reason)
        if hint == "missing":
            computed = "Probably Ineligible"
        elif hint == "unknown":
            computed = "Unknown"

    if computed is None and opp.get("major_requirement"):
        mr = " ".join(as_list(opp.get("major_requirement")))
        major = norm(ed.get("major"))
        if major and mr:
            major_tokens = [t for t in major.split() if len(t) > 2]
            if any(t in norm(mr) for t in major_tokens):
                reasons.append("专业要求与画像专业字面相关（最终以组织方定义为准）")
            else:
                needs_llm = True
                reasons.append("专业要求需语义判断（related field 类表述）")
        elif not major:
            computed = "Unknown"
            reasons.append("页面有专业要求，但画像未提供专业")

    if explicit:
        verdict = explicit
        reasons.insert(0, "采用 Agent 的资格判定（Step 10）")
    elif computed is None:
        verdict = "Probably Eligible" if reasons else "Unknown"
        if not reasons:
            reasons.append("页面未写明硬性资格范围，也没有可判定的冲突项")
    else:
        verdict = computed

    return VERDICT_SCORE.get(verdict, 55), verdict, reasons, needs_llm


def goal_component(opp, profile):
    goals = as_list(profile.get("goals"))
    if not goals:
        return 60.0, "画像未提供目标，按中性处理"
    cats = {opp.get("primary_category")} | set(as_list(opp.get("secondary_categories")))
    best, note = 0.0, "与声明的目标不重合"
    for g in goals:
        if not isinstance(g, dict):
            continue
        w = PRIORITY_WEIGHT.get(g.get("priority"), 0.5)
        for c in GOAL_TO_CATEGORY.get(g.get("type"), []):
            if opp.get("primary_category") == c:
                if w > best:
                    best, note = w, f"命中目标 {g.get('type')}（priority={g.get('priority')}）"
            elif c in cats:
                if w * 0.8 > best:
                    best, note = w * 0.8, f"作为次要类别命中目标 {g.get('type')}"
    return (100.0 * best if best else 15.0), note


def skill_component(opp, profile):
    ps = [s.get("name") if isinstance(s, dict) else s for s in as_list(profile.get("skills"))]
    req = as_list(opp.get("skills_required"))
    pref = as_list(opp.get("skills_preferred"))
    if not ps:
        return 50.0, "画像未提供技能，按中性处理"
    if req:
        rc = sum(1 for r in req if skill_hit(r, ps)) / len(req)
        pc = (sum(1 for r in pref if skill_hit(r, ps)) / len(pref)) if pref else 0.0
        score = 100 * (0.75 * rc + 0.25 * pc)
        hit = [r for r in req if skill_hit(r, ps)]
        return score, f"硬性技能覆盖 {len(hit)}/{len(req)}" + (f"（命中：{', '.join(map(str, hit))}）" if hit else "")
    if pref:
        pc = sum(1 for p in pref if skill_hit(p, ps)) / len(pref)
        return 100 * (0.35 + 0.5 * pc), f"页面只写了偏好技能，覆盖 {pc:.0%}"
    return 50.0, "页面未写明技能要求"


def interest_component(opp, profile):
    interests = as_list(profile.get("interests"))
    if not interests:
        return 55.0, "画像未提供兴趣"
    text = " ".join([norm(str(opp.get("title"))), norm(str(opp.get("summary"))),
                     " ".join(norm(t) for t in as_list(opp.get("tags"))),
                     norm(str(opp.get("primary_category"))),
                     " ".join(norm(x) for x in as_list(opp.get("major_requirement"))),
                     " ".join(norm(x) for x in as_list(opp.get("skills_preferred"))),
                     " ".join(norm(x) for x in as_list(opp.get("skills_required")))])
    matched = []
    for it in interests:
        key = norm(it)
        aliases = INTEREST_ALIASES.get(key, [key])
        if any(norm(a) and norm(a) in text for a in aliases):
            matched.append(it)
    if not matched:
        return 20.0, "未发现与画像兴趣的重合信号"
    ratio = len(matched) / len(interests)
    score = 100 * (0.25 + 0.75 * min(1.0, ratio * 2))
    return score, f"兴趣命中：{', '.join(matched)}"


def location_component(opp, profile):
    c = profile.get("constraints") or {}
    countries = [norm(x) for x in as_list(c.get("preferred_country"))]
    cities = [norm(x) for x in as_list(c.get("preferred_city"))]
    remote_pref = c.get("remote")
    relocation = c.get("relocation")
    if not countries and not cities and remote_pref is None:
        return 60.0, "画像未提供地区约束"
    oc, oci = norm(opp.get("country")), norm(opp.get("city"))
    if cities and oci and any(x and (x in oci or oci in x) for x in cities):
        return 100.0, f"城市匹配：{opp.get('city')}"
    if countries and oc and any(x and (x in oc or oc in x) for x in countries):
        return 95.0, f"国家/地区匹配：{opp.get('country')}"
    if opp.get("remote") and remote_pref:
        return 95.0, "远程，符合你的 remote 偏好"
    if opp.get("remote") and remote_pref is None:
        return 85.0, "远程机会（画像未表态，按可接受处理）"
    if oc and countries:
        return (60.0 if relocation else 25.0), f"地区为 {opp.get('country')}，不在偏好列表中"
    if not oc and not opp.get("remote"):
        return 45.0, "页面未写明地点，无法确认地区匹配"
    return 55.0, "地区信息不足"


def value_component(opp, profile):
    v = opp.get("value") or {}
    if not v:
        return 55.0, "尚未评估价值维度"
    goals = as_list(profile.get("goals"))
    dims = []
    for g in sorted([g for g in goals if isinstance(g, dict)],
                    key=lambda g: -PRIORITY_WEIGHT.get(g.get("priority"), 0.5)):
        dims = GOAL_TO_VALUE_DIM.get(g.get("type"), [])
        if dims:
            break
    if not dims:
        dims = list(v.keys())
    vals = [VALUE_LEVEL.get(str(v.get(d, "")).lower(), 0.5) for d in dims if d in v]
    if not vals:
        return 55.0, "价值评估与目标维度无交集"
    return 100 * sum(vals) / len(vals), f"按目标相关维度（{', '.join(dims)}）评分"


def trust_component(opp):
    t = opp.get("trust_tier")
    score = TRUST_SCORE.get(t, 50)
    vs = opp.get("verification_status")
    note = f"来源 Tier {t}" if t else "来源层级未知"
    if vs == "conflicting":
        score -= 5
        note += "，官方与第三方信息冲突（已以官方为准）"
    elif vs == "unverified":
        score -= 10
        note += "，未获官方确认"
    elif vs == "expired":
        score -= 30
        note += "，官方页面显示已结束"
    elif vs == "verified_official":
        note += "，3 项关键事实已官方确认"
    return max(0, score), note


def novelty_component(opp, seen_index):
    if seen_index is None:
        return 80.0, "无本地状态，按新机会处理"
    sid = opp.get("id")
    st = opp.get("seen_status") or seen_index.get(sid)
    if st == "repeat":
        return 40.0, "上次已推荐且无变化"
    if st == "changed":
        return 90.0, "已见过但有关键字段变化"
    if st == "new" or st is None:
        return 100.0, "新发现"
    return 80.0, "状态未知"


def urgency_score(days):
    if days is None:
        return None
    if days < 0:
        return 0.0
    if days <= 3:
        return 100.0
    if days <= 7:
        return 92.0
    if days <= 14:
        return 82.0
    if days <= 30:
        return 68.0
    if days <= 60:
        return 50.0
    if days <= 120:
        return 35.0
    return 20.0


def band(score):
    return "High" if score >= 80 else ("Medium" if score >= 60 else "Low")


# ------------------------------------------------------------------ 主流程

def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_list(path):
    """支持：机会数组 / last-run.json / dedupe.py 的输出（clusters[].merged）。"""
    data = load_json(path)
    if isinstance(data, list):
        return data
    for k in ("opportunities", "records", "items", "results"):
        if isinstance(data.get(k), list):
            return data[k]
    if isinstance(data.get("clusters"), list):
        return [c.get("merged") for c in data["clusters"] if isinstance(c, dict) and c.get("merged")]
    raise SystemExit(f"未在 {path} 中找到机会数组（支持 opportunities / clusters[].merged）")


def score_all(profile, opps, seen_index=None, today=None):
    today = today or dt.date.today()
    results, excluded = [], []

    for opp in opps:
        if not isinstance(opp, dict):
            continue
        el_score, verdict, el_reasons, needs_llm = eligibility_component(opp, profile, today)
        comp = {
            "eligibility": el_score,
            "goal_fit": goal_component(opp, profile)[0],
            "skill_fit": skill_component(opp, profile)[0],
            "interest_fit": interest_component(opp, profile)[0],
            "location_fit": location_component(opp, profile)[0],
            "value_fit": value_component(opp, profile)[0],
            "trust": trust_component(opp)[0],
            "novelty": novelty_component(opp, seen_index)[0],
        }
        match = round(sum(WEIGHTS[k] * v for k, v in comp.items()))

        d = days_until(opp.get("deadline"), today)
        ug = urgency_score(d)
        flags, warnings = [], []

        if verdict == "Ineligible":
            excluded.append({"id": opp.get("id"), "title": opp.get("title"),
                             "reason": "Ineligible: " + "；".join(el_reasons)})
            continue
        if d is not None and d < 0:
            excluded.append({"id": opp.get("id"), "title": opp.get("title"),
                             "reason": f"deadline 已过（{opp.get('deadline')}）"})
            continue

        if d is not None and d <= 14:
            flags.append("urgent")
        hours = parse_hours(opp.get("time_commitment"))
        limit = parse_hours((profile.get("constraints") or {}).get("weekly_time"))
        if hours and limit and hours > limit:
            flags.append("heavy_load")
            warnings.append(f"时间投入（{opp.get('time_commitment')}）超出你的每周上限 {limit:g}h")
        if opp.get("verification_status") == "unverified":
            flags.append("unverified")
            warnings.append("未找到官方确认来源")
        if needs_llm:
            flags.append("needs_semantic_check")
        if (opp.get("language_requirement") in (None, [], {})):
            flags.append("language_unspecified")
            warnings.append("页面未写明语言要求")

        priority = round(0.85 * match + 0.15 * ug) if ug is not None else match
        if "heavy_load" in flags:
            priority -= 5
        if "unverified" in flags:
            priority -= 8

        results.append({
            "id": opp.get("id"),
            "title": opp.get("title"),
            "organization": opp.get("organization"),
            "primary_category": opp.get("primary_category"),
            "layer": opp.get("layer"),
            "components": comp,
            "eligibility_verdict": verdict,
            "eligibility_reasons": el_reasons,
            "match_score": match,
            "match_band": band(match),
            "urgency": ug,
            "days_remaining": d,
            "priority_score": priority,
            "priority_band": band(priority),
            "flags": flags,
            "warnings": warnings,
            "reasons": {
                "goal_fit": goal_component(opp, profile)[1],
                "skill_fit": skill_component(opp, profile)[1],
                "interest_fit": interest_component(opp, profile)[1],
                "location_fit": location_component(opp, profile)[1],
                "value_fit": value_component(opp, profile)[1],
                "trust": trust_component(opp)[1],
                "novelty": novelty_component(opp, seen_index)[1],
            },
        })

    results.sort(key=lambda r: (-r["priority_score"], -r["match_score"], str(r["id"])))

    cats = {}
    layers = {}
    for r in results:
        cats[r["primary_category"]] = cats.get(r["primary_category"], 0) + 1
        if r["layer"]:
            layers[r["layer"]] = layers.get(r["layer"], 0) + 1
    diversity = {
        "categories": cats,
        "layers": layers,
        "checks": {
            "categories_ge_3": len(cats) >= 3,
            "has_adjacent": layers.get("adjacent", 0) >= 1,
            "has_explore": layers.get("explore", 0) >= 1,
            "single_category_share_ok": (max(cats.values()) / len(results) <= 0.5) if results else None,
        },
        "note": "配额判定见 references/ranking.md §3；未通过的项需由 Agent 在最终结果里显式补足或说明",
    }

    return {
        "params": {"weights": WEIGHTS, "priority_formula": "0.85*match + 0.15*urgency",
                   "today": today.isoformat(),
                   "disclaimer": "确定性打分，仅作排序辅助；展示时请用档次 + 理由，不要展示裸分数当结论"},
        "scored": len(results),
        "results": results,
        "excluded": excluded,
        "diversity": diversity,
    }


def render_table(res):
    out = ["| # | 机会 | 类别 | Match | 紧迫 | Priority | 档 | 资格 | 主要理由 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(res["results"], 1):
        reason = r["reasons"]["interest_fit"] if r["components"]["skill_fit"] < 50 else r["reasons"]["goal_fit"]
        out.append(f"| {i} | {r['title']} | {r['primary_category']} | {r['match_score']} "
                   f"| {'' if r['urgency'] is None else int(r['urgency'])} | {r['priority_score']} "
                   f"| {r['priority_band']} | {r['eligibility_verdict']} | {reason} |")
    if res["excluded"]:
        out.append("")
        out.append("已排除：")
        for e in res["excluded"]:
            out.append(f"- {e['id']}: {e['reason']}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Opportunity 匹配度/优先级确定性打分（决策辅助）")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--opportunities", required=True)
    ap.add_argument("--seen", help="seen.json，用于 novelty 与重复处理")
    ap.add_argument("--today", help="参照日期 YYYY-MM-DD，默认今天")
    ap.add_argument("--output")
    ap.add_argument("--format", choices=["json", "table"], default="json")
    args = ap.parse_args(argv)

    profile = load_json(args.profile)
    opps = load_list(args.opportunities)
    seen_index = None
    if args.seen and os.path.exists(args.seen):
        seen_index = {k: v.get("status") for k, v in (load_json(args.seen).get("entries") or {}).items()}

    today = dt.date.fromisoformat(args.today) if args.today else None
    res = score_all(profile, opps, seen_index, today)
    payload = render_table(res) if args.format == "table" else json.dumps(res, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print(f"写入 {args.output}（scored={res['scored']} excluded={len(res['excluded'])}）", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
