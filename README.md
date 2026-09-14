<div align="center">

[简体中文](./README.zh-CN.md) | **English**

# 📡 OpportunityRadar

**Find the opportunities you didn't know to search for.**

[![tests](https://github.com/Sver0411/OpportunityRadar/actions/workflows/test.yml/badge.svg)](https://github.com/Sver0411/OpportunityRadar/actions/workflows/test.yml)
[![unittest](https://img.shields.io/badge/unittest-158-4B9B6F)](#-tests)
[![license](https://img.shields.io/badge/license-MIT-3DA639)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](#-helper-scripts)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-534AB7)](#-installation)
[![runtime deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen)](#-helper-scripts)

Turns “最近有什么适合我的机会？” into a 13-step protocol 🎯
**Understand → Expand → Discover → Verify → Filter → Rank → Explore**

Personalised across 13 categories 🗂️ · Official-source verified 🛡️ · Local-language search 🌏 · Duplicate-aware 🧹 · Explainable verdicts 📝

*Works with any web-capable host agent · No accounts, no cloud, no telemetry 🏠*

</div>

---

## 🚀 Quick start

```bash
# 1) install — the target directory must be named opportunity-radar
git clone https://github.com/Sver0411/OpportunityRadar.git opportunity-radar
cp -r opportunity-radar ~/.workbuddy/skills/opportunity-radar   # or your agent's skills directory
```

Then just ask — no configuration, no API keys:

```text
我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？
```

Want to check the deterministic layer first?

```bash
python3 -m unittest discover -s tests -t tests        # full test suite, stdlib only (no network)
python3 scripts/normalize_date.py "9月20日-10月5日" --default-year 2026 --now 2026-09-14
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --format text
```

📖 Chinese documentation: [README.zh-CN.md](./README.zh-CN.md)

---

## 🧭 Why OpportunityRadar

Plain search answers the wrong question. Ask a general agent "帮我找几个实习" and it searches
`IoT internship`, returns a handful of links, and stops. But the hard part was never the
search — it is that **the user does not know what to search for**.

OpportunityRadar fills that gap with a protocol rather than a prompt:

| Step | A bare agent | OpportunityRadar |
|---|---|---|
| Scope | internships / jobs | 13 opportunity categories including research, open source, funding, hobby, networking |
| Queries | the user's literal words | a search matrix derived from major family (more specific → peer → adjacent → transferable) |
| Language | English only | local language + English, so Japanese/Chinese/German pages are not missed |
| Mix | all directly related | 70% direct / 20% adjacent / 10% transferable-and-unexpected |
| Sources | whatever ranked first | Tier A–D model; only official sources confirm facts |
| Eligibility | a yes/no guess | five-level verdict with the deciding evidence |
| Duplicates | not handled | URL/title/organization/cycle clustering with conflict reporting |
| Ordering | search-engine order | Match and Priority separated, with deadline urgency |
| Memory | starts over each time | local seen/saved/ignored state with change detection |
| Gaps | generic learning advice | requirement frequency derived from real discovered postings |

---

## 🎁 What it can discover

| Category | Examples |
|---|---|
`career` | summer/winter/remote/overseas internships, research internships, campus recruiting, graduate programmes, part-time, campus ambassador
`research` | research assistant roles, undergraduate research, lab openings, summer research, visiting student,论文合作
`competition` | programming, algorithm, CTF, AI/CV/NLP/LLM, data science, IoT, embedded, FPGA, robotics, drones, math modelling, hackathons, design, case competitions
`education` | graduate admission, summer schools, exchange, joint programmes, dual degrees, short courses
`language` | JLPT / TOEIC / IELTS / TOEFL / GRE / CET / TOPIK, language competitions, scholarships, exchanges
`skill_development` | certifications, student cloud/GPU/API credits, bootcamps, developer training, dev-board programmes
`open_source` | GSoC-style programmes, mentorship, contributor programmes, good first issues, bounties, beta programmes
`hobby` | photography, drones, automotive, aviation, games, game jams, music, writing, design, maker, 3D printing
`funding` | scholarships, research/travel/conference grants, startup funds, equipment and cloud funding, tuition waivers
`event` | conferences, developer conferences, academic meetings, workshops, meetups, open days, career fairs
`project` | company problem statements, open innovation, capstones, civic-tech projects, build challenges, dataset projects
`entrepreneurship` | startup competitions, accelerators, incubators, campus ventures, demo days, co-founder calls
`networking` | mentor programmes, alumni mentoring, student chapters, professional societies, community leads

Full subcategory lists, typical sources and multilingual query patterns:
[`references/opportunity-taxonomy.md`](references/opportunity-taxonomy.md).

---

## ⚙️ How it works

Thirteen steps, no shortcuts (a single search followed by a result list is not the protocol):

```
 understand → build search space → expand queries → search categories → discover
 → find canonical sources → verify → extract → dedupe → eligibility → rank
 → explore adjacents → return the best
```

The full step-by-step protocol lives in [`SKILL.md`](SKILL.md); three rules shape all of it:

- **Hard constraints outrank model judgement.** If a page says "PhD only" and the user is an
  undergraduate, the verdict stays ineligible even if a model would rather say yes. Semantic
  judgement handles `related field` and fuzzy "relevant experience" wording only.
- **Missing profile data ≠ not qualified.** A progressive profile has gaps; a user who never
  entered a language score is `Unknown`, not ineligible. Only an explicit "I don't have this"
  produces a negative verdict.
- **Verified beats complete.** Facts are asserted only from official sources, and anything
  unconfirmed is labelled as such.

---

## 📦 Installation

Skill packages are just folders. Copy this repository's contents into your agent's skills
directory **under the name `opportunity-radar`** (the directory name must match the `name` in
`SKILL.md` frontmatter):

```bash
# the target directory must be named opportunity-radar
git clone https://github.com/Sver0411/OpportunityRadar.git opportunity-radar
cp -r opportunity-radar ~/.workbuddy/skills/opportunity-radar      # WorkBuddy
cp -r opportunity-radar ~/.codebuddy/skills/opportunity-radar      # CodeBuddy
cp -r opportunity-radar ~/.claude/skills/opportunity-radar         # Claude Code
cp -r opportunity-radar <project>/.<agent>/skills/opportunity-radar # project-scoped
```

No dependencies to install. The helper scripts run on Python 3.8+ with the standard library only.

GitHub repository name is `OpportunityRadar`; the installed skill directory must be
`opportunity-radar`.

### Environment requirements

| Capability | Needed for | If missing |
|---|---|---|
| Web search | discovery, local-language queries | discovery cannot run — the skill will say so and stop |
| Page fetch / browser | confirming facts at official sources | facts are marked unverified |
| Python 3.8+ | deterministic helpers (`scripts/*.py`) | Protocol-only Mode: same workflow, manual judgement, no deterministic claims |
| File write | local state, JSON artifact | state is skipped; everything else works |
| Host memory | reusing a known profile | the skill asks once, or caches `.opportunity-radar/profile.json` |

---

## 💡 Usage examples

### Example 1 — general discovery (Japanese + Chinese + remote)

```text
我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？
```

Expected behaviour: uses the profile; covers several categories (internships, competitions,
research, open source, student resources); expands queries beyond the literal words; searches in
Chinese, English and Japanese; returns a short list with eligibility verdicts, deadlines and
official sources; includes adjacent and non-obvious directions.

### Example 2 — not job-hunting

```text
我不想找工作，就是最近有点闲，有什么值得做的吗？
```

Expected behaviour: lowers the weight of career/education and looks at competitions, open source,
projects, skill programmes, events and hobbies instead. It will not keep recommending internships.

### Example 3 — capability backfill

```text
我想以后做 Embedded AI，但是不知道现在应该做什么。
```

Expected behaviour: searches **real** Embedded AI opportunities, extracts what they actually
require, then searches competitions/projects/open-source/skill programmes that build exactly those
requirements — instead of printing a generic "learn C++ / learn RTOS" list.

### Example 4 — gap analysis

```text
我现在缺什么？为什么很多机会我都申请不了？
```

Expected behaviour: reports requirement frequency across the opportunities actually scanned, e.g.
"in the 23 postings scanned, RTOS appears in 9", and pairs each gap with opportunities that would
close it. It always states the sample size and never claims market-wide statistics.

An output-format walkthrough (fictional data) is in
[`examples/discovery-output.example.md`](examples/discovery-output.example.md).

---

## 🧱 Project structure

```
OpportunityRadar/
├── SKILL.md                          # the protocol: triggers, modes, 13 steps, rules, self-check
├── README.md  README.zh-CN.md        # English / 简体中文
├── DEVELOPMENT.md                    # design decisions, acceptance scenarios, QA checklist
├── LICENSE  .gitignore
├── references/                       # loaded on demand, one concern per file
│   ├── opportunity-taxonomy.md        # 13 categories, sources, multilingual query patterns
│   ├── search-strategy.md             # search matrix, expansion rules, 70/20/10, budgets
│   ├── profile-building.md            # progressive profile, when to ask, memory reuse
│   ├── trust-policy.md                # Tier A–D, discovery vs confirmation, freshness
│   ├── extraction-policy.md           # field rules, evidence status, anti-hallucination
│   ├── eligibility.md                 # hard-constraint order, 5 verdicts, missing-data policy
│   ├── ranking.md                     # Match vs Priority, weights, coverage, value rubric
│   ├── output-format.md               # answer templates, length budget, JSON artifact
│   └── state-and-feedback.md          # seen/saved/ignored, change detection, gap wording
├── schemas/
│   ├── profile.schema.json            # user profile (JSON Schema draft 2020-12)
│   └── opportunity.schema.json        # opportunity record incl. evidence/provenance
├── scripts/                          # deterministic helpers, stdlib only, no network
│   ├── common.py                      # single source of truth: enums, URL, ID, contract checks
│   ├── normalize_date.py              # deadlines → ISO + deadline_type + urgency
│   ├── dedupe.py                      # cycle-aware clustering, conflict report
│   ├── score.py                       # eligibility pre-check, Match/Priority components
│   └── state.py                       # seen/saved/ignored, change detection, feedback
├── examples/                         # fictional data, for format and tooling demos
└── tests/                            # unittest suite (stdlib; jsonschema optional)
```

> All data under `examples/` is **fictional** and marked as such in each file. Never reuse it as
> verified opportunity data.

---

## 🔧 Helper scripts

Deterministic work is done by code, not by the model: dates, duplicate detection, base scoring,
state. Each script is standalone and safe to run by hand.

### `normalize_date.py` — deadlines and windows

```bash
python3 scripts/normalize_date.py "9月20日-10月5日" --default-year 2026 --now 2026-09-14
```

```json
{
  "iso": "2026-09-20",
  "end": "2026-10-05",
  "deadline_type": "range",
  "urgency_days": 21,
  "days_until_start": 6,
  "days_until_end": 21,
  "year_unknown": true,
  "notes": [
    "原文未写年份，按 --default-year 2026 填充（请复核）",
    "紧迫度以区间截止端点为准（urgency_days = days_until_end）"
  ]
}
```

Key behaviours: `rolling` / `asap` / `flexible` / `tbd` are **distinct** states (a rolling intake
and an unannounced date call for different action); a missing year is reported, never invented;
times and timezones are preserved without fake UTC conversion. 26 sample inputs:
[`examples/dates.example.txt`](examples/dates.example.txt).

### `dedupe.py` — duplicate detection

```bash
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --format text
```

```text
input=8  clusters=7  removed=1

[c001] size=2 canonical=nagi-robotics-2027-summer-internship-program
  title: 2027 Summer Internship Program
  org  : Nagi Robotics, Inc.
  - merged in: nagi-robotics-summer-internship-2027
```

Three guards keep it from over-merging: a **cycle guard** (the same official URL is often reused
year after year — 2026 and 2027 stay separate), **conservative URL normalization** (only `utm_*`
and clear click-tracking parameters are dropped; paths keep their case), and a **coherence check**
that prevents A~B, B~C chaining from fusing A and C. Conflicts between sources are reported
rather than silently resolved.

### `score.py` — eligibility pre-check and ranking components

```bash
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --output /tmp/clusters.json
python3 scripts/score.py --profile examples/profile.example.json \
                         --opportunities /tmp/clusters.json --today 2026-09-14 --format table
```

```text
| # | 机会 | 类别 | Match | 紧迫 | Priority | 档 | 资格 | 判定来源 |
|---|---|---|---|---|---|---|---|---|
| 1 | Nagi Robotics Robot Hackathon | competition | 81 | 35 | 74 | Medium | Eligible | hard_constraint |
| 2 | 2027 Summer Internship Program | career | 74 | 68 | 73 | Medium | Probably Ineligible | hard_constraint |
| 3 | Kagura University Undergraduate Research Program | research | 65 | 35 | 60 | Medium | Unknown | hard_constraint |
```

(That output is a deliberate demonstration: the fictional Nagi internship targets March 2028
graduates while the example profile graduates in June 2028 — different cohorts, so it is
ineligible. The Kagura entry is `Unknown` because the profile has no JLPT score; the skill does
not assume one.)

Behaviours: `Priority = 0.85 × Match + 0.15 × Urgency`; unknown requirements score neutrally
instead of zero; hard constraints cannot be overturned by a model verdict; a mismatched score
scale (GPA 3.0/4.0 vs 85/100) yields `Unknown` rather than a fabricated conversion.

### `state.py` — local memory

```bash
python3 scripts/state.py init
python3 scripts/state.py mark-seen --input .opportunity-radar/last-run.json
python3 scripts/state.py feedback saved --id <id> --category competition --tags robotics
python3 scripts/state.py list --status saved
python3 scripts/state.py suggest
```

Change detection tracks eight fields (`deadline`, `application_open`, `cost`, `compensation`,
`education_level`, `student_year`, `language_requirement`, `official_url`). Adding `utm_*`
parameters does **not** count as a change. `suggest` only prints weighting advice — it never
rewrites the profile.

### `common.py` — shared foundations

Enums, URL canonicalization, ID generation and lightweight contract validation live here so that
`dedupe.py`, `score.py` and `state.py` cannot drift apart.

```bash
python3 scripts/common.py --url "https://www.Example.com/Path/To/Page/?b=2&utm_source=x&a=1"
# example.com/Path/To/Page?a=1&b=2

python3 scripts/common.py --validate examples/opportunity.batch.example.json
# checked=8 errors=0
```

---

## 🛡️ Source verification and trust

| Tier | Examples | Use |
|---|---|---|
| **A** | official programme/company/university/government/lab/competition sites | may be cited as fact |
| **B** | university career centres, academic societies, industry associations, official partners | may confirm; A wins on conflict |
| **C** | LinkedIn, job boards, competition/event aggregators, technical communities | **discovery only** |
| **D** | blogs, forums, personal posts, reposts, unofficial articles | discovery and leads only |

Rules: C/D discovers, A/B confirms. When a third party says 9/20 and the official page says 9/25,
the official date is used and the difference is reported. If no canonical source exists the answer
says "未找到官方确认来源" — links are never invented. Freshness is tracked per type
(competitions 14 days, internships 30, scholarships 60, evergreen resources 180).

---

## 🔒 Local state and privacy

```
.opportunity-radar/
├── profile.json     # cached profile (only needed when the host has no memory)
├── seen.json        # first/last seen, tracked-field hash, change log
├── saved.json       # interested / saved / applied
├── ignored.json     # ignored / not_relevant
└── last-run.json    # last discovery artifact
```

Everything stays on the local filesystem; the scripts make no network requests. The directory is
git-ignored and optional — the skill works without it. No credentials, contact details or
documents are stored.

Application and contact actions (submitting forms, emailing, registering, uploading personal
data) are outside the discovery workflow and remain the user's own step.

---

## ⚠️ Limitations

- **Requires a web-capable host.** Without web access the skill says so and stops rather than
  guessing.
- **No market-wide statistics.** Gap analysis describes the sample that was actually scanned, and
  says so every time.
- **Judgement is still needed** for `related field` eligibility, fuzzy duplicates and value
  ratings; the scripts supply deterministic signals, not decisions.
- **Time-sensitive by nature.** Re-verify `last_verified` before relying on a result.
- **Language coverage** is strongest for Chinese, English and Japanese; other languages follow the
  same pattern but are less battle-tested.
- **No automatic applications.** Discovery, verification, assessment and explanation only.

---

## ✅ Tests

```bash
python3 -m unittest discover -s tests -t tests
```

Standard-library `unittest`; `jsonschema` is optional and used only to meta-validate the schemas
and run positive/negative cases. The suite covers date semantics, URL/ID contracts, duplicate
guards, eligibility authority, missing-data policy, state transitions, schema contracts and
cross-file consistency (enums and weights must match `scripts/common.py`).

Maintenance notes, design decisions and the live-web acceptance scenarios live in
[DEVELOPMENT.md](DEVELOPMENT.md).

---

## 📄 License

MIT — see [LICENSE](LICENSE).
