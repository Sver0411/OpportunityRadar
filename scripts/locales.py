#!/usr/bin/env python3
"""locale.py - 运行时决定搜索语言、要加载的区域知识，以及搜索矩阵骨架。

**Core 不知道用户来自哪里。** 目标地区来自 profile / 当前请求，语言随之推导；
英文只是"提升国际召回"时的补充，不是无条件默认；没有对应区域文件的国家照样能工作。

三条原则：
  1. Search language follows opportunity geography, not developer preference.
  2. Core works without country-specific rules; locale files only improve recall.
  3. Unknown region → 走通用规则 + 根据页面/结果的语言动态扩展，不报错、不猜。

用法：
  python3 scripts/locales.py --profile examples/profiles/cs-student.example.json
  python3 scripts/locales.py --countries "Germany,Netherlands" --mode A
  python3 scripts/locales.py --countries France --format json
  python3 scripts/locales.py --detect "https://example.fr/offres"      # 动态语言检测
  python3 scripts/locales.py --list-locales
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    CATEGORIES, COUNTRY_ALIASES, GOAL_TO_CATEGORY, INTEREST_ALIASES, canonical_country,
)

#: 中日韩文字的国家名（"德国""日本"）：CJK 没有词边界，子串匹配是安全的（国家名足够独特），
#: 而拉丁文单词不能这么做（"in" 会命中无数普通词）。
_CJK_COUNTRY_ALIASES = tuple(sorted(
    (a for a in COUNTRY_ALIASES if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", a)),
    key=len, reverse=True))

#: 目标地区 → 搜索语言。primary 为该地区的当地语言，secondary 是"有国际项目价值时"的补充。
#: 这张表可以按需扩展；**没有列出的国家不受影响**（见 resolve_locales 的 unknown 处理）。
REGION_LOCALES = {
    "china": {"primary": "zh-CN", "secondary": ["en"]},
    "japan": {"primary": "ja-JP", "secondary": ["en"]},
    "korea": {"primary": "ko-KR", "secondary": ["en"]},
    "germany": {"primary": "de-DE", "secondary": ["en"]},
    "austria": {"primary": "de-AT", "secondary": ["en"]},
    "switzerland": {"primary": "de-CH", "secondary": ["fr-CH", "en"]},
    "france": {"primary": "fr-FR", "secondary": ["en"]},
    "netherlands": {"primary": "nl-NL", "secondary": ["en"]},
    "sweden": {"primary": "sv-SE", "secondary": ["en"]},
    "denmark": {"primary": "da-DK", "secondary": ["en"]},
    "finland": {"primary": "fi-FI", "secondary": ["sv-FI", "en"]},
    "norway": {"primary": "nb-NO", "secondary": ["en"]},
    "spain": {"primary": "es-ES", "secondary": ["en"]},
    "italy": {"primary": "it-IT", "secondary": ["en"]},
    "portugal": {"primary": "pt-PT", "secondary": ["en"]},
    "brazil": {"primary": "pt-BR", "secondary": ["en"]},
    "india": {"primary": "en-IN", "secondary": ["hi-IN"]},
    "singapore": {"primary": "en-SG", "secondary": ["zh-CN", "ms-SG"]},
    "us": {"primary": "en-US", "secondary": []},
    "uk": {"primary": "en-GB", "secondary": []},
    "ireland": {"primary": "en-IE", "secondary": []},
    "canada": {"primary": "en-CA", "secondary": ["fr-CA"]},
    "australia": {"primary": "en-AU", "secondary": []},
    "remote": {"primary": "en", "secondary": []},
}

#: 有专门区域知识文件的国家（**增强层**，不是硬依赖）。
LOCALE_FILES = {
    "china": "cn", "japan": "jp", "us": "us", "uk": "uk", "germany": "de",
}

#: 通用规则文件永远加载
GENERIC_LOCALE_FILE = "references/locales/generic.md"


def locale_file(country: str) -> str | None:
    cc = LOCALE_FILES.get(country)
    return f"references/locales/{cc}.md" if cc else None


# ---------------------------------------------------------------- 模式权重

PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.35, None: 0.5}

#: 类别 × 模式 的权重表（单一来源；references/search-strategy.md 的模式表以此为准）
#: A 常规发现 / B 非求职 / C 未知机会 / D 能力反推
MODE_WEIGHTS = {
    "A": {"career": 1.0, "research": 0.8, "competition": 0.8, "education": 0.5,
          "language": 0.5, "skill_development": 0.8, "open_source": 0.8, "hobby": 0.5,
          "funding": 0.8, "event": 0.5, "project": 0.8, "entrepreneurship": 0.5,
          "networking": 0.5},
    "B": {"career": 0.3, "research": 0.7, "competition": 1.0, "education": 0.0,
          "language": 0.5, "skill_development": 1.0, "open_source": 1.0, "hobby": 1.0,
          "funding": 0.7, "event": 1.0, "project": 1.0, "entrepreneurship": 0.7,
          "networking": 0.7},
    "C": {"career": 0.7, "research": 0.7, "competition": 0.7, "education": 0.5,
          "language": 0.5, "skill_development": 0.7, "open_source": 1.0, "hobby": 0.7,
          "funding": 0.7, "event": 0.7, "project": 1.0, "entrepreneurship": 0.7,
          "networking": 1.0},
    "D": {"career": 1.0, "research": 0.7, "competition": 1.0, "education": 0.5,
          "language": 0.7, "skill_development": 1.0, "open_source": 1.0, "hobby": 0.3,
          "funding": 0.7, "event": 0.7, "project": 1.0, "entrepreneurship": 0.3,
          "networking": 0.7},
}

#: 各模式的层配比（exploit / adjacent / explore）
MODE_LAYERS = {
    "A": {"exploit": 0.70, "adjacent": 0.20, "explore": 0.10},
    "B": {"exploit": 0.60, "adjacent": 0.25, "explore": 0.15},
    "C": {"exploit": 0.55, "adjacent": 0.25, "explore": 0.20},
    "D": {"exploit": 0.60, "adjacent": 0.25, "explore": 0.15},
}


# ---------------------------------------------------------------- 目标地区

def as_list(v):
    if v in (None, "", [], {}):
        return []
    return v if isinstance(v, list) else [v]


def target_regions(profile, request_text: str = "") -> tuple:
    """从 profile / 当前请求解析目标地区（规范化的国家值）。

    优先级：当前请求中**可识别**的地区 > constraints.preferred_country >
    学校所在国 > （都没有）Global/Remote。
    返回 (regions, unknown_regions, notes)。

    注意：请求文本里只接受**能被 canonical_country 识别**的地区名，不会把普通英文单词
    误当成"未知地区"（没有地理词库就无法判断 "Finland" 是国家名还是别的词 ——
    这种情况下走 Global/Remote + 动态语言检测，不猜）。
    """
    notes: list[str] = []
    unknown: list[str] = []
    req = str(request_text or "")

    def known_in(text):
        out = []

        def add(c):
            if c and c not in out:
                out.append(c)

        # 拉丁文：整词匹配（避免把普通单词当国家）
        for token in re.findall(r"[A-Za-z]{2,}", text):
            add(canonical_country(token))
        # CJK：子串匹配（"我想找德国的实习" 里没有空格可分）
        for alias in _CJK_COUNTRY_ALIASES:
            if alias in text:
                add(COUNTRY_ALIASES[alias])
        return out

    cons = profile.get("constraints") or {}
    pref_raw = [str(x) for x in as_list(cons.get("preferred_country"))]
    pref, unknown = [], []
    for raw in pref_raw:
        c = canonical_country(raw)
        (pref if c else unknown).append(c if c else raw)
    school = canonical_country((profile.get("education") or {}).get("school_country"))

    regions: list[str] = []
    for group in (known_in(req), pref, [school] if school else []):
        for c in group:
            if c and c not in regions:
                regions.append(c)

    if not regions:
        regions = ["remote"]
        notes.append("Profile/请求未给出可识别的目标地区 → 按 Global/Remote 处理：以英文为主，"
                     "并根据实际搜到的页面语言动态增加本地语言查询")
    if unknown:
        notes.append("以下偏好地区未收录在 locale 表中，将走通用规则"
                     "（按页面语言动态扩展，功能不受影响）：" + "、".join(unknown))
    return regions, unknown, notes


def _locale_for(region: str) -> dict:
    return REGION_LOCALES.get(region, {"primary": "en", "secondary": []})


def resolve_locales(profile, request_text: str = "") -> dict:
    """目标地区 → 语言计划 + 需要加载的区域知识文件。"""
    regions, unknown, notes = target_regions(profile, request_text)

    primary: list[str] = []
    secondary: list[str] = []
    files = [GENERIC_LOCALE_FILE]
    for r in regions:
        loc = _locale_for(r)
        if loc["primary"] not in primary:
            primary.append(loc["primary"])
        for s in loc.get("secondary", []):
            if s not in secondary and s not in primary:
                secondary.append(s)
        f = locale_file(r)
        if f and f not in files:
            files.append(f)

    # 用户明确具备的语言：作为补充召回（不做默认语言）
    for entry in as_list(profile.get("languages")):
        if not isinstance(entry, dict):
            continue
        tag = _language_tag(entry.get("language"))
        if tag and tag not in primary and tag not in secondary:
            secondary.append(tag)
            notes.append(f"画像中记录了 {entry.get('language')} → 作为补充召回语言（非默认）")

    # 同一语言只保留地区变体：同时出现 "en" 与 "en-US" 时丢弃裸 "en"
    def drop_bare(locales, reference):
        specific = {l.split("-")[0] for l in reference if "-" in l}
        return [l for l in locales if "-" in l or l not in specific]

    primary = drop_bare(primary, primary)
    secondary = [s for s in drop_bare(secondary, primary + secondary) if s not in primary]
    if not primary:
        primary = ["en"]
    return {"regions": regions, "unknown_regions": unknown,
            "region_hints": unknown or regions,
            "primary_locales": primary, "secondary_locales": secondary,
            "load_files": files, "notes": notes}


#: 语言名（英文/中文/日文写法）→ BCP-47 近似标签。仅用于补充召回，不做区域假设。
LANGUAGE_TAGS = {
    "japanese": "ja-JP", "日本語": "ja-JP", "日语": "ja-JP",
    "english": "en", "英語": "en", "英语": "en",
    "chinese": "zh-CN", "中文": "zh-CN", "汉语": "zh-CN",
    "korean": "ko-KR", "한국어": "ko-KR", "韩语": "ko-KR",
    "german": "de-DE", "deutsch": "de-DE", "德语": "de-DE",
    "french": "fr-FR", "français": "fr-FR", "法语": "fr-FR",
    "spanish": "es-ES", "español": "es-ES", "西班牙语": "es-ES",
    "italian": "it-IT", "italiano": "it-IT",
    "portuguese": "pt-PT", "português": "pt-PT",
    "russian": "ru-RU", "俄语": "ru-RU",
    "arabic": "ar", "hindi": "hi-IN",
}


def _language_tag(name) -> str | None:
    if not name:
        return None
    return LANGUAGE_TAGS.get(str(name).strip().lower())


# ---------------------------------------------------------------- 动态语言检测

#: 顶级域名 → locale（用于"搜到哪个地区的站点"这类动态判断）
TLD_LOCALES = {
    "jp": "ja-JP", "cn": "zh-CN", "kr": "ko-KR", "de": "de-DE", "at": "de-AT",
    "ch": "de-CH", "fr": "fr-FR", "nl": "nl-NL", "se": "sv-SE", "dk": "da-DK",
    "fi": "fi-FI", "no": "nb-NO", "es": "es-ES", "it": "it-IT", "pt": "pt-PT",
    "br": "pt-BR", "ru": "ru-RU", "in": "en-IN", "sg": "en-SG", "uk": "en-GB",
    "us": "en-US", "ca": "en-CA", "au": "en-AU",
}

#: 路径前缀 / 语言切换链接里的语言代码
PATH_PREFIX_LOCALES = {"ja": "ja-JP", "zh": "zh-CN", "ko": "ko-KR", "de": "de-DE",
                       "fr": "fr-FR", "nl": "nl-NL", "es": "es-ES", "it": "it-IT",
                       "pt": "pt-PT", "sv": "sv-SE", "da": "da-DK", "fi": "fi-FI",
                       "nb": "nb-NO", "ru": "ru-RU", "en": "en"}


def detect_locale(text: str) -> dict:
    """从 URL 或页面文本推测语言（用于"发现页面后扩展下一轮 query"）。

    只做高置信度判断：域名后缀 > 路径语言前缀 > 文字系统 > 无结论。
    无法判断时返回 locale=None，交给通用规则，不猜。
    """
    s = str(text or "")
    if not s.strip():
        return {"locale": None, "reason": "空输入"}

    m = re.search(r"https?://([^/\s]+)(/[^\s]*)?", s)
    host = (m.group(1) if m else "").lower()
    path = (m.group(2) if m else "").lower()
    if host:
        tld = host.rsplit(".", 1)[-1]
        if tld in TLD_LOCALES:
            return {"locale": TLD_LOCALES[tld], "reason": f"域名后缀 .{tld}"}
        m2 = re.match(r"^/([a-z]{2})(?:/|$)", path)
        if m2 and m2.group(1) in PATH_PREFIX_LOCALES:
            return {"locale": PATH_PREFIX_LOCALES[m2.group(1)], "reason": f"路径前缀 /{m2.group(1)}/"}

    scripts = [
        ("ja-JP", r"[\u3040-\u309f\u30a0-\u30ff]", "含假名"),
        ("ko-KR", r"[\uac00-\ud7af]", "含谚文"),
        ("ru-RU", r"[\u0400-\u04ff]", "含西里尔字母"),
        ("ar", r"[\u0600-\u06ff]", "含阿拉伯字母"),
        ("hi-IN", r"[\u0900-\u097f]", "含天城文"),
        ("th-TH", r"[\u0e00-\u0e7f]", "含泰文"),
        ("zh-CN", r"[\u4e00-\u9fff]", "含汉字（无假名 → 按中文处理）"),
    ]
    for locale, rx, reason in scripts:
        if re.search(rx, s):
            return {"locale": locale, "reason": reason}
    if re.search(r"[A-Za-z]{4,}", s):
        return {"locale": None, "reason": "仅拉丁字母，无法区分语言 → 按结果质量决定是否补充本地语言"}
    return {"locale": None, "reason": "无法判断语言"}


# ---------------------------------------------------------------- 搜索矩阵骨架

def interest_keywords(profile, limit: int = 24) -> list:
    """只从 **profile 的兴趣** 生成扩展关键词。

    没有 IoT/Embedded 信号就绝不会生成 ESP32/TinyML —— 这是"不替用户预设路线"的保证。
    """
    out: list[str] = []
    for interest in as_list(profile.get("interests")):
        key = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", str(interest).lower()).strip()
        key = key.replace(" ", "_")
        aliases = INTEREST_ALIASES.get(key)
        if aliases is None:
            for k in INTEREST_ALIASES:
                if k in key or key in k:
                    aliases = INTEREST_ALIASES[k]
                    break
        for token in (aliases or [str(interest)]):
            if token not in out:
                out.append(token)
        if len(out) >= limit:
            break
    return out[:limit]


def search_plan(profile, mode: str = "A", request_text: str = "") -> dict:
    """搜索矩阵骨架：地区 → 语言 → 类别权重 → 层配比 → 兴趣关键词。"""
    mode = (mode or "A").upper()
    if mode not in MODE_WEIGHTS:
        mode = "A"
    loc = resolve_locales(profile, request_text)
    weights = MODE_WEIGHTS[mode]

    goals = [g for g in as_list(profile.get("goals")) if isinstance(g, dict)]
    cat_weight: dict = {}
    for c in CATEGORIES:
        base = 0.15                       # 未被目标覆盖的类别保留少量探索权重
        for g in goals:
            if c in GOAL_TO_CATEGORY.get(g.get("type"), []):
                base = max(base, PRIORITY_WEIGHT.get(g.get("priority"), 0.5))
        cat_weight[c] = round(base * weights.get(c, 0.5), 3)

    categories = [c for c in sorted(cat_weight, key=lambda k: (-cat_weight[k], k))
                  if cat_weight[c] > 0]
    notes = list(loc["notes"])
    notes.append(f"模式 {mode}：层配比 "
                 f"{int(MODE_LAYERS[mode]['exploit'] * 100)}/{int(MODE_LAYERS[mode]['adjacent'] * 100)}"
                 f"/{int(MODE_LAYERS[mode]['explore'] * 100)}（exploit/adjacent/explore）")
    if not goals:
        notes.append("未提供 goals → 全部类别保留探索权重，由模式与兴趣决定优先级")
    notes.append("interest_keywords 供语义匹配/扩词使用；实际 query 需按上面的 locale 本地化")
    return {
        "mode": mode,
        "regions": loc["regions"],
        "unknown_regions": loc["unknown_regions"],
        "region_hints": loc["region_hints"],
        "primary_locales": loc["primary_locales"],
        "secondary_locales": loc["secondary_locales"],
        "load_files": loc["load_files"],
        "categories": categories,
        "category_weights": cat_weight,
        "layer_ratios": MODE_LAYERS[mode],
        "interest_keywords": interest_keywords(profile),
        "notes": notes,
    }


# ---------------------------------------------------------------- CLI

def _render_text(plan: dict) -> str:
    out = [f"mode: {plan['mode']}",
           f"regions: {', '.join(plan['regions'])}"
           + (f"  (未收录地区，按通用规则处理: {', '.join(plan['unknown_regions'])})"
              if plan["unknown_regions"] else ""),
           f"primary locales: {', '.join(plan['primary_locales'])}",
           f"secondary locales: {', '.join(plan['secondary_locales']) or '（无）'}",
           "load files:",
           *[f"  - {f}" for f in plan["load_files"]],
           f"categories ({len(plan['categories'])}): " + ", ".join(plan["categories"][:8])
           + (" …" if len(plan["categories"]) > 8 else ""),
           f"interest keywords: {', '.join(plan['interest_keywords']) or '（画像未提供兴趣）'}",
           "notes:"]
    out += [f"  · {n}" for n in plan["notes"]]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="运行时决定搜索语言与要加载的区域知识")
    ap.add_argument("--profile", help="画像 JSON 路径")
    ap.add_argument("--countries", help="逗号分隔的目标地区（无 profile 时使用）")
    ap.add_argument("--request", default="", help="当前请求原文（可从中识别目标地区）")
    ap.add_argument("--mode", default="A", choices=["A", "B", "C", "D"])
    ap.add_argument("--detect", help="从 URL/页面文本推测语言")
    ap.add_argument("--list-locales", action="store_true", help="列出已收录的地区与区域文件")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args(argv)

    if args.detect:
        res = detect_locale(args.detect)
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.format == "json"
              else f"{res['locale'] or '(无法判断)'} ← {res['reason']}")
        return 0

    if args.list_locales:
        rows = [f"{cc:<12} {v['primary']:<8} {'/'.join(v['secondary']) or '-':<16} "
                f"{locale_file(cc) or '(仅通用规则)'}" for cc, v in sorted(REGION_LOCALES.items())]
        print("region       primary  secondary        knowledge file")
        print("\n".join(rows))
        print(f"\n未收录地区一律走 {GENERIC_LOCALE_FILE} + 动态语言检测。")
        return 0

    if args.profile:
        with open(args.profile, encoding="utf-8") as fh:
            profile = json.load(fh)
    elif args.countries:
        profile = {"constraints": {"preferred_country": args.countries.split(",")}}
    else:
        ap.error("需要 --profile 或 --countries（或用 --detect / --list-locales）")

    plan = search_plan(profile, args.mode, args.request)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if args.format == "json"
          else _render_text(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
