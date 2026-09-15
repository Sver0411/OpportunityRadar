# Development Notes

Internal notes for maintaining OpportunityRadar. Not needed to use the skill — it is a
protocol, and the user-facing documentation is in [README.md](README.md).

---

## 1. Design decisions and trade-offs

### Why an Agent Skill and not an agent

The host already has web search, fetch, a browser, shell, Python, file I/O and memory. Rebuilding
those inside the skill would add surface area without adding capability. OpportunityRadar only
adds what a bare agent lacks: a taxonomy, a search strategy, verification and eligibility policy,
and deterministic helpers.

### Why hard constraints outrank model judgement

An LLM asked "is this a good fit?" tends to be agreeable. For eligibility, agreeableness produces
false hope: the user spends an evening on an application for a PhD-only programme. The protocol
therefore separates *deterministic* conditions (page-stated requirements versus profile-stated
facts) from *semantic* ones (`related field`, "strong background"). `merge_verdict()` in
`scripts/score.py` enforces the ordering:

| Hard-constraint result | Effect of the model verdict |
|---|---|
| explicit conflict | cannot be overturned |
| all satisfied | model may be more conservative, not more optimistic |
| `Unknown` because the **profile** lacks data | model decides (it may have the fact from conversation) |
| `Unknown` because the **page** lacks data or scales are incomparable | clamped at `Probably Eligible` |

### Why missing data is `Unknown`, not "no"

Profiles are built progressively — insisting on completeness before answering would break the
primary use case. `str(None).lower() == "none"` once caused "no language score recorded" to be
read as "explicitly does not speak Japanese"; `is_explicit_none()` now exists solely to prevent
that class of bug. Only an explicit marker (`level: "none"`, `不会`, `无`) produces a negative
verdict.

### Why the cycle guard exists

Programme pages are routinely reused across years. If "same URL → same opportunity" were enforced
naively, a 2026 intake and a 2027 intake would collapse into one record and the user would see a
deadline that no longer applies. `cycles_conflict()` compares only *explicit* cycle evidence
(primary year, and season when both sides name one), so "Summer 2027" and "2027" stay the same
cycle while 2026 and 2027 do not.

### Why URL normalization is conservative

Lowercasing paths breaks case-sensitive servers, and dropping `ref` / `source` / `from` can break
real routing or attribution. Only `utm_*` and unambiguous click-tracking parameters are removed;
hosts are lowercased, paths are not. Sorting query parameters keeps comparisons stable.

### Why the coherence check exists

Union-find is single-link: A~B and B~C merge A with C even when A and C are dissimilar. The
coherence pass picks the cluster anchor and ejects members that do not clear the threshold
against it, which is what stops an ambiguous record from bridging two different cycles.

### Why the search-space guidance is not a hard quota

Requiring "at least one explore item" or "five categories" invites padding: weak opportunities
included to satisfy a number. The guidance is therefore explicit about *why* it exists (prevent
the all-internships failure mode), and the honest answer when nothing qualifies is a sentence
saying so.

### Why eligibility needs an evidence gate

A requirement that was *inferred* (or whose provenance nobody recorded) must not be able to
exclude a candidate. Two concrete failure modes drove this:

- An extractor guesses "Japanese N2" from a company's location; the user, who has N1-adjacent
  other languages but no JLPT score, gets silently filtered out of an opportunity that never
  stated the requirement.
- A page states nothing about eligibility at all, and the old code answered "Probably Eligible" —
  turning "no information" into a positive claim.

So: only `evidence.status: explicit` (or a record with no `evidence` block at all — legacy mode,
which keeps old data working but caps the conclusion at `Probably Eligible`) may reject anyone.
`inferred` / `unknown` values downgrade to `Unknown` for semantic review, and a page that states
nothing yields `Unknown`. Profile fields marked `inferred_pending` are stripped before eligibility
runs, while search expansion and ranking still use the full profile.

### Why `Ineligible` is reserved for unambiguous conflicts

`Ineligible` removes an opportunity from the result list, so it is limited to enumerated or date
based conflicts that cannot be interpreted differently: expired deadline, `education_level`,
`student_year`, `graduation_window`. Everything that depends on reading wording — nationality
phrasing, school rosters, language proficiency descriptions, GPA scales — yields
`Probably Ineligible` or `Unknown` instead.

### Why the core must not know the user

A discovery skill accumulates defaults fast: the author's own region, field and language exams
creep into examples, query templates and fixtures until the skill serves one kind of user while
claiming to serve everyone. The three concepts have to be kept apart:

| Concept | Example | Treatment |
|---|---|---|
| **Capability** | parsing `JLPT N2`, `Praktikum`, `应届生`, `CPT` | keep — it is just text handling |
| **Locale knowledge** | "日本按卒業年度筛选", "德国区分 Pflichtpraktikum" | keep, but load only when the target region needs it |
| **Default assumption** | "the user probably wants Japan/embedded" | remove |

So target regions come from the profile and the current request, languages follow from the
regions (`scripts/locales.py`), and region knowledge lives in `references/locales/` as an
*optional* layer. A user in a country with no locale file still gets a working pipeline — generic
rules plus dynamic language detection — and the examples deliberately cover several unrelated
people (CS/security in the US, biology in Germany, design in France, IoT in Japan) so no single
route reads as the default.

One nuance about the seed tables (COUNTRY_ALIASES, PLACES, INTEREST_ALIASES): they are
**normalization and acceleration, not boundaries**. Their only jobs are (a) canonicalization so
comparisons and tests are reproducible, (b) fast place→country→language inference, (c) scoring
signals that behave identically across runs. The agent's semantic layer always takes precedence:
a place, field or interest it extracts that the tables don't know passes through as a hint and
is used anyway. Nothing is gated by the tables. When a missing entry causes a real failure, the
failure-driven process adds it — entries are not collected speculatively.

### Locale precedence and responsibility boundary

`target_regions()` implements **precedence, not merging**: an explicit request override
（"只找德国"）replaces the profile's long-term preferences; a non-restrictive mention adds the
request region ahead of the profile's; otherwise the profile falls back through
`preferred_country` → school country → Global/Remote. The chosen path is reported as
`region_source`, and `region_hints` keeps whatever the user named even when it is not in the
locale table — a region and its search language are different things.

Responsibilities are split deliberately: `locales.py` does canonicalization, known-alias
resolution, locale planning, knowledge-file selection and fallback; the host agent's semantic
layer extracts target geography from messy natural language and passes it in structured form
(`--countries` / `preferred_country`). Free-text region detection inside `locales.py` is
best-effort alias matching only. User-language entries become `optional_locales` only when the
profile shows explicit ability (`level` / `score` non-empty, not a "none" marker); a bare
language name with no recorded ability is ignored.

### Why `external Actions` are out of scope

Discovery and explanation are reversible; submitting a form is not. Application actions stay with
the user unless a separate, explicitly authorized workflow handles them.

---

## 2. Single source of truth

`scripts/common.py` owns the shared vocabulary — categories, goal types, verdicts, trust tiers,
verification statuses, value levels, evidence statuses, deadline types, layer names, weights,
tracked fields, evidence fields — plus `canonical_url()`, `derive_id()`, `norm_org()`,
`canonical_country()` and the contract validators. `score.py` owns the eligibility semantics:
`evidence_status()` / `is_hard_evidence()`, `deadline_info()`, `normalize_language_requirement()`,
`skill_hit()` and `filter_profile_for_eligibility()`.

`locales.py` owns region → locale resolution: `REGION_LOCALES`, `LOCALE_FILES`, `MODE_WEIGHTS`,
`MODE_LAYERS`, `target_regions()`, `resolve_locales()`, `detect_locale()` and `search_plan()`.
`GOAL_TO_CATEGORY` and `INTEREST_ALIASES` moved into `common.py` so that scoring and planning
cannot drift apart. `schemas/*.json` and `references/*.md` must agree with it.

`tests/test_consistency.py` enforces this mechanically:

- `references/ranking.md` weight table must equal `common.WEIGHTS`
- schema enums must equal the `common` tuples
- every enum value must be documented in the relevant reference
- every reference and script must be indexed in `SKILL.md`
- `dedupe.py` / `state.py` / `score.py` must not redefine the shared helpers
- no placeholder markers, and no development-process residue in `README.md`

If you change a constant, change it in `common.py` first and let the test suite point you at
whatever else needs updating.

---

## 3. Agent Skills compatibility

### 3.1 Agent Skills specification (public standard, verifiable)

The shipped frontmatter uses only the six fields the specification allows:

```yaml
name: opportunity-radar
description: ...
license: MIT
compatibility: ...
metadata:
  agent_created: "true"
  version: "2.0"
```

- Allowed top-level keys: `name`, `description`, `license`, `compatibility`, `metadata`,
  `allowed-tools`. Unknown top-level keys cause a hard error when packaging or uploading.
- `compatibility` accepts a string of up to **500 characters** (asserted by
  `tests/test_schemas.py`).
- `description` has **no independent length limit in the specification**. What is documented is
  that `description` and `when_to_use` are truncated together at **1,536 characters** in the skill
  listing. This project applies a stricter self-imposed budget of 1,024 characters so the trigger
  phrases stay visible — that budget is a project choice, not a specification limit.
- `metadata` is a free-form map and is not interpreted by hosts; it is a supported place for
  bookkeeping keys such as `agent_created` or `version`.

### 3.2 Host-specific implementation notes (not part of the standard)

These observations come from inspecting one host build and must not be presented as
specification behaviour:

- The host examined parses frontmatter into a fixed whitelist
  (`name`, `description`, `description_zh`, `description_en`, `when-to-use`, `allowed-tools`,
  `disable`, `disable-model-invocation`, `user-invocable`, `license`) and contains **no
  references to `agent_created`** anywhere. It therefore does not consume that key.
- That host tolerates extra frontmatter keys, so its local validator passes even when a key would
  be rejected by specification-strict packaging. Do not rely on that tolerance.
- Because `description_zh` is host-specific, Chinese trigger phrases live inside `description`
  instead.

## 4. Repository QA checklist

Before publishing a change:

```bash
# 1. unit tests (stdlib; jsonschema optional)
python3 -m unittest discover -s tests -t tests

# 2. CLI smoke tests — every documented command must still run
python3 scripts/normalize_date.py --file examples/dates.example.txt --default-year 2026 --now 2026-09-14 > /dev/null
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --output /tmp/clusters.json
python3 scripts/score.py --profile examples/profiles/cs-student.example.json \
                         --opportunities /tmp/clusters.json --today 2026-09-14 --format table
python3 scripts/common.py --validate examples/opportunity.batch.example.json

# locales: every example profile must resolve, and unknown regions must not break anything
for f in examples/profiles/*.json; do python3 scripts/locales.py --profile "$f" > /dev/null; done
python3 scripts/locales.py --countries Kenya        # falls back to generic + English

# 3. skill validation against the local spec tooling, if available
python3 <skill-creator>/scripts/quick_validate.py .

# 4. packaging smoke test (must succeed; also checks frontmatter legality)
python3 <skill-creator>/scripts/package_skill.py . /tmp/skill-dist
```

Plus the manual review questions:

1. Did anything change that requires updating `common.py` and its dependants together?
2. Does `README.md` still describe only behaviour the tests actually cover?
3. Are new example files still clearly marked as fictional?
4. If an enum changed, does `tests/test_consistency.py` tell you every place to update — and does
   it actually pass?
5. Did any example/test/fixture quietly re-introduce a region or field default? `tests/test_locale.py`
   is the guard for that.

### Bilingual documentation

`README.md` (English) and `README.zh-CN.md` (简体中文) are kept consistent, but the test suite
only checks **functional** properties, not visual style:

- both files exist and link to each other
- relative links point at paths that exist, and every internal `](#anchor)` resolves against the
  headings of the same file (GitHub slug rules: lowercase, punctuation removed, spaces → hyphens,
  so `## ✅ Tests` becomes `#-tests`)
- no development-process residue and no absolute host-support claims

Deliberately **not** enforced: badge counts, emoji on every heading, 1:1 section parity, and any
"test count badge must match the suite" rule. Those are style decisions that should not be able to
fail CI. Never put volatile numbers (test counts, resource counts) in prose.

## 5. Acceptance scenarios

Behavioural scenarios worth re-running after any change to search strategy, eligibility or output
format. They require live web access, so they are not part of the unit suite.

| # | Input | Expected |
|---|---|---|
| 1 | 我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？ | uses the profile; ≥5 categories; expanded queries; Chinese + English + Japanese search; real current opportunities; official sources preferred; eligibility verdicts; duplicates removed; reasons given; at least some adjacent/explore items |
| 2 | 我不想找实习，最近有什么值得做的？ | does **not** keep recommending internships; shifts to competitions / research / open source / projects / skills / events / hobbies |
| 3 | 我想以后做 Embedded AI，但是不知道现在应该做什么。 | searches real Embedded AI postings, counts their requirements, backfills with competitions / open source / projects / research / skill programmes — not a generic study roadmap |

Example profiles (all fictional): [`examples/profiles/`](examples/profiles/). Format reference:
[`examples/discovery-output.example.md`](examples/discovery-output.example.md).

---

## 6. Known limitations and future work

- **Live-web behaviour is not unit-tested.** Scenarios in §5 are manual; only the deterministic
  layer is covered by CI.
- **Cycle detection needs explicit evidence.** A programme page that reuses a URL across years
  *without* any year in the title or dates cannot be separated automatically — the coherence and
  conflict machinery surfaces it, but a human or model must decide.
- **Major-relevance matching is lexical for the literal case only.** `related field` judgement is
  deliberately left to the model, per the eligibility policy.
- **Locale knowledge depth is uneven.** `cn` / `jp` / `us` / `uk` / `de` have dedicated files; every
  other region runs on generic rules plus dynamic detection. That is deliberate (files are added when
  a region has a real misjudgement risk), but it does mean European and North American specifics are
  thinner than the five covered files.
- **`ref` / `source` parameters cost precision.** They are preserved deliberately, which means a
  campaign tag change is reported as a change. If that proves noisy in practice, the fix is to
  add a user-configurable ignore list rather than to broaden the defaults.
