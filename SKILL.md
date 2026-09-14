---
name: opportunity-radar
description: Personal opportunity discovery protocol for students, graduate students, and early-career users. Activates when the user asks what opportunities fit them, what they should do next, or whether there are competitions / internships / research programs / open-source programs / scholarships / student programs / events worth joining — including opportunities they would not have known to search for. Triggers include "最近有什么适合我的机会", "我最近可以做点什么", "有没有适合我的比赛/实习/科研/开源项目", "有没有我可能不知道的机会", "我想提高以后找嵌入式实习的竞争力现在做什么最好". Do NOT activate for plain factual lookups (e.g. "AWS 是什么", "TOEIC 什么时候考试") unless the user asks to evaluate it against their own situation.
agent_created: true
license: MIT
---

# OpportunityRadar

Find the opportunities you didn't know to search for.

A personal opportunity discovery **protocol** for a web-capable host agent. It turns
"帮我搜几个实习" into: understand user → expand queries → discover across categories →
verify at official sources → extract → dedupe → judge eligibility → rank → explore adjacents → explain.

The skill does not replace the host agent. It reuses the host's web search, browser, fetch,
shell, code execution, file I/O, and memory, and adds the protocol, taxonomy, policies, and
deterministic helpers that a bare agent does not have.

---

## 0. Host capability check (do this once per session)

| Host capability | Required? | How the protocol uses it |
|---|---|---|
| Web search | **Yes** | Broad discovery, local-language queries |
| Fetch / page read | **Yes** | Confirm facts at canonical sources |
| File read/write | Recommended | Local state, JSON artifacts, profile |
| Shell / Python | Recommended | `scripts/*.py` for dates, dedupe, scoring, state |
| Browser | Optional | JS-rendered or login-gated official pages |
| Memory | Optional | Reuse a known profile before asking |

If the host has **no web capability**, say exactly this and stop:

> Opportunity discovery requires a web-capable host agent.

Do not silently fall back to an unconfigured third-party API, a cached dataset, or invented data.

---

## 1. When to activate

Activate when the request implicitly or explicitly asks *"what should **I** do / join / apply to?"*
or *"what exists that fits someone like me?"*:

- 最近有什么适合我的机会？ / 有没有我可能不知道的机会？
- 我最近可以做点什么？ / 最近有点闲，有什么值得做的吗？
- 有没有适合我的比赛 / 实习 / 科研 / 开源项目 / 奖学金 / 学生计划？
- 有什么适合我专业的东西？ / 有没有含金量高的活动？
- 我想找点科研做。 / 有没有学生能申请的项目？
- 我想提高以后找嵌入式实习的竞争力，现在做什么最好？ ← capability-gap mode (§4, Mode D)
- 我现在缺什么？ / 为什么很多机会我都申请不了？ ← gap analysis (§8.6)

### Do NOT activate (plain lookup)

| User says | Why not | What to do instead |
|---|---|---|
| "AWS 是什么？" | Definitional | Answer directly |
| "TOEIC 什么时候考试？" | Factual lookup | Answer directly |
| "翻译一下这个 JD" | Transform | Translate |
| "帮我改简历" | Not discovery | Out of scope |

**Boundary rule:** if the same topic follows with *"根据我的情况看看要不要考"* /
*"适不适合我"* / *"值得参加吗"*, the request becomes discovery → activate.

If a plain lookup is followed by a discovery follow-up, answer the lookup first (one or two
lines), then run the protocol. Do not make the user re-ask.

---

## 2. Non-goals (hard)

Never build or produce: a website, dashboard, React app, SaaS backend, login/account system,
cloud database, crawler platform, recommendation model, mobile app, payment flow.

Never do on the user's behalf without explicit, separate authorization in that same turn:
submit applications, send emails, register, upload personal data, or contact organizations.
Default responsibilities are: **discover, verify, judge, explain, organize.**

If the user asks you to auto-apply, state the boundary in one line and offer to prepare the
materials checklist instead.

---

## 3. Resource map — load only what the task needs

| File | Load when | Contents |
|---|---|---|
| `references/opportunity-taxonomy.md` | Step 2 always; step 4 for the category being searched | 13 categories, subcategories, where each lives, query patterns |
| `references/search-strategy.md` | Steps 2–4 | Search matrix construction, expansion rules, 70/20/10, local language, budgets, modes |
| `references/profile-building.md` | Step 1 | Minimum viable profile, when to ask, memory reuse, local profile file |
| `references/trust-policy.md` | Steps 6–7 | Tier A–D, discovery vs confirmation, conflict handling, freshness |
| `references/extraction-policy.md` | Step 8 | Field-by-field extraction, Explicit/Inferred/Unknown, anti-hallucination |
| `references/eligibility.md` | Step 10 | Deterministic-first checks, 5-level verdicts, semantic rules |
| `references/ranking.md` | Steps 11–12 | Match vs Priority, weights, diversity quota, value rubric, reason writing |
| `references/output-format.md` | Step 13 | Answer templates, length budget, JSON artifact |
| `references/state-and-feedback.md` | Any time `.opportunity-radar/` exists or the user reacts | Seen/saved/ignored, change detection, gap analysis wording |

Scripts (deterministic; never re-implement these inline):

| Script | Use for |
|---|---|
| `scripts/normalize_date.py` | Any deadline/date string → ISO, ranges, "year unknown" |
| `scripts/dedupe.py` | Cluster duplicate opportunities, pick canonical + conflicts |
| `scripts/score.py` | Deterministic Match/Priority components to base ranking on |
| `scripts/state.py` | seen/saved/ignored CRUD, change detection, feedback suggestion |

Schemas: `schemas/opportunity.schema.json`, `schemas/profile.schema.json`.
Missing field → `null`. Never guess.

---

## 4. Step 0 — pick the mode, then reweight

| Mode | Signal | Reweight |
|---|---|---|
| **A. Profile discovery** (default) | "最近有什么适合我的机会" | Balanced across goals |
| **B. Non-career** | "我不想找工作 / 有点闲，有什么值得做的" | ↓ Career ↓ Education; ↑ Competition, Open Source, Project, Skill, Event, Hobby |
| **C. Unknown-unknowns** | "我可能完全不知道的机会" | ↑ Adjacent + Explore to ~45%, include non-traditional paths |
| **D. Capability gap backfill** | "我想以后做 X，现在做什么最好" | Search **real** X opportunities → count requirement frequency → search opportunities that build exactly those requirements |

Mode is not exclusive; combinations are normal (B+C is common). Record the chosen mode in the
answer header so the user can see why the mix looks the way it does.

---

## 5. The workflow (13 steps, in order, no shortcuts)

> Forbidden: one search → return results. Every step leaves a concrete artifact.

**1. Understand User.** Build/refresh the profile. Reuse host memory first. Start from whatever
the user already said; a single sentence ("我是大二物联网专业，最近有什么值得参加的？") is
enough. Do not interrogate. See `references/profile-building.md`.

**2. Build Opportunity Search Space.** Pick categories from the taxonomy using Goals +
Interests + major_family, not just the literal words the user used. Choose the mode reweighting.

**3. Expand Queries.** Produce a search matrix: `category × layer(exploit/adjacent/explore) × language`.
Expansions must trace back to a profile signal; cap at 2 semantic hops. See `references/search-strategy.md`.

**4. Search Multiple Categories.** Execute the matrix with the host's web capability. Minimum
category coverage for an open-ended ask: **≥5 categories**; for a goal-specific ask: **≥3**.
Never collapse everything into internships.

**5. Discover Candidates.** Cheap breadth-first pass: titles, org, deadline, link.
Record where each was found (`discovery_url`) and its tier.

**6. Find Canonical Sources.** For each credible candidate, locate the official page
(program page, company careers page, university page, organizer site). Tier C/D may discover,
Tier A/B must confirm.

**7. Verify Important Facts.** On the canonical page, confirm at least: **application window /
deadline, eligibility scope, official application path**. Record `verification_status` and
`last_verified`. If no canonical page can be found, write "未找到官方确认来源" — never invent a link.

**8. Extract Structured Data.** Fill the opportunity schema via `references/extraction-policy.md`.
Tag each important field Explicit / Inferred / Unknown. Pass dates through `normalize_date.py`.

**9. Deduplicate.** Same opportunity found on several sites must merge. Run `scripts/dedupe.py`,
then resolve its "maybe" pairs by judgment.

**10. Check Eligibility.** Per high-ranked item give one of: Eligible / Probably Eligible /
Unknown / Probably Ineligible / Ineligible — with the deciding reasons. Never blanket yes/no.

**11. Rank.** Run `scripts/score.py` for components; then apply judgment on top.
Sort primarily by **Priority** (Match + urgency), not Match alone.

**12. Explore Adjacent Opportunities.** Always reserve slots for Adjacent and Explore layers —
this is the reason the skill exists. Target mix in the final answer:
~70% exploit / 20% adjacent / 10% explore (Mode C: roughly 55/25/20).

**13. Return Best Opportunities.** 5–15 genuinely worth-looking items, concise format,
each with: what it is, why it fits, eligibility verdict, deadline, cautions, official source, value.
Then optionally write the JSON artifact to `.opportunity-radar/last-run.json`.

**Pacing.** Prefer quality over completeness. Stop a category when two consecutive query
variants only return already-seen or irrelevant results. Never pad the answer to look thorough.

---

## 6. Cross-cutting rules

1. **Trust.** Tier A/B for facts; Tier C/D for discovery only. Prefer official over third party
   and say so when they conflict (`references/trust-policy.md`).
2. **No fabrication.** No invented URLs, deadlines, requirements, or "official" pages.
   Missing → `null` + "未找到官方确认来源".
3. **Explicit / Inferred / Unknown.** Never upgrade an inference to a fact. A Japanese company
   page without a language requirement does *not* mean "需要 N2".
4. **Eligibility is a verdict with reasons**, not a boolean.
5. **Dedupe before ranking** — otherwise one program eats three slots.
6. **Match ≠ Priority.** A 95-match item closing in 6 months may rank below an 88-match item
   closing in 2 days.
7. **Real requirements over generic advice.** For "怎么提升竞争力" style asks, derive the
   requirement list from actual discovered postings, and quantify as
   "在本次扫描到的 N 个机会中，X 出现在 M 个里" — never "学 X 就能多 N 个机会".
8. **Novelty.** If state exists, mark items already seen; re-show only when something changed
   (deadline, requirement, status).
9. **Never silently rewrite the profile.** Suggest weighting changes instead.
10. **Answer in the user's language.** Keep program names, organization names, and URLs verbatim
    (add a short gloss if the user's language differs).

---

## 7. Output contract

Default: compact. Header (mode + categories covered + count) → 3–6 full blocks → a short
"另一个方向 / Adjacent & Explore" group → "已见过 / 有变化" → optional gap snapshot →
optional one-line next actions.

Every full block answers **为什么推荐给我** with evidence (✓ matched conditions) and
**可能的问题** (△ unknowns / frictions). No block longer than ~10 lines.
Templates, length budget, and the JSON artifact: `references/output-format.md`.

---

## 8. Local state

```
.opportunity-radar/          # optional, relative to the working directory
├── profile.json             # cached profile (only if the host has no memory)
├── seen.json                # opportunity_id → first_seen / last_seen / status / tracked hash
├── saved.json               # Interested + Saved
├── ignored.json             # Ignored + Not Relevant
└── last-run.json            # last discovery artifact (written by step 13)
```

Read state at step 9–13 if the directory exists; write via `scripts/state.py` only.
Never store credentials, contact details, or anything the user did not supply.
Details, feedback semantics, and gap-analysis wording: `references/state-and-feedback.md`.

---

## 9. Self-check before answering

- [ ] Did I use the profile, or did I only use the literal words in the request?
- [ ] Did I search **multiple categories** (not only internships)?
- [ ] Did I expand queries, and did I use the local language for local opportunities?
- [ ] Does every factual claim trace to a Tier A/B source, or is it marked unverified?
- [ ] Did I run dedupe, or is the same program listed twice?
- [ ] Does every recommended item carry an eligibility verdict and a *why*?
- [ ] Are there at least some Adjacent / Explore items the user likely would not have searched?
- [ ] Did I avoid writing files, applying, or contacting anyone?
- [ ] Is the answer 5–15 items, not 100 links?
