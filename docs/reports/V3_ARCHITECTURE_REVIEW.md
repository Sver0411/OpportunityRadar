# V3 Architecture Review

版本演进：`Personal Opportunity Search Skill` → `Personal Opportunity Intelligence & Decision Skill`
基线：main @ `3dd3d0f`（275 tests 全绿）
原则：evolution，不是 rewrite；兼容现有 profile / opportunity JSON；新字段默认 optional。

---

## 1. 现状里哪些部分保留（不重写）

| 能力 | 当前载体 | V3 处理 |
|---|---|---|
| 13 个一级 category | `references/opportunity-taxonomy.md` + `common.CATEGORIES` | **保留**，只扩“职业阶段含义”（§7 需求） |
| 渐进式画像 + provenance | `profile.schema.json` + `references/profile-building.md` | **保留**，新增字段一律 optional |
| locale / place_hints / precedence | `scripts/locales.py` | **保留**，V3 只消费，不改逻辑 |
| deadline → freshness（open/likely_open/unknown/closed/expired/future） | `normalize_date.freshness()` + exclusion | **保留**，仍是最硬的 gate |
| canonical source gate（无 official_url 不进主推荐） | `score.py` `no_canonical_source` + zone | **保留** |
| eligibility + evidence gate（explicit 才能淘汰） | `score.eligibility_component()` | **保留**，新增的 readiness 与之**分离** |
| dedupe / cycle detection | `scripts/dedupe.py` | **保留** |
| seen/saved/ignored/applied | `scripts/state.py` | **保留并扩展**为 application lifecycle |
| Match / Priority / weights | `score.py` | **保留**（compatibility），Utility 作为**第三层**叠加 |
| 三区输出（recommended / worth verifying / excluded） | `output-format.md` | **保留**，升级为 portfolio 结构 |
| benchmarks + usertests | `benchmarks/`、`usertests/` | **保留**，加自动一致性校验 |
| 用户新加的 `region` / `program_degree` / `cohort_year` / `application_status` / `organization_*` | schemas + score | **保留**，作为 V3 的事实基础 |

## 2. 哪些 schema 需要扩展

**profile.schema.json（新增，全部 optional、兼容老文件）**
```
life_stage[]            student / working / studying_and_working / career_break /
                        unemployed / self_employed / founder
career_stage[]          pre_college / undergraduate / graduate_student / new_grad /
                        early_career / mid_career / senior_ic / manager / executive /
                        researcher / founder / freelancer / career_switcher / returning_to_work
employment{}            status, industry, company_type, company_size, role, function,
                        seniority, years_of_experience, management_level, employment_type
career_state{}          current_direction, target_role, target_industry,
                        target_company_type, target_country, promotion_target,
                        switch_intent, management_intent, specialist_intent,
                        entrepreneurship_intent, compensation_growth_intent,
                        work_life_balance_intent, timeline, growth_bottlenecks[]
decision_preferences{}  risk_tolerance, competition_tolerance, time_horizon,
                        prefer_public_output, prefer_low_commitment, prefer_high_upside,
                        prefer_structured_program, prefer_independent_work,
                        prefer_networking, prefer_remote, prefer_paid
dealbreakers[] / green_lights[]   自由文本（用户语言），参与 gate 与解释
```

**opportunity.schema.json（新增，全部 optional）**
```
outcomes{}              13 个 outcome facet × High/Medium/Low/Unknown
readiness{}             status, estimated_preparation, ready_items[], missing_items[], blockers[]
effort{}                estimated_hours, weekly_commitment, duration, preparation_complexity
cost{}                  application_cost, participation_cost, travel_cost, opportunity_cost
time_to_value           immediate / weeks / months / long_term / unknown
schedule_flexibility    high / medium / low / unknown
career_capital{}        skill/portfolio/network/reputation/credential/domain/management/research
future_optionality      High / Medium / Low / Unknown（+ reason）
career_leverage         High / Medium / Low / Unknown（+ reason）
prerequisites[] / produces[] / unlocks[]
related_opportunities[] / goal_contribution[]
```

> `unlocks[]` 允许 `{type, label, opportunity_id?}`：没发现的后续机会用 type，发现了就链真实 ID。

**不属于 schema 的（放 local state）**：`watches.json`、`sources.json`、`search_coverage`（run artifact）。

## 3. 哪些 reference 需要改

| 文件 | 改动 |
|---|---|
| `opportunity-taxonomy.md` | 每类补“职场阶段含义”（career / education / research / networking / entrepreneurship） |
| `profile-building.md` | 加 life_stage / career_stage / employment / career_state / decision_preferences 的渐进式提问与 provenance |
| `extraction-policy.md` | outcome / effort / cost / career_capital 的抽取纪律（explicit vs inferred 必须分） |
| `eligibility.md` | 明确 eligibility ≠ readiness（新增 readiness 章节引用） |
| `ranking.md` | 加 Match / Priority / **Utility** 三层分离 |
| `output-format.md` | 三区 → Portfolio 结构；每条机会的回答清单 |
| `trust-policy.md` | source intelligence + coverage 说明（不得声称“搜遍全部”） |
| `search-strategy.md` | intent 层（discover / promotion / career_switch …）+ unknown-unknown 七类相邻 |
| `state-and-feedback.md` | application lifecycle + watch / delta scan |

## 4. 哪些 scripts 需要改 / 新增

| 文件 | 处理 |
|---|---|
| `common.py` | 新增枚举：LIFE_STAGES、CAREER_STAGES、OUTCOME_FACETS、READINESS_STATUSES、TIME_TO_VALUE、FLEXIBILITY、CAPITAL_DIMS、UTILITY_BANDS、APPLICATION_STATUSES（保持单一事实来源） |
| `readiness.py` | **新增**：资格之外的“离开始还有多远”（ready/missing/blockers + status） |
| `graph.py` | **新增**：produces → unlocks → goal_contribution；gap → bridge 推荐 |
| `coverage.py` | **新增**：search coverage ledger（region/locale/category/query_count…） |
| `utility.py` | **新增**：Personal Utility（High/Medium/Low + 理由），消费 eligibility/goal/readiness/outcome/effort/cost/optionality/trust/urgency |
| `score.py` | 保留 Match/Priority；读取 new fields 但不改权重；gate 增加 readiness / effort conflict / dealbreaker conflict |
| `state.py` | 扩展 lifecycle 状态 + watch 定义（P1 的完整 delta scan 留在 P1） |
| `dedupe.py` / `locales.py` / `normalize_date.py` | 不动（除必要的字段兼容） |

## 5. 哪些 tests 会受影响

- 新增：`test_readiness.py`、`test_graph.py`、`test_utility.py`、`test_coverage.py`、`test_benchmark_consistency.py`
- 一致性测试扩展：新枚举必须出现在 `common.py` 且被 schema / 文档引用（沿用现有 `test_consistency.py` 模式）
- 老测试：老 profile / opportunity JSON 不含新字段 → 全部必须继续通过（这就是兼容性回归）

## 6. 兼容性风险

| 风险 | 处理 |
|---|---|
| 新枚举进 schema 后老 JSON 校验失败 | 新字段全部 optional，无 `required` 新增 |
| Utility 与 Priority 语义混淆 | Utility 只输出 High/Medium/Low + 理由，不输出数字分数 |
| 职场用户被学生机会淹没 | career_stage 参与过滤与排序（P0 只做基础：不匹配学生专属机会时降权/标注） |
| unlocks 编造 | 未发现的后续机会只写 `type`，禁止编造 opportunity_id |
| 文档与数据矛盾（67% vs “all gates passed”） | `test_benchmark_consistency.py` 直接读 metrics 校验阈值与报告文字 |

## 7. P0 具体改动清单（本轮实施）

1. `common.py`：新增 9 组枚举（单一事实来源）
2. `schemas/profile.schema.json`：life_stage / career_stage / employment / career_state / decision_preferences / dealbreakers / green_lights
3. `schemas/opportunity.schema.json`：outcomes / readiness / effort / cost / time_to_value / schedule_flexibility / career_capital / future_optionality / career_leverage / prerequisites / produces / unlocks / related_opportunities / goal_contribution
4. `scripts/readiness.py`、`graph.py`、`coverage.py`、`utility.py`（新模块，纯 stdlib）
5. `score.py`：gate 增加 readiness / effort conflict / dealbreaker conflict（不改权重）
6. taxonomy：5 个类别补职场含义
7. `SKILL.md`：工作流从 13 步演进到“理解人 → 理解阶段 → 覆盖计划 → 发现 → 验证 → 判断 → 决策 → 组合 → gate” + intent 层 + portfolio + coverage 说明
8. benchmarks：新增 7 个职业 persona；新增 `test_benchmark_consistency.py`
9. 清理过期描述：usertests/README 的城市级定位缺口标注为 historical（fixed in `18262b4`）
10. 跑全量测试 + 新增测试

## 8. 建议的新数据结构（摘要）

```jsonc
// opportunity（片段）
"outcomes": {"portfolio": "High", "skill": "High", "network": "Medium", "financial": "Low"},
"readiness": {"status": "minor_preparation",
              "ready_items": ["学历满足"], "missing_items": ["英文 CV", "Demo 链接"]},
"effort": {"weekly_commitment": "6-8 h", "preparation_complexity": "medium"},
"cost": {"application_cost": "free", "participation_cost": "unknown"},
"time_to_value": "months", "schedule_flexibility": "medium",
"career_capital": {"skill_capital": "High", "network_capital": "Medium"},
"future_optionality": {"level": "High", "reason": "公开成果 → 后续实习/研究通道"},
"career_leverage": {"level": "Medium", "reason": "可验证成果 + 稀缺经历"},
"produces": [{"type": "public_repo", "label": "GitHub 仓库"}],
"unlocks": [{"type": "embedded_internship", "label": "嵌入式实习", "opportunity_id": null}],
"goal_contribution": ["Japan Embedded AI"]
```

## 9. 不应该实现 / 应该延后（本轮不做）

- **不做**：向量库、ML reranker、爬虫集群、Web SaaS、登录、后台常驻调度器
- **延后到 P1**：Watch/Delta Scan 完整实现、Source Intelligence 状态文件、Opportunity Portfolio 自动分栏、Gap→Bridge 自动检索、Application Lifecycle 全状态机
- **延后到 P2**：Goal Roadmap、更多 locale、职业细分枚举、长期 analytics
- **明确不做**：录取概率、薪资预测、（已禁止）

---

审查结论：现有架构**不需要重构**，V3 是在其上叠加“理解人（阶段/职业状态/决策偏好）+ 理解价值（outcome/effort/optionality）+ 理解关系（graph/bridge）+ 决策（utility/portfolio）”。
