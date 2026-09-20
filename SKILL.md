---
name: opportunity-radar
description: 面向学生、研究生和职场新人的个人机会发现 Skill。用户询问“最近有什么适合我的机会”“我现在可以做什么”“有没有适合我的实习、工作、科研、竞赛、开源项目、奖学金或交流项目”，或希望根据自身背景判断下一步时启用；也会寻找用户尚未想到的相关机会。纯定义、考试日期、价格等事实查询不触发，除非用户要求结合自身情况评估。
license: MIT
compatibility: Requires a web-capable host agent (web search plus page fetch or browser) for discovery and verification. Python 3.8+ is needed for the deterministic helpers in scripts/ (standard library only, no network); without it, run Protocol-only Mode and apply the reference rules by hand. No external services, credentials, or paid APIs.
metadata:
  agent_created: "true"
  version: "2.1"
---

# OpportunityRadar

Find the opportunities you didn't know to search for.

A discovery protocol for a web-capable host agent. It turns "帮我搜几个实习" into:

understand user → build search space → expand queries → search across categories →
discover → verify at official sources → extract → dedupe → judge eligibility →
rank → explore adjacents → explain.

The skill reuses the host's web search, fetch, browser, shell and file I/O. It adds the
protocol, taxonomy, policies and deterministic helpers a bare agent does not have.

## Scope

OpportunityRadar covers **discovery, verification, eligibility evaluation, ranking, and
opportunity analysis** for students, graduate students and early-career users.

Application or contact actions (submitting forms, emailing, registering, uploading personal
data) are outside this workflow and should be handed to an appropriate authorized workflow
when one is available.

## Execution modes

Pick the mode that matches the environment, and say which one you used when it affects the result.

| Mode | Availability | Behaviour |
|---|---|---|
| **Full Mode** | Host has Python/shell | Use `scripts/*.py` for dates, dedupe, scoring and state. Deterministic results are reproducible. |
| **Protocol-only Mode** | Host has web access but no shell | Follow the same 13 steps and reference rules by hand. Do **not** claim deterministic dedupe/scoring was run, and do not create local state files. State the limitation in one line, e.g. "在无脚本环境下运行，去重/评分为人工判断，未使用确定性校验。" |

The host must also be able to search the web and read pages (fetch or browser) for discovery and
verification; without page access, mark facts unverified. If the host has no web capability at all,
say "Opportunity discovery requires a web-capable host agent." and stop. File writing is optional:
without it, skip local state. Without host memory, ask once or cache
`.opportunity-radar/profile.json`.

## When to activate

Activate when the request asks *"what should **I** do / join / apply to?"* or
*"what exists that fits someone like me?"*:

- 最近有什么适合我的机会？ / 有没有我可能不知道的机会？
- 我最近可以做点什么？ / 最近有点闲，有什么值得做的吗？
- 有没有适合我的比赛 / 实习 / 科研 / 开源项目 / 奖学金 / 学生计划？
- 有什么适合我专业的东西？（文理工商医艺术都适用）/ 有没有含金量高的活动？
- 我想找点科研做。 / 有没有学生能申请的项目？
- 我想以后做 X，现在做什么最好？（能力反推；X 可为任意领域）
- 我现在缺什么？ / 为什么很多机会我都申请不了？（缺口分析）

### Do not activate (plain lookup)

| User says | What to do |
|---|---|
| "AWS 是什么？" | Answer directly |
| "这个比赛什么时候截止？" | Answer directly |
| "帮我改简历" / "翻译一下这个 JD" | Out of scope |

**Boundary rule:** if a plain lookup is followed by *"根据我的情况看看要不要考"* /
*"适不适合我"* / *"值得参加吗"*, the request becomes discovery → activate.
If a lookup is followed by a discovery follow-up, answer the lookup in one or two lines first,
then run the protocol.

## Discovery modes (internal steering)

These reweight the search space; they are an execution concern, not user-facing labels.

| Mode | Signal | Reweight |
|---|---|---|
| **A — profile discovery** (default) | "最近有什么适合我的机会" | Balanced across the user's goals |
| **B — non-career** | "我不想找工作 / 有点闲，有什么值得做的" | ↓ career, education; ↑ competition, open source, project, skill, event, hobby |
| **C — unknown-unknowns** | "我可能完全不知道的机会" | ↑ adjacent + explore to ~45%; include non-traditional paths |
| **D — capability backfill** | "我想以后做 X，现在做什么最好" | Search real X opportunities → count requirement frequency → search opportunities that build those requirements |

Modes combine (B+C is common). In the answer, express the *behaviour*, not the label:
"这轮降低了求职类权重，更侧重竞赛、开源和项目。" Mode IDs only belong in debug output.

## Resource map — load only what the task needs

| File | Load when | Contents |
|---|---|---|
| `references/opportunity-taxonomy.md` | Step 2 always; step 4 per category | 13 categories, subcategories, sources, language-neutral intent templates |
| `references/search-strategy.md` | Steps 2–4 | Search matrix, expansion rules, 70/20/10, local language, budgets |
| `references/profile-building.md` | Step 1 | Minimum viable profile, when to ask, memory reuse |
| `references/trust-policy.md` | Steps 6–7 | Tier A–D, discovery vs confirmation, conflict handling, freshness |
| `references/extraction-policy.md` | Step 8 | Field-by-field extraction, evidence status, anti-hallucination |
| `references/eligibility.md` | Step 10 | Hard-constraint order, 5-level verdicts, semantic rules |
| `references/ranking.md` | Steps 11–12 | Match vs Priority, weights, coverage guidance, value rubric |
| `references/output-format.md` | Step 13 | Answer templates, length budget, JSON artifact |
| `references/state-and-feedback.md` | When `.opportunity-radar/` exists or the user reacts | seen/saved/ignored, change detection, gap analysis wording |
| `references/locales/generic.md` | **Always** (step 2/3) | Region → locale resolution: target regions, primary/optional locales, unknown regions, dynamic language detection |
| `references/locales/<cc>.md` | Only when the target geography needs it | Region-specific vocabulary, timelines and eligibility terms (`cn` / `jp` / `us` / `uk` / `de`) |

**Locale loading discipline:** load `generic.md` always; load country files **only** for the
resolved target regions. A normal discovery run must not read all of them at once.

Deterministic helpers (Full Mode; never re-implement inline):

| Script | Use for |
|---|---|
| `scripts/normalize_date.py` | Deadline strings → ISO; `deadline_type` (fixed/range/rolling/asap/flexible/tbd); urgency uses the **end** of a range |
| `scripts/dedupe.py` | Cluster duplicates; cycle guard; candidate anchor coherence; conflict report |
| `scripts/score.py` | Eligibility pre-check (hard constraints first), Match/Priority components, coverage self-check |
| `scripts/state.py` | seen/saved/ignored CRUD, change detection, feedback weighting suggestion |
| `scripts/locales.py` | Resolve target regions → search languages + which locale files to load; search-plan skeleton; dynamic language detection (`--detect`) |
| `scripts/common.py` | Shared enums, URL canonicalization, ID generation, lightweight contract validation |
| `scripts/readiness.py` | Readiness: how far the user is from actually starting (not admission probability) |
| `scripts/graph.py` | Opportunity graph: produces → unlocks → goal contribution; gap → bridge opportunities |
| `scripts/gaps.py` | Evidence-backed gap model (skill vs research vs leadership vs network…), each gap citing "N of M target opportunities require X" |
| `scripts/sources.py` | Minimal source intelligence: gap type → bridge intent → source family → targeted queries (research / language / OSS entry), stage-aware, with general-search fallback |
| `scripts/coverage.py` | Search coverage ledger (region/locale/category depth) + one plain-language statement |
| `scripts/utility.py` | Personal Utility: High/Medium/Low + reasons (worth investing resources now?) |
| `scripts/evidence.py` | Pre-gate evidence check: canonical source + official verification + dated application-status evidence; distinguishes "we forgot to record" from "the page cannot confirm" |
| `scripts/portfolio.py` | Resource-constrained portfolio (now / bridge / low_cost / high_upside / long_term / explore), never exceeds the user's weekly budget |

Single source of truth: enums, weights, tracked fields and ID/URL rules live in
`scripts/common.py`; `schemas/*.json` and the references must match it.

## The workflow (13 steps)

> Forbidden: one search → return results. Every step leaves a concrete artifact.

1. **Understand user.** Build/refresh the profile; reuse host memory first. One sentence
   ("我是大二物联网专业，最近有什么值得参加的？") is enough to start. Do not interrogate.
2. **Build search space.** Choose categories from the taxonomy via goals + interests + major
   family — not just the user's literal words. Apply the mode reweighting.
3. **Resolve target geographies, then locales, then queries.** Target geographies come from:
   (1) explicit current-request geography（"只找德国" is an override）, (2) structured profile
   preferences (`preferred_country`), (3) school-country fallback, (4) Global/Remote fallback —
   in that order, never merged blindly. When the host agent identifies a location that
   `scripts/locales.py` does not know, pass it explicitly as a region hint (`--countries`)
   instead of dropping it. Then resolve the search languages (`scripts/locales.py`) and build the
   `category × layer × language` matrix. City/province hints（`place_hints`，如 "杭州"、
   "江浙沪"）must be carried into the queries themselves — country-level language alone loses
   city intent. `optional_locales` are candidates, not mandatory search passes.
   Localize the taxonomy's intent templates into the target languages; when a first pass surfaces
   pages in another language, add that language to the next round. Every expansion must trace
   back to a profile signal; max two semantic hops.
   Treat the current request as a per-run context, not a silent profile rewrite. In Full Mode,
   pass the same current goals and location constraints to `scripts/locales.py --context <json>`
   and `scripts/score.py --context <json>`;
   a new country preference replaces stale city/province preferences for this run. Explicit
   constraints such as "small companies only" need verified organization-size evidence;
   unknown size is a lead to check, not a qualifying match.
4. **Search multiple categories.** Open-ended asks: aim for **≥5 categories**; goal-specific
   asks: normally ≥2 relevant categories, or one when the user narrowly specifies a single
   category. This is a coverage guideline to avoid the "everything becomes internships" failure
   mode — never search irrelevant categories just to hit a number.
5. **Discover candidates.** Cheap breadth-first pass: title, organization, deadline, link,
   `discovery_url` and its trust tier.
5b. **Plan sources, not just queries (minimal source intelligence).** For each gap or intent
    (`scripts/sources.py`): gap type → bridge intent → source family → targeted query, with
    **general search as fallback**. Stage matters — a working professional's research bridge
    (part-time programme, open seminar, industry-academia project) differs from an
    undergraduate's (summer research, undergraduate lab). Record each candidate's provenance
    (`known_source` / `source_family_query` / `general_search` / `adjacent_discovery`).
    A source family is a **starting point, never a whitelist**: sources absent from the registry
    are still discovered normally. See `references/source-families/`.
6. **Find canonical sources.** Locate the official page (program/company/university/organizer).
   Tier C/D may discover; Tier A/B must confirm.
7. **Verify important facts.** On the canonical page confirm at least: application window /
   deadline, eligibility scope, official application path. Record `verification_status` and
   `last_verified`. Distinguish the graduation/intake cohort from when applications open.
   Record field-level `evidence.application_status` or `evidence.deadline` with the exact
   official source and verification date; an organization homepage alone is not proof that
   this specific opportunity is open. If no canonical page exists, write
   "未找到官方确认来源" — never invent a link.
8. **Extract structured data.** Fill the opportunity schema per `references/extraction-policy.md`.
   Tag key fields with `evidence.status` = explicit / inferred / unknown. Pass dates through
   `normalize_date.py`.
9. **Deduplicate.** Run `scripts/dedupe.py`, then resolve its `maybe_pairs` by judgement.
   Records whose cycles differ are separate opportunities unless confirmed otherwise.
10. **Check eligibility.** Per high-ranked item give one of Eligible / Probably Eligible /
    Unknown / Probably Ineligible / Ineligible, with the deciding reasons.
    **Hard constraints outrank model judgement** (see Cross-cutting rules).
11. **Assess readiness (not probability).** For high-ranked items state how far the user is
    from starting (`scripts/readiness.py`): ready_now / minor / short / major preparation /
    blocked / unknown, with ready_items / missing_items / blockers. **Never output admission chance.**
11b. **Value, effort and connections.** Record `outcomes` (so "unpaid" is not "worthless"),
    `effort` / `cost` / `time_to_value`, and `produces` → `unlocks` → `goal_contribution`
    (`scripts/graph.py`). Use `unlocks[].type` when the follow-up is not actually found; never
    fabricate an `opportunity_id`. Unknown stays Unknown.
11c. **Personal Utility.** Decide whether it deserves the user's resources *now*
    (`scripts/utility.py` → High/Medium/Low + reasons). Separate from Match (fit) and Priority
    (urgency): a high-match but very expensive opportunity can be Low utility.
11d. **Gaps → bridge opportunities.** Derive gaps from **real evidence only**
    (`scripts/gaps.py`): requirements of the scanned target opportunities, the user's stated
    target, or requirements repeating across several opportunities — every gap must be able to
    say "N of M target opportunities require X". Type the gap honestly (skill / research /
    network / leadership / public_reputation / language / portfolio / location_visa …);
    **do not classify everything as a skill gap**. Then find a **real** bridge opportunity
    (`scripts/graph.py` — same gates as any opportunity, never a course list unless nothing real
    exists) and record the chain gap → bridge → produced evidence → target. When no real bridge
    exists, say so and log it as a source-intelligence need.
12. **Rank.** Run `scripts/score.py` for components, then apply judgement.
    Sort primarily by Priority (Match + urgency), not Match alone.
12b. **Explore adjacents.** Actively search adjacent and non-obvious directions — this is why
    the skill exists. Include them when they meet the quality and verification bar; never pad
    with weak items to satisfy a quota. If nothing qualifies, say so in one line.
13. **FINAL_RECOMMENDATION_CHECK, then return.** Before writing the answer, run the gate on
    every candidate: `freshness` → `canonical source` → `eligibility` → `duplicate` →
    `verification` → `relevance`. Split the output into three zones and never merge them:

    | Zone | Gate | Size |
    |---|---|---|
    | **Recommended now** | freshness ∈ {open, likely_open} **AND** canonical source and recent explicit application/deadline evidence **AND** verified_official **AND** not Ineligible **AND** match ≥ 55 | 3–6 (fewer is fine) |
    | **Worth verifying** | freshness unknown / no canonical source / eligibility unknown | 3–8, labelled "需确认" |
    | **Closed / Excluded** | closed / expired / Ineligible | with reason |

    `scripts/score.py` computes this (`--zone recommended_now` filters it). Quality gates:
    **expired leakage = 0**, **unverified actionable leakage = 0**,
    final-recommendation verification **≥ 80% (ideal 100%)**.
    If the budget only allows 4 verified items, return 4. Each item still carries what it is,
    why it fits, eligibility verdict, deadline, cautions, official source, value.
    Optionally write the JSON artifact to `.opportunity-radar/last-run.json`.

**Decision model (three separate questions).**
  * *Match* — is it a fit?  *Priority* — is it urgent?  *Utility* — does it deserve resources now?
  Utility weighs eligibility, goal fit, readiness, outcome value, effort, cost, time-to-value,
  future optionality, trust and urgency. Output **High / Medium / Low + reasons only** — never a bare score.

**Opportunity portfolio (for open-ended asks).** Build it with `scripts/portfolio.py`: roles
(now / bridge / low_cost / high_upside / long_term / explore) are **earned, never padded** — a
role only appears if an item genuinely qualifies. The portfolio must respect the user's
resources: the sum of weekly commitments may not exceed `constraints.weekly_time`; drop the
lowest-priority items instead and report what was dropped (`portfolio_resource_conflict_rate`
must stay 0). When several routes are reasonable, offer side-by-side alternatives
("如果你优先升职 → A+B；如果想转方向 → A+C") instead of making a life decision for the user.

**Prohibitions.** No admission probability, no predicted salary, no "搜遍了所有机会", no fabricated
`unlocks[].opportunity_id`.

**Budget split.** At the start of a run, split the budget explicitly: **Discovery Budget**
(expand queries, collect candidates) and **Verification Budget** (return to official pages).
Discovery must not consume verification. Pre-screen candidates (obviously expired, irrelevant,
duplicate, terrible source) *without* spending fetches, then verify only the Top candidates by
Match → Priority → Novelty. Budget for fewer, fully verified recommendations — never more,
half-verified ones.

**Pacing.** Prefer quality over completeness. Stop a category when two consecutive query
variants only return already-seen or irrelevant results.

## Cross-cutting rules

1. **Trust.** Tier A/B for facts; Tier C/D for discovery only. Prefer official over third party
   and state the difference when they conflict.
2. **No fabrication.** No invented URLs, deadlines, requirements or "official" pages.
   Missing → `null` + "未找到官方确认来源".
2b. **`deadline: null` is not "still open".** Every opportunity gets a `freshness`
   (`open` / `likely_open` / `unknown` / `closed` / `expired` / `future`) from
   `scripts/normalize_date.py --freshness`. A future graduation or intake cohort does not
   mean applications are not yet open. Past application/event cycle or ended event
   ⇒ `closed` ⇒ excluded. When in doubt, answer "current status unconfirmed" — never "apply now".
2c. **No canonical source ⇒ no "apply now".** Third-party-only findings are discovery leads:
   put them under "值得继续核实 / Unverified leads" with "未找到官方确认来源"; they must not appear
   in Recommended now.
3. **Hard constraints outrank judgement.** Explicit page requirements versus explicit profile
   facts decide deadline, education level, student year, graduation window, nationality/work
   authorization, school restrictions, GPA and language scores. Semantic judgement may add
   (related field, relevant experience) but may not overturn those.
4. **Missing profile data ≠ not qualified.** A progressive profile has gaps. Only judge against
   the user when they **explicitly** stated the missing capability (e.g. `level: "none"` for a
   language). Otherwise the verdict is `Unknown`. Profile fields marked `inferred_pending`
   (via `_provenance` / `_source`) are excluded from eligibility checks — they may still drive
   search expansion and ranking, but never a hard verdict.
5. **Explicit / inferred / unknown.** Never upgrade an inference to a fact: a Japanese company
   page without a language requirement does not mean "requires N2". Key fields carry an
   `evidence.status`; only `explicit` (or a record with no `evidence` block at all — legacy mode,
   which caps the conclusion at `Probably Eligible`) may reject an opportunity. `inferred` and
   `unknown` values cannot exclude anyone; they downgrade the verdict to `Unknown` for semantic
   judgement. If a page states nothing about eligibility, the verdict is `Unknown` — "no stated
   requirement" is not "probably qualifies".
6. **Eligibility is a verdict with reasons**, not a boolean.
7. **Dedupe before ranking** — otherwise one program eats three slots.
8. **Match ≠ Priority.** A 95-match item closing in six months may rank below an 88-match item
   closing in two days.
9. **Real requirements over generic advice.** For "how do I get stronger" asks, derive the
   requirement list from actually discovered postings and quantify as
   "在本次扫描到的 N 个机会中，X 出现在 M 个里" — never "学 X 就能多 N 个机会".
10. **Novelty.** If state exists, mark only items actually shown to the user as seen;
    discovered-but-unshown candidates remain new. Re-show when something material changed.
11. **Never silently rewrite the profile.** Suggest weighting changes instead.
12. **Answer in the user's language**; keep program, organization and URL strings verbatim.

## Output contract

Default: compact. Header (what was searched + count) → 3–6 full blocks → a short
"另一个方向" group for adjacent/explore items → "已见过 / 有变化" when state exists →
optional gap snapshot → optional next actions.

Every full block answers **为什么推荐给我** with evidence (✓ matched conditions, each linked to
a page or field) and **可能的问题** (△ unknowns, frictions). No block longer than ~10 lines.
Templates and length budget: `references/output-format.md`.

Do not print internal mode IDs or raw scores; express behaviour and bands instead.

## Local state (optional)

```
.opportunity-radar/
├── profile.json     # cached profile (only if the host has no memory)
├── seen.json        # first_seen / last_seen / tracked hash / change log
├── saved.json       # interested / saved / applied
├── ignored.json     # ignored / not_relevant
└── last-run.json    # last discovery artifact
```

Allowed local state: only the files above. External side effects (applications, emails,
registrations, uploading personal data) are out of scope.
Read state at steps 9–13 if the directory exists; write it via `scripts/state.py`.
Never store credentials, contact details, or anything the user did not supply.
Details: `references/state-and-feedback.md`.

## Self-check before answering

- [ ] Did I use the profile, or only the literal words in the request?
- [ ] Did I search multiple categories rather than collapsing everything into internships?
- [ ] Did I resolve the target region from the profile/request (rather than assuming one), and
      search in that region's language(s) instead of a fixed language list?
- [ ] Did I avoid assuming a field or region that the user never stated?
- [ ] Does every factual claim trace to a Tier A/B source, or is it marked unverified?
- [ ] Did I dedupe, and are cycles kept distinct?
- [ ] Does every recommended item carry an eligibility verdict **and** its deciding evidence?
- [ ] Where a hard constraint conflicted with a judgement call, did the hard constraint win?
- [ ] Did I treat missing profile fields as `Unknown` rather than "not qualified"?
- [ ] Are adjacent/explore items included when they qualified — and honestly reported as absent
      when they did not?
- [ ] Did I keep side effects inside the optional `.opportunity-radar/` state directory?
- [ ] Is the answer a concise selection (fewer than 5 is fine when evidence is sparse), not a link dump?
- [ ] If running without scripts, did I say so instead of implying deterministic results?
