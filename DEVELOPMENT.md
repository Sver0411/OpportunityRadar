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

### Why `external Actions` are out of scope

Discovery and explanation are reversible; submitting a form is not. Application actions stay with
the user unless a separate, explicitly authorized workflow handles them.

---

## 2. Single source of truth

`scripts/common.py` owns the shared vocabulary — categories, goal types, verdicts, trust tiers,
verification statuses, value levels, evidence statuses, deadline types, layer names, weights,
tracked fields, evidence fields — plus `canonical_url()`, `derive_id()`, `norm_org()` and the
contract validators. `schemas/*.json` and `references/*.md` must agree with it.

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

## 3. Agent Skills specification compliance

The shipped frontmatter uses only the six fields allowed by the Agent Skills specification:

```yaml
name: opportunity-radar
description: ...
license: MIT
compatibility: ...
metadata:
  agent_created: "true"
  version: "2.0"
```

Notes from verifying this against the tooling available in the development environment:

- The specification allows exactly `name`, `description`, `license`, `compatibility`, `metadata`,
  `allowed-tools`. Unknown **top-level** keys cause a hard error when packaging or uploading
  (for example to claude.ai or the Skills API).
- `agent_created: true` was previously a top-level key. It is not part of the specification, and
  scanning the local host bundle showed the frontmatter parser reads a fixed whitelist
  (`name`, `description`, `description_zh`, `description_en`, `when-to-use`, `allowed-tools`,
  `disable`, `disable-model-invocation`, `user-invocable`, `license`) with **zero** references to
  `agent_created` anywhere. It has therefore been moved into `metadata`, where it is harmless and
  still discoverable by tooling that looks for it.
- The local validator (`skill-creator/scripts/quick_validate.py`) checks only that `SKILL.md`
  exists, that the frontmatter opens with `---`, that `name` is hyphen-case and that
  `description` contains no angle brackets. Extra keys are tolerated there, but not by the
  packaging/upload paths above.
- `description` and `when_to_use` are truncated together at 1,536 characters in the skill listing,
  so the most important trigger phrases come first in `description`.
- `compatibility` is limited to 500 characters (asserted by `tests/test_schemas.py`).
- Host-specific keys such as `description_zh` exist in some hosts and would improve local
  triggering, but they are not spec-legal; the Chinese trigger phrases therefore live inside
  `description` instead.

---

## 4. Repository QA checklist

Before publishing a change:

```bash
# 1. unit tests (stdlib; jsonschema optional)
python3 -m unittest discover -s tests -t tests

# 2. skill validation against the local spec tooling, if available
python3 <skill-creator>/scripts/quick_validate.py .

# 3. packaging smoke test (must succeed; also checks frontmatter legality)
python3 <skill-creator>/scripts/package_skill.py . /tmp/skill-dist
```

Plus the manual review questions:

1. Did anything change that requires updating `common.py` and its dependants together?
2. Does `README.md` still describe only behaviour the tests actually cover?
3. Are new example files still clearly marked as fictional?
4. If an enum changed, does `tests/test_consistency.py` tell you every place to update — and does
   it actually pass?

### Bilingual documentation

`README.md` (English) and `README.zh-CN.md` (简体中文) are kept in sync mechanically by
`tests/test_consistency.py` → `TestBilingualDocs`:

- both must link to each other, and start with a `<div align="center">` block that is closed
- the first `##` section must be the quick-start section, and every `##` heading must lead with an emoji
- every internal `](#anchor)` link must resolve against the headings of the same file
  (GitHub's slug rules: lowercase, punctuation stripped, spaces → hyphens, so `## ✅ Tests`
  becomes `#-tests`)
- badges must be https, include shields.io and the CI status badge, and the
  `unittest-<N>` badge number must equal the real number of collected test cases
- the two files must have the same number of `##` sections

Practically: when you add a section or a test case, update **both** files — the suite fails
otherwise. Keep volatile numbers (test counts, resource counts) out of prose; the badge is the
single place the test count lives.

---

## 5. Acceptance scenarios

Behavioural scenarios worth re-running after any change to search strategy, eligibility or output
format. They require live web access, so they are not part of the unit suite.

| # | Input | Expected |
|---|---|---|
| 1 | 我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？ | uses the profile; ≥5 categories; expanded queries; Chinese + English + Japanese search; real current opportunities; official sources preferred; eligibility verdicts; duplicates removed; reasons given; at least some adjacent/explore items |
| 2 | 我不想找实习，最近有什么值得做的？ | does **not** keep recommending internships; shifts to competitions / research / open source / projects / skills / events / hobbies |
| 3 | 我想以后做 Embedded AI，但是不知道现在应该做什么。 | searches real Embedded AI postings, counts their requirements, backfills with competitions / open source / projects / research / skill programmes — not a generic study roadmap |

Profile for scenario 1: [`examples/profile.example.json`](examples/profile.example.json)
(fictional). Format reference:
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
- **Language coverage.** Query templates are strongest for Chinese, English and Japanese; German
  and Korean are basic.
- **`ref` / `source` parameters cost precision.** They are preserved deliberately, which means a
  campaign tag change is reported as a change. If that proves noisy in practice, the fix is to
  add a user-configurable ignore list rather than to broaden the defaults.
