#!/usr/bin/env python3
"""locales.py - 运行时决定搜索语言、要加载的区域知识，以及搜索矩阵骨架。

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
    is_explicit_none,
)

#: 中日韩文字的国家名（"德国""日本"）：CJK 没有词边界，子串匹配是安全的（国家名足够独特），
#: 而拉丁文单词不能这么做（"in" 会命中无数普通词）。
_CJK_COUNTRY_ALIASES = tuple(sorted(
    (a for a in COUNTRY_ALIASES if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", a)),
    key=len, reverse=True))

#: 多词拉丁文别名（"United States" / "South Korea" / "Great Britain"）：
#: 只按**多词**匹配，单词仍然整词匹配 —— 否则 "in"、"us"、"no" 这类短词会造成大量误识别。
_ASCII_MULTIWORD_ALIASES = tuple(sorted(
    (a for a in COUNTRY_ALIASES if " " in a and re.fullmatch(r"[A-Za-z ]+", a)),
    key=len, reverse=True))

# ---------------------------------------------------------------- 地名（省/市级）
#
# Benchmark/彩排失败驱动：用户说"在杭州读书，不想去太远"时，国家级解析丢失了城市意图，
# 搜索 query 里也不会带"杭州"。这张表是**保守的种子表**（不是地理数据库）：
#   * 中国：省级行政区 + 主要城市（CJK 名唯一性强，子串匹配安全）
#   * 国际：少数知名城市（拉丁名只做整词匹配，避免 "paris"/"austin" 这类同名误判）
# 没有列出的地名走 unknown passthrough，由 Agent 结构化传入。
PLACES = {
    # ---- 中国：省级 ----
    "北京": ("china", "province"), "上海": ("china", "province"), "天津": ("china", "province"),
    "重庆": ("china", "province"), "河北": ("china", "province"), "山西": ("china", "province"),
    "辽宁": ("china", "province"), "吉林": ("china", "province"), "黑龙江": ("china", "province"),
    "江苏": ("china", "province"), "浙江": ("china", "province"), "安徽": ("china", "province"),
    "福建": ("china", "province"), "江西": ("china", "province"), "山东": ("china", "province"),
    "河南": ("china", "province"), "湖北": ("china", "province"), "湖南": ("china", "province"),
    "广东": ("china", "province"), "海南": ("china", "province"), "四川": ("china", "province"),
    "贵州": ("china", "province"), "云南": ("china", "province"), "陕西": ("china", "province"),
    "甘肃": ("china", "province"), "青海": ("china", "province"), "广西": ("china", "province"),
    "内蒙古": ("china", "province"), "新疆": ("china", "province"), "西藏": ("china", "province"),
    "宁夏": ("china", "province"),
    # ---- 中国：主要城市 ----
    "杭州": ("china", "city"), "宁波": ("china", "city"), "温州": ("china", "city"),
    "南京": ("china", "city"), "苏州": ("china", "city"), "无锡": ("china", "city"),
    "广州": ("china", "city"), "深圳": ("china", "city"), "东莞": ("china", "city"),
    "成都": ("china", "city"), "武汉": ("china", "city"), "西安": ("china", "city"),
    "青岛": ("china", "city"), "厦门": ("china", "city"), "大连": ("china", "city"),
    "沈阳": ("china", "city"), "哈尔滨": ("china", "city"), "长春": ("china", "city"),
    "长沙": ("china", "city"), "郑州": ("china", "city"), "合肥": ("china", "city"),
    "福州": ("china", "city"), "济南": ("china", "city"), "昆明": ("china", "city"),
    # ---- 中国：多省区域短语 ----
    "江浙沪": ("china", "region"), "长三角": ("china", "region"), "珠三角": ("china", "region"),
    "大湾区": ("china", "region"), "京津冀": ("china", "region"),
    # ---- 国际：知名城市（拉丁名整词匹配）----
    "tokyo": ("japan", "city"), "osaka": ("japan", "city"), "nagoya": ("japan", "city"),
    "kyoto": ("japan", "city"), "sendai": ("japan", "city"), "fukuoka": ("japan", "city"),
    "berlin": ("germany", "city"), "munich": ("germany", "city"), "hamburg": ("germany", "city"),
    "heidelberg": ("germany", "city"), "frankfurt": ("germany", "city"),
    "paris": ("france", "city"), "lyon": ("france", "city"),
    "london": ("uk", "city"), "manchester": ("uk", "city"), "edinburgh": ("uk", "city"),
    "seoul": ("korea", "city"),
    "new york": ("us", "city"), "san francisco": ("us", "city"), "boston": ("us", "city"),
    "seattle": ("us", "city"), "chicago": ("us", "city"), "austin": ("us", "city"),
    "amsterdam": ("netherlands", "city"), "zurich": ("switzerland", "city"),
    # ---- 国际城市的 CJK 写法 ----
    "东京": ("japan", "city"), "大阪": ("japan", "city"), "名古屋": ("japan", "city"),
    "京都": ("japan", "city"), "仙台": ("japan", "city"), "福冈": ("japan", "city"),
    "柏林": ("germany", "city"), "慕尼黑": ("germany", "city"), "海德堡": ("germany", "city"),
    "巴黎": ("france", "city"), "里昂": ("france", "city"),
    "伦敦": ("uk", "city"), "曼彻斯特": ("uk", "city"), "爱丁堡": ("uk", "city"),
    "首尔": ("korea", "city"), "阿姆斯特丹": ("netherlands", "city"), "苏黎世": ("switzerland", "city"),
}

#: 拉丁多词地名（子串匹配安全）
_PLACE_MULTIWORD = tuple(sorted((a for a in PLACES if " " in a), key=len, reverse=True))
#: 拉丁单词地名（整词匹配）
_PLACE_LATIN_WORD = tuple(sorted((a for a in PLACES if re.fullmatch(r"[a-z]+", a)), key=len, reverse=True))
#: CJK 地名（子串匹配安全）
_PLACE_CJK = tuple(sorted((a for a in PLACES if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", a)),
                          key=len, reverse=True))


def resolve_places(text) -> list:
    """从文本中识别省/市级地名 → [{name, country, level}]（保守：拉丁单词必须整词）。"""
    out: list = []
    low = " " + str(text or "").lower() + " "

    def add(name):
        if name not in [p["name"] for p in out]:
            country, level = PLACES[name]
            out.append({"name": name, "country": country, "level": level})

    for a in _PLACE_MULTIWORD:
        if a in low:
            add(a)
    for w in re.findall(r"[a-z]+", low):
        if w in _PLACE_LATIN_WORD:
            add(w)
    for a in _PLACE_CJK:
        if a in text:
            add(a)
    return out

#: 目标地区 → 搜索语言。primary 为该地区的当地语言，secondary 是"有国际项目价值时"的补充。
#: 这张表可以按需扩展；**没有列出的国家不受影响**（见 resolve_locales 的 unknown 处理）。
REGION_LOCALES = {
    "china": {"primary": "zh-CN", "optional": ["en"]},
    "japan": {"primary": "ja-JP", "optional": ["en"]},
    "korea": {"primary": "ko-KR", "optional": ["en"]},
    "germany": {"primary": "de-DE", "optional": ["en"]},
    "austria": {"primary": "de-AT", "optional": ["en"]},
    "switzerland": {"primary": "de-CH", "optional": ["fr-CH", "en"]},
    "france": {"primary": "fr-FR", "optional": ["en"]},
    "netherlands": {"primary": "nl-NL", "optional": ["en"]},
    "sweden": {"primary": "sv-SE", "optional": ["en"]},
    "denmark": {"primary": "da-DK", "optional": ["en"]},
    "finland": {"primary": "fi-FI", "optional": ["sv-FI", "en"]},
    "norway": {"primary": "nb-NO", "optional": ["en"]},
    "spain": {"primary": "es-ES", "optional": ["en"]},
    "italy": {"primary": "it-IT", "optional": ["en"]},
    "portugal": {"primary": "pt-PT", "optional": ["en"]},
    "brazil": {"primary": "pt-BR", "optional": ["en"]},
    "india": {"primary": "en-IN", "optional": ["hi-IN"]},
    "singapore": {"primary": "en-SG", "optional": ["zh-CN", "ms-SG"]},
    "us": {"primary": "en-US", "optional": []},
    "uk": {"primary": "en-GB", "optional": []},
    "ireland": {"primary": "en-IE", "optional": []},
    "canada": {"primary": "en-CA", "optional": ["fr-CA"]},
    "australia": {"primary": "en-AU", "optional": []},
    "remote": {"primary": "en", "optional": []},
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


#: 明确表示"全球/远程"目标的写法（出现时不使用学校所在地做 fallback）
_GLOBAL_MARKERS = ("global", "worldwide", "any country", "international", "remote",
                   "全球", "远程", "不限地区", "world wide")

#: 请求里的"覆盖"信号：出现时 request 完全取代画像中的地区偏好
OVERRIDE_MARKERS = ("只找", "仅限", "这次只看", "只看", "只搜", "只考虑",
                    "only", "only in", "exclusively")


def target_regions(profile, request_text: str = "") -> dict:
    """目标地区解析（**precedence，不是合并**）。

    | 来源级别 | 触发 | 行为 |
   ---|---|---|
    | `explicit_override` | 请求明确限定地区（"只找德国"） | 忽略画像里的长期地区偏好 |
    | `explicit_additive` | 请求提到地区但非限定（"德国和荷兰也可以"） | 请求地区在前，画像地区保留在后 |
    | `profile_fallback`  | 请求没有地区 | preferred_country → school_country |
    | `default_remote`    | 什么都没有 | Global/Remote |

    返回 {regions, unknown_regions, place_hints, hints, source, notes}。
    `place_hints` 是省/市级地名（如 "杭州"、"浙江"、"江浙沪"、"东京"），供搜索 query 直接使用 ——
    **地区和搜索语言之外，还要把地名带进 query**，否则城市意图会丢失。

    职责边界：本函数只做 **canonicalization + 已知别名解析**（best-effort）；
    从复杂自然语言里提取地理意图是宿主 Agent 的语义层职责 —— 请把解析结果通过
    `--countries` / `preferred_country` 结构化传入，未知国家会被原样保留为 hint。
    """
    notes: list[str] = []
    unknown: list[str] = []
    req = str(request_text or "")

    def known_in(text):
        out = []

        def add(c):
            if c and c not in out:
                out.append(c)

        # 拉丁文单词：整词匹配（避免把普通单词当国家）
        for token in re.findall(r"[A-Za-z]{2,}", text):
            add(canonical_country(token))
        # 拉丁文多词别名：子串匹配（"United States" / "South Korea" / "Great Britain"）
        low = text.lower()
        for alias in _ASCII_MULTIWORD_ALIASES:
            if alias in low:
                add(COUNTRY_ALIASES[alias])
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
    # 省/市级地名：来自请求文本 + 结构化偏好（preferred_city / preferred_region）
    req_places = resolve_places(req)
    city_raw = [str(x) for x in as_list(cons.get("preferred_city"))]
    region_raw = [str(x) for x in as_list(cons.get("preferred_region"))]
    pref_places = resolve_places("、".join(city_raw + region_raw))
    place_unknown = [x for x in (city_raw + region_raw)
                     if x not in {p["name"] for p in pref_places}]
    unknown = list(dict.fromkeys(unknown + place_unknown))
    place_hints = ([p["name"] for p in req_places]
                   + [p["name"] for p in pref_places]
                   + place_unknown)
    place_hints = list(dict.fromkeys(place_hints))

    # preferred_country 一旦声明（哪怕全部未收录）就独占；school_country 只是 fallback，
    # 不会被追加成第二个搜索目标。
    # preferred_country / preferred_city / preferred_region 任一声明都算显式偏好
    declared = bool(pref_raw) or bool(city_raw) or bool(region_raw)
    remote_ok = bool((profile.get("constraints") or {}).get("remote"))
    global_pref = any(str(x).strip().lower() in _GLOBAL_MARKERS for x in pref_raw)

    req_known = known_in(req)
    is_override = (req_known or req_places) and any(m in req.lower() for m in OVERRIDE_MARKERS)

    req_countries = list(req_known) + [p["country"] for p in req_places
                                        if p["country"] not in req_known]

    if is_override:
        regions, source = req_countries, "explicit_override"
        notes.append("请求明确限定地区（override）→ 画像中的长期地区偏好本轮不参与")
    elif req_countries:
        regions = req_countries + [r for r in (pref + [p["country"] for p in pref_places])
                                   if r not in req_countries]
        source = "explicit_additive"
        notes.append("请求提到地区 → 请求地区优先；画像地区保留在其后，可按语义舍弃")
    elif global_pref:
        # 明确声明了 Global / Worldwide / Remote only → 不使用学校所在地
        regions, source = ["remote"], "global_intent"
        notes.append("画像明确声明全球/远程目标 → 不使用学校所在国作为搜索地区")
    elif declared:
        regions, source = list(pref) + [p["country"] for p in pref_places
                                        if p["country"] not in pref], "profile_fallback"
        if remote_ok and "remote" not in regions:
            # 「国家 + 也可以远程」：国家为主，remote 作为附加目标
            regions = regions + ["remote"]
            notes.append("画像允许远程 → 国家地区为主，remote 作为附加目标")
        if unknown:
            notes.append("preferred_country 中的部分地区未收录在 locale 表中 → "
                         "语言按英文起步并动态检测；地区仍保留在 region_hints")
    elif remote_ok:
        # 没有声明国家，但明确接受远程/全球 → 全球优先，不退回学校所在国
        regions, source = ["remote"], "global_intent"
        notes.append("未声明目标国家但接受远程/全球 → 按 Global/Remote 处理（不退回学校所在国）")
    elif school:
        regions, source = [school], "profile_fallback"
        notes.append("未声明 preferred_country → 用学校所在国作为 fallback")
    elif unknown:
        regions, source = [], "profile_fallback"
        notes.append("画像中的目标地区未收录 → 语言按英文起步并动态检测；"
                     "地区信息保留在 region_hints，搜索时仍以该地区为准")
    else:
        regions, source = ["remote"], "default_remote"
        notes.append("Profile/请求未给出可识别的目标地区 → 按 Global/Remote 处理：以英文为主，"
                     "并根据实际搜到的页面语言动态增加本地语言查询")
    if unknown:
        notes.append("以下地区未收录在 locale 表中，将走通用规则"
                     "（按页面语言动态扩展，功能不受影响）：" + "、".join(unknown))
    # region_hints = 已知地区 + 未收录地区（两者都保留，不能二选一）
    return {"regions": regions, "unknown_regions": unknown,
            "place_hints": place_hints,
            "hints": list(regions) + list(place_hints)
                     + [u for u in unknown if u not in regions],
            "source": source, "notes": notes}


def _locale_for(region: str) -> dict:
    return REGION_LOCALES.get(region, {"primary": "en", "optional": []})


def resolve_locales(profile, request_text: str = "") -> dict:
    """目标地区 → 语言计划 + 需要加载的区域知识文件。

    `optional_locales` 是**候选**而不是必搜清单：当地语言负责本地召回，
    英文只在国际召回有增益时使用（见 references/locales/generic.md §4）。
    画像语言条目只有在**明确具备能力**（level/score 有值且不是 none 标记）时才会
    成为召回语言；只记录名字 ≠ 会用这门语言理解机会。
    """
    tp = target_regions(profile, request_text)
    regions, unknown, notes = tp["regions"], tp["unknown_regions"], list(tp["notes"])

    primary: list[str] = []
    optional: list[str] = []
    files = [GENERIC_LOCALE_FILE]
    for r in regions:
        loc = _locale_for(r)
        # remote 作为**附加**目标时，它的语言（英文）只是候选召回，不提升为主语言
        # （"国家 + 也可以远程" = 国家为主，remote 次之）
        additive_remote = (r == "remote" and len(regions) > 1)
        target = optional if additive_remote else primary
        if loc["primary"] not in target:
            target.append(loc["primary"])
        for s in loc.get("optional", []):
            if s not in optional and s not in primary:
                optional.append(s)
        f = locale_file(r)
        if f and f not in files:
            files.append(f)

    # 画像语言：只有**明确具备**的才作为候选召回语言
    for entry in as_list(profile.get("languages")):
        if not isinstance(entry, dict):
            continue
        lang = entry.get("language")
        if is_explicit_none(entry.get("level")) or is_explicit_none(entry.get("score")):
            notes.append(f"{lang} 在画像中明确标注不具备 → 不作为召回语言")
            continue
        has_ability = any(str(entry.get(k) or "").strip() for k in ("level", "score"))
        tag = _language_tag(lang)
        if not has_ability:
            if tag:
                notes.append(f"{lang} 只记录了名字、没有等级/分数 → 无法确认可用于搜索，"
                             "不加入召回语言")
            continue
        if tag and tag not in primary and tag not in optional:
            optional.append(tag)
            notes.append(f"画像中记录了 {lang}（明确具备）→ 作为候选召回语言（非默认）")

    # 同一语言只保留地区变体：同时出现 "en" 与 "en-US" 时丢弃裸 "en"
    def drop_bare(locales, reference):
        specific = {l.split("-")[0] for l in reference if "-" in l}
        return [l for l in locales if "-" in l or l not in specific]

    primary = drop_bare(primary, primary)
    optional = [s for s in drop_bare(optional, primary + optional) if s not in primary]
    if not primary:
        primary = ["en"]
    return {"regions": regions, "unknown_regions": unknown,
            "region_hints": tp["hints"], "place_hints": tp["place_hints"],
            "region_source": tp["source"],
            "primary_locales": primary, "optional_locales": optional,
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
        "place_hints": loc["place_hints"],
        "region_source": loc["region_source"],
        "primary_locales": loc["primary_locales"],
        "optional_locales": loc["optional_locales"],
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
           + (f"  (place hints: {', '.join(plan['place_hints'])})" if plan.get('place_hints') else "")
           + (f"  (未收录地区，按通用规则处理: {', '.join(plan['unknown_regions'])})"
              if plan["unknown_regions"] else ""),
           f"primary locales: {', '.join(plan['primary_locales'])}",
           f"optional locales: {', '.join(plan['optional_locales']) or '（无）'} （候选，非必搜）",
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
