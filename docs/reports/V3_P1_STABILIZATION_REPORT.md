# V3 / P1 稳定化总报告（Stabilization Round）

日期：2026-09-20 · 本轮完成：① Gap 相关性判据 ② IoT 67% known failure 修复 ③ 真人测试体系
测试：**378 → 386 全绿** · CI 3.8 / 3.12 通过

---

## 1. Gap relevance 实现

`scripts/gaps.py`：

```
Requirement → Potential Gap → **Gap Relevance** → Development Gap → Bridge Search
```

- `career_direction(profile)` 从 `career_state`（switch / entrepreneurship / management /
  promotion_target / compensation）与 `goals` 推出**当前方向**（promotion / switch / research /
  education / entrepreneurship / skill_upgrade / income / explore）。
- `DIRECTION_AFFINITY`：每个方向关联的缺口类型（不是关键词硬匹配）。
- `gap_relevance()` → `core_gap` / `supporting_gap` / `contextual_gap` / `irrelevant`，并给出理由。
- **学术味道缺口**（教授 / lab / 学会 / 论文 / research）在非 research·education 方向下**最多算
  contextual**；无明确方向（explore）时**一律不产生 core_gap**。
- `development_gaps()` = core + supporting；`gap_to_bridge_report()` 默认**只对发展缺口**做 Bridge
  搜索（contextual 需显式 `include_contextual=True`），避免浪费 query 预算。

## 2. before / after 示例

场景：**后端工程师，目标升 Senior**（Case C 的真实问题）

| 缺口 | before（只看 requirement） | after（加相关性判据） |
|---|---|---|
| `research` | 与其它缺口同等对待 | **contextual_gap** — 学术向、与 promotion 关系弱 |
| `professor contact` | 同上 | **contextual_gap** |
| `ownership` / `system design` | supporting | **supporting_gap**（Bridge 搜索保留） |
| 公开影响力（演讲 / maintainer） | supporting | **supporting_gap** |

场景：**Embedded → Edge AI**（转方向）
- `TinyML` 在 2 个目标机会中构成硬要求 → **core_gap**，Bridge 搜索优先。

场景：**没有明确目标**
- 所有缺口 = `contextual_gap`，`development_gaps()` 为空 → 不制造"人生建议"。

## 3. IoT 67% 根因

复现并定位（不是沿用旧猜想）：

> Round-2 的 3 条主推荐中，1 条（全国大学生智能汽车竞赛 `smartcarrace.com`）只有
> `verification_status = verified_official`，**却没有 `evidence.application_status` 结构**。
> 当时的 gate 只检查"是否标记为已核实"，不检查证据结构，于是这条被计入「已核实」，
> 把最终验证率压到 67%（2/3）。

分类：`evidence_extraction`（官方域可访问但返回无关"成果库"页 → 报名证据无法抽取）。
另一条失败（ETロボコン 2026）是 `fact`：页面为当前信息但 2026 报名已关闭。

## 4. IoT 修复方式

不是改阈值、不是删失败、不是把未验证项移出统计，而是**补上缺失的那道门**：

- 主推荐 gate 现在要求 `canonical source` + `verified_official` + **带日期的
  `evidence.application_status`**（`scripts/evidence.py` 前置检查）；
- 缺结构的机会**一律降级**到 `worth_verifying`，不计入"已核实"；
- 配套 `source_freshness` 拒绝把历史页面当作当前证据。

## 5. IoT 最新 verification（2026-09-20 真实联网重跑）

| 指标 | 值 |
|---|---|
| discovered / qualified / recommended / verified | 6 / 5 / **4** / **4** |
| downgraded / excluded | 1 / 1 |
| **final recommendation verification** | **100%**（阈值 80%） |
| expired leakage | **0** |
| unverified actionable leakage | **0** |

独立复核（我自己逐条检查，不只信摘要）：4 条主推荐全部带 2026-09-20 当日的
`source_url` + `verified_at` 官方证据（openUBMC / openEuler / 全国大学生嵌入式芯片设计竞赛 / Mujin）。

**没有通过"把推荐数压到 1 条"来机械达标**：推荐数是 4。

## 6. known failure 是否关闭

**已关闭，且关闭是可机器校验的。**

- `benchmarks/known_failures.json`：`known_failures` 现为**空**；IoT 移入 `resolved_failures`，
  带 `old_value 67 / new_value 100 / threshold 80 / root_cause / fix / measured_by /
  verification_measurement / failure_classification / history_note`。
- `benchmarks/_metrics-stabilization.json`：实测值机器可读；
  `tests/test_benchmark_consistency.py` 新增两条测试：
  - `test_resolved_failures_really_pass`：已关闭的失败必须有 ≥ 阈值的**实测值**，且不得低于旧值
  - `test_resolved_persona_not_still_active`：同一失败不能同时在 active 与 resolved
- **历史没有抹掉**：`gates.json` 仍保留 round-2 的 67% 数值，只多了一个 `status: resolved` 标记；
  旧报告文字未改写。

## 7. 全 benchmark 状态

| 检查项 | 结果 |
|---|---|
| 全部 unit tests | **386 passed** |
| round-2 gates（历史） | expired leakage 0 / unverified leakage 0（4/4 persona）；IoT 验证 67% → 已 resolved |
| stabilization 轮 | IoT 100%；Case B 100%；C/D/E 主推荐分别为 4 / 4 / 2，均 0 标注不一致 |
| 5 个 Gap/Portfolio persona | `bridge_verified_rate` 1.00、`bridge_actionable_rate` 1.00、`portfolio_resource_conflict_rate` **0.00** |
| `gap_coverage_rate` | 0.53（**口径变化**：现在只对 development gaps 计，contextual 不再进分母 —— 数值下降是诚实的，不是退步） |
| stage 规划 | `stage_inapplicable_query_rate` **0.00**、`stage_family_precision` **1.00** |
| source stale leakage | **0** |
| gap noise | 0.00（合成检查）/ 0.125（Case C 显式测量，logistics 已出分母） |

## 8. C / D / E 状态（SI + refinement 轮）

| Case | gate 计算 | 备注 |
|---|---|---|
| D 在职申硕 | recommended 4 / worth 3 / excluded 1 | 研究缺口覆盖 0.50 → **0.75** |
| C 升 Senior | recommended 4 / worth 1 / excluded 3 | 招聘类占比 0；SIG/maintainer/CFP 构成 |
| E 无目标 | recommended 2 / worth 7 / excluded 0 | 无缺口、不过搜索，general search 主导 |

所有手工标注与真实 gate 已对齐（0 处不一致；原标注保留在 `zone_declared_by_agent`）。

## 9. 当前还剩哪些 FAIL

**没有 active 的声明失败。** 需要区分两类"还不是满分"的地方（都不是 gate 失败）：

1. **`gap_coverage_rate` 0.53**：语言/研究类缺口在部分场景仍找不到真实 Bridge —— 这是**机会本身稀缺**，
   不是规则失败；已如实记录，不设硬阈值。
2. **预算未知时 Portfolio 给出较大计划**（36h / 107h）：已改为 `budget_unknown=true` +
   `resource_conflict=None`，不再谎报"无冲突"；是否要限制条数属于 **UX 假设**，等真人测试再定。

## 10. 真人测试目录和方法

`usertests/real/`：`README.md`（5 类用户 × 1–2 人、30–40 分钟流程、记录纪律）、
`SESSION_TEMPLATE.md`（画像 / 回答摘要 / 行为表 / 8 个指标 / 6 个主观问题 / 观察笔记）、
`METRICS.md`（行为指标定义 + 系统侧辅助指标 + **事先定好的判读规则**）、
`CONSENT_OR_PRIVACY_NOTE.md`（收集/不收集、只用代号、本地存放、可删除、系统局限）。

- `usertests/real/sessions/` 已加入 `.gitignore`（含个人信息，不入库）
- 汇总写到 `usertests/real/SUMMARY.md`；**不得用 LLM judge 替代真人行为**
- 第一轮只求发现"哪里没用/奇怪/太多/太泛/漏掉重点"，不追求统计显著性

## 11. 当前架构还有没有明显 blocker

**没有 blocker。** 已知的边界都已有明确处理方式：

| 边界 | 现状 |
|---|---|
| 反爬 / JS 渲染官方页 | 记录为 infrastructure 失败，降级而非伪造（LFX、picoCTF、smartcarrace） |
| 历史页面 | `source_freshness` 判 historical，可 discovery 不能当当前证据 |
| 没有明确目标 | 不造 Gap、不造 Goal，只用低成本/探索角色 |
| 预算未知 | 显式标注未知，不谎报"无冲突" |
| 机会本身稀缺（在职者的不脱产研究经历） | 如实说明"本轮未找到"，不凑数 |

## 12. 哪些功能已经足够稳定（可以停手）

- 事实链：canonical source / freshness（机会 + 页面两层）/ evidence 前置检查 / dedupe
- 资格与准备度：eligibility（evidence gate）、readiness、冲突（时间 / dealbreaker）
- 决策层：Match / Priority / Utility 三层分离，Portfolio 资源约束（冲突率 0）
- 召回层：locale + place hints、minimal source intelligence（阶段敏感、非白名单）
- 运营层：benchmark gates + known/resolved failures 的机器化校验

## 13. 哪些功能应该停止继续优化

Watch / Delta Scan、Application Lifecycle、更多 locale、新 taxonomy、更多 source family、
新 profile 字段、UI、复杂 ranking（ML reranker / 向量库）、大规模 crawler。
**除非真人测试出现明确失败，不再扩。**

## 14. V3 是否可以进入"真实用户测试阶段"

**可以。** 理由：

- 全部 hard quality gate 达标：expired leakage 0、unverified actionable leakage 0、
  主推荐核验率 100%（IoT / Case B）、resource conflict 0、stale leakage 0
- 声明失败已清零（唯一一个已 resolved 且可机器校验）
- 5 类真人测试用户、指标定义、判读规则、隐私说明已就位，可以开始招募

**下一步（严格按此顺序）**：
1. 招募 5 类用户各 1–2 人，跑第一轮 session（不改代码，只记录）
2. 汇总 Action Rate / Surprise Rate / False Positive Rate
3. 只针对真人暴露的失败做最小修复（不再凭想象加规则）
4. 预算未知时的结果条数问题，等真人反馈后再定规则

**本轮起停止核心架构重构。** 除非出现 P0 级真实失败。
