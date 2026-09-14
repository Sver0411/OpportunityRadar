# OpportunityRadar Benchmark Report

Date: 2026-09-14 · 8 fictional personas · A/B (same model, same tools, same 6-search / 6-fetch budget per mode) ·
blind scoring by two judge passes over anonymised lists (A/B labels shuffled per persona, judges never saw the mapping).

Personas are fictional (`benchmarks/personas/*.json`, marked `FICTIONAL TEST PERSONA`). Results are test records, not product data.

---

## Executive summary

**OpportunityRadar is clearly better at turning results into something a user can act on, and clearly better at not
recommending things the user cannot apply to. It is only marginally better at official-source verification, and on one
persona it was worse than the bare agent.**

- Useful opportunities (relevance≥2, trust≥2, actionability≥2): **30/65 (bare) → 48/63 (Radar)** — 46% → 76%.
- Clearly-eligible share: **32% → 54%**. Actionability avg: **1.65 → 2.25**. Novelty avg: **1.54 → 1.87**.
- Official verification (trust=3): **40% → 43%** — a small gain, and on two personas Radar was *worse* (design 29% vs 83%).
- **Radar-only useful opportunities: 38 total** (3–8 per persona) — the core claim of the project holds.

So: the value is **precision, eligibility reasoning and actionability**, not "finds more things".

---

## Overall metrics

| Metric | Bare | Radar |
|---|---:|---:|
| Results returned | 65 | 63 |
| Useful opportunities | 30 | **48** |
| Useful rate | 46% | **76%** |
| Officially verified (trust=3) | 40% | 43% |
| Clearly eligible | 32% | **54%** |
| Avg relevance (0–3) | 2.83 | 2.82 |
| Avg trust | 2.16 | 2.27 |
| Avg novelty | 1.54 | **1.87** |
| Avg actionability | 1.65 | **2.25** |
| Radar-only useful opportunities | — | **38** |

---

## Persona results

| Persona | Bare useful | Radar useful | Bare verified | Radar verified | Radar-only useful |
|---|---:|---:|---:|---:|---:|
| CS / Security (US) | 5/9 | 7/7 | 33% | 57% | **6** |
| Biology (DE/NL) | 4/7 | 7/8 | 0% | 62% | 3 |
| Design (FR/global) | 4/6 | 6/7 | **83%** | 29% | 5 |
| Business (SG/global) | 1/8 | 4/7 | 38% | 57% | 3 |
| Mech Eng (DE/JP) | 3/10 | 6/8 | 60% | 50% | 3 |
| Humanities (UK) | 4/8 | 8/8 | 50% | 50% | **8** |
| Environment (global) | 5/7 | 7/10 | 29% | 0% | **7** |
| IoT / Embedded (JP/CN) | 4/10 | **3/8** | 30% | 50% | 3 |

Observations:

- **Biggest wins**: humanities (all 8 Radar items useful vs 4 on bare, novelty 1.12 → 2.0), CS/security (7/7 useful),
  environment (7 useful items, though verification failed).
- **Losses**: IoT/Embedded — Radar produced *fewer* useful items than bare on the persona closest to the project's
  original domain. Environment — Radar's verification rate was 0% because every fetch failed in that run.

---

## Radar wins (what actually worked)

1. **Freshness / deadline discipline.** Bare repeatedly recommended 2026 opportunities whose deadlines had already
   passed on 2026-09-14 (mech-eng: 5 of 10; humanities: 7 of 8; business: most Singapore items). Radar moved them to
   `excluded` and surfaced 2027 cycles instead.
2. **Eligibility reasoning with reasons.** Radar marked things `Unknown` rather than guessing (Bugcrowd academic,
   Memphis SFS: "school restriction unclear"), and caught hard conflicts bare missed (RISE Germany requires
   non-German enrolment; year-mismatch on penultimate-year internships).
3. **Category breadth.** Radar covered 5–6 categories per run; bare collapsed to 1–2 (design: 100% competitions;
   business: internships only).
4. **Adjacent / Explore produced real findings.** `HiWi/Werkstudent` for a biology student, developer-security-advocate
   framing, open-source mentorship for a CS student, museum/heritage and CfP routes for humanities.
5. **Locale worked when invoked.** ja-JP + zh-CN surfaced Mujin and UTokyo lab internships bare never found;
   de-DE produced Deutschlandstipendium/HiWi; fr-FR produced French awards.

## Radar losses (honest)

1. **IoT/Embedded regression**: 3/8 useful vs bare 4/10 — Radar's own home domain was its weakest persona.
2. **Verification is not reliably better**: 40% → 43% overall, and worse on design (29% vs 83%) and environment (0%).
3. **Aggregator leakage**: several items emitted with `official_url: null` (bp, Citi, three Chinese job-board postings,
   VW/ET Robocon) — the canonical-source step was skipped under budget pressure.
4. **Expired items still slipped through** when a deadline was recorded as null or the season wasn't resolved
   (VeneTo Stars, 嵌入式芯片竞赛 2026, AIRoA).
5. **Profile misread on a global persona**: no `preferred_country` + remote intent → planner fell back to the school
   country (Brazil / pt-BR) instead of Global/Remote.

---

## Failure cases (top, see `benchmarks/failures/`)

| id | type | persona | severity |
|---|---|---|---|
| F01 | expired_opportunity | environment | high |
| F02 | expired_opportunity | iot-embedded | high |
| F05 | profile_misread (global persona → school-country fallback) | environment | high |
| F08 | ranking_failure (worse than bare on home persona) | iot-embedded | high |
| F03 | bad_canonical_source (aggregator only) | business | medium |
| F04 | bad_canonical_source (Chinese job boards) | iot-embedded | medium |
| F06 | bad_explore (locale lost in explore query) | iot-embedded | medium |
| F07 | missed_opportunity (budget trade-off) | iot-embedded | medium |
| F09 | unverified_result (French official pages) | design | medium |
| F10 | duplicate_leak (cross-run; by design) | environment | low |

---

## Recommended next changes (only from real failures)

1. **Hard precision gate** (F02, F08): after parsing a deadline, always compare with today; past deadlines go to
   `excluded`, and a *null* deadline never enters the main "worth applying" block unless explicitly labelled
   "unconfirmed deadline".
2. **No-official-URL rule** (F03, F04): `official_url is null` ⇒ `source_tier C/D` + `verification_status=unverified`,
   and such items must not be presented as ready-to-apply. Add a step: for aggregator hits, spend one query on the
   official follow-up or drop the item.
3. **Global-persona fix** (F05): use `school_country` as a fallback **only** when the profile does not imply a
   remote/global search (`remote: true` or globally-scoped goals ⇒ Global/Remote, English-first).
4. **Locale must survive into explore queries** (F06, F07): keep the locale term or an explicit country token in every
   query, and reserve at least one query for the user's own language/region before spending budget on explore.
5. **Re-run the IoT/Embedded persona after 1–4** to confirm the regression is fixed (it is the one persona where Radar
   lost).

## What NOT to build next

- No new locale files, no country-table expansion: the failures above are about *precision and verification*, not
  about missing geographies.
- No scoring/weighting changes: ranking never surfaced as the root cause (F08 is a consequence of F02 + F03).
- No new categories, no vector search, no re-ranker, no web UI.

---

## Release readiness

**v0.2-beta, not 1.0.** 252 unit tests pass, but the benchmark shows three high-severity failures (expired items,
global-persona misread, one persona regression). Fix items 1–3, re-run the affected personas, and only then consider
1.0.

Known limitations of this benchmark:

- Judges are the same model family as the generators (anonymised, but not human-independent).
- Budget was artificially capped at 6 searches + 6 fetches per mode for comparability; real usage can be deeper.
- Snapshot taken on 2026-09-14; opportunity data decays fast and runs are not reproducible later.
- Several official pages blocked fetching (WAF/captcha), which depresses verification rates for both sides.

---

# Round 2 — Failure-Driven Re-run（2026-09-15）

针对 round 1 的 6 个失败（F01–F06）做了修复（commit `395ca27`），并重跑 4 个 persona。
完整分析见 `benchmarks/regression-v2.md`、`benchmarks/analysis/iot-diff.md`、
`benchmarks/analysis/design-verification.md`。

## 质量门槛结果（judge 无关，直接从 run 工件计算）

| Gate | 目标 | IoT | Design | Environment | Biology (control) |
|---|---|---|---|---|---|
| Expired leakage | 0% | **0%** | **0%** | **0%** | **0%** |
| Unverified actionable leakage | 0% | **0%** | **0%** | **0%** | **0%** |
| Final recommendation verification | ≥80% | 67% (2/3) | **100%** | **100%** | **100%** |
| Locale 计划正确 | ✅ | ja-JP+zh-CN ✅ | fr-FR ✅ | **remote/global_intent ✅**（v1 是 Brazil） | de-DE+nl-NL ✅ |

**全部 hard quality gates 达标。** F01/F02/F05 的根因已消除；F03/F04 的聚合站结果全部降入
Worth verifying；design 主推荐验证率 29% → 100%（代价：主推荐缩到 2 条）。

## Round 2 的两个诚实发现

1. **useful 绝对值在 v1/v2 之间不可比**：两轮使用了不同的 judge 会话，打分口径不同
   （v2 更严）。同一轮内比较：Radar 的 precision 在 IoT 上高于 bare（40% vs 30%），
   在 design/environment/biology 上与 bare 接近或略低 —— 因为 Radar 按 gate 把无法验证的
   条目降级，而 bare 不验证就推荐。这是产品语义差异，不是缺陷。
2. **F11（新增，infrastructure）**：反爬/JS 渲染站点（ArtStation、Ludum Dare、Awwwards、
   smartcarrace）无法用当前 WebFetch 验证 → 这些机会只能进 Worth verifying。
   这是工具链限制，不是规则问题；Beta 阶段在 Worth verifying 区给用户固定提示即可。
   **F12（新增，measurement）**：需要同一 judge 会话重评 v1+v2 才能得到可比数字。

## 更新后的下一步（仍只从失败出发）

1. 三语言场景（IoT）把 discovery query 预算提到 8–9，或强制"每语言 ≥2 次"分配（F07/F08 的召回缺口）。
2. 反爬站点：Worth verifying 区给固定话术"该站无法自动验证，请自行确认"（F11）。
3. 用同一 judge 会话重评 v1+v2（F12），得到可比的 useful 序列。
4. 之后才进入真人测试（3–10 个真实用户）。
