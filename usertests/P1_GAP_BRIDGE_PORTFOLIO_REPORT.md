# P1 报告：Gap → Bridge Opportunity + Opportunity Portfolio

日期：2026-09-20 · 基线 `974cd87` · 范围：P1 ①（Gap→Bridge）→ P1 ②（Portfolio）
测试：**324 → 344 全绿** · 指标脚本：`usertests/_p1_metrics.py`

---

## 1. Gap 模型定义

`scripts/gaps.py`。Gap **只能来自真实证据**，来源分级：

| 来源 | 含义 | 例句 |
|---|---|---|
| `requirements` | 本轮扫描到的真实目标机会的硬性要求 | "本轮 3 个目标机会中 2 个要求「RTOS」" |
| `user_stated` | 用户明确说出的目标方向 | "用户在目标中提到「Edge AI」，画像无对应经历" |
| `repeated` | 多个真实机会中重复出现（≥3 次） | "本轮 3 个目标机会中 3 个要求「TinyML」" |
| `semantic` | 语义判断（必须写明依据） | "目标是晋升，画像里没有公开产出" |

**12 种类型**（不要都当技能）：`skill / experience / portfolio / research / language /
credential / network / leadership / management / location_visa / education / public_reputation`

例如：缺论文 → `research`；缺 Staff 级 ownership → `leadership`；缺教授接触 → `network`；
缺签证/地点 → `location_visa`。

无目标、无要求时**不产出任何 Gap**（有测试守卫）。

## 2. Bridge Opportunity 定义

Bridge 仍然是 OpportunityRadar 意义上的**真实机会**（开源 issue / 竞赛 / 项目 / 科研项目 /
开发者计划 / CFP / 社区角色 / 导师角色 / 认证 / 技术委员会 / 真实 build challenge）。
**不默认推荐教程/课程列表** —— 只有确实找不到真实 Bridge 时才回退，并如实说明。

Bridge 与普通机会**使用同一套 gate**：canonical source / current evidence / freshness /
eligibility / verification；`evidence_complete` 为 False 的 Bridge 会被标记（有测试）。

`time_to_evidence` 回答"多久能产生可展示的真实证据"：
3 小时证书 → `medium`；公开 GitHub PR / 论文 / 演讲 → `strong`。

## 3. Graph 改动

`scripts/graph.py` **扩展现有模型**，没有另起一套：

```
User → Gap → Bridge Opportunity → Produced Evidence → Target / Goal
```

- `build_graph()`（原有，机会间 produces/unlocks）保持
- 新增 `time_to_evidence()`、`bridges_for_gap()`（评分）、`bridge_graph()`（统一图）
- 非技能类 Gap 用**意图信号**匹配（`GAP_TYPE_SIGNALS`：类别 + 标签），
  因为中文缺口名与英文 tag 之间没有 token 交集 —— 这是实现中发现并修复的真实缺陷
- `gap_to_bridge_report()` 在找不到 Bridge 时输出 `source_gap.reason = no_real_bridge_found`
  + `query_hint`，直接作为 Source Intelligence 的输入

## 4. Portfolio 构建逻辑

`scripts/portfolio.py`。角色（候选，不是必需）：
`now / bridge / low_cost / high_upside / long_term / explore`

- **角色是挣来的，不是凑的**：`low_cost` 要求 ≤2h/周；`high_upside` 要求 `future_optionality=high`
  或 outcomes 有 high + 长期显现；`explore` 要求 layer=explore 或 novelty≥70；
  `bridge` 必须来自真实的 Gap→Bridge 结果
- 不输出 Top-N：只有达标项才进入对应角色
- `alternatives`：给出"如果你优先升职 → A+B；如果想转方向 → A+C"的对照，**不替用户做人生决定**

## 5. 资源约束逻辑

- 预算：`constraints.weekly_time`（或 `--budget-hours`）
- 每条机会的每周投入：`effort.weekly_commitment` → `estimated_hours` → `time_commitment`
- 贪心选择：角色优先 → utility → match；超出预算的项**丢弃并记录原因**
- 未写明投入的项不计入总和，但记录在 `unknown_hours_items` 并在输出中说明
- **`portfolio_resource_conflict_rate` 必须为 0**（有测试 + 指标脚本校验）

> 本轮修复的真实缺陷：`score.py` 的结果行原先**不带 `effort`**，导致 Portfolio 算不出小时数、
> 资源约束形同虚设（T1 首轮 planned=0h）。现已透传 `effort / time_commitment / time_to_value /
future_optionality / outcomes / produces / layer / small_bet_type`。

## 6. 新增测试

`tests/test_gap_bridge_portfolio.py`（20 例）：

- Gap 模型：样本量必须出现（"本轮 3 个中 2 个"）、**不能都是 skill**、研究类缺口分型独立、目标模糊时不造 Gap
- Bridge：真实 Bridge 优先于课程、`time_to_evidence` 区分 PR 与证书、**不降低真实性门槛**、
  找不到时如实上报、`bridge_graph` 连通 Gap→证据→Goal
- Portfolio：不超预算、冲突率 0、角色不凑栏目、bridge 角色来自真实 Gap→Bridge、给出对照方案
- 5 个场景级用例（技能缺口 / 职业资本缺口 / 研究申请缺口 / 资源冲突 5h / 目标模糊）

## 7. Regression（5 个场景 + 指标）

`python3 usertests/_p1_metrics.py` 实测：

| 场景 | gaps | 覆盖率 | bridges | verified | actionable | graph | 投入/上限 | 冲突 | 角色 |
|---|---:|---:|---:|---:|---:|---|---:|---|---|
| T1 技能缺口（embedded→Edge AI） | 7 | 0.86 | 14 | 1.0 | 1.0 | ✅ | 3.0/6.0 | 无 | bridge, now, long_term |
| T2 职业资本缺口（升 Senior） | 7 | 0.57 | 5 | 1.0 | 1.0 | ✅ | 5.0/6.0 | 无 | bridge, now, high_upside, low_cost, long_term |
| T3 研究申请缺口（日本硕士） | 8 | 0.50 | 4 | 1.0 | 1.0 | ✅ | 5.0/6.0 | 无 | bridge, low_cost, long_term |
| T4 资源冲突（5h/周） | 0 | — | — | — | — | n/a | **5.0/5.0** | **无** | now |
| T5 目标模糊 | 0 | — | — | — | — | n/a | 3.0/5.0 | 无 | now, low_cost, explore |

**P1 指标**

| 指标 | 值 | 目标 |
|---|---|---|
| `gap_coverage_rate` | **0.64** | 不设硬门槛（语言/材料类缺口本轮确实找不到真实 Bridge，如实记录） |
| `bridge_verified_rate` | **1.00** | 1.0 ✓ |
| `bridge_actionable_rate` | **1.00** | 1.0 ✓ |
| `portfolio_resource_conflict_rate` | **0.00** | **0 ✓** |
| `portfolio_diversity`（roles/categories，各场景） | (3,4) (5,2) (3,2) (1,1) (3,1) | 视场景而定，不凑 |
| `graph_connected_rate` | 0.60（有 Gap 的 3/3 场景全部连通） | — |

## 8. 成功案例

1. **T1 技能缺口**：从 3 个真实目标机会中提取出"2 个要求 RTOS、2 个要求 TinyML"，
   Bridge 首选**FreeRTOS good-first-issue（公开 PR）**而不是 RTOS 课程；课程排在后面。
2. **T2 职业资本缺口**：Gap 类型识别为 `public_reputation` + `leadership`（**不是 skill**），
   Bridge 是 CFP 演讲与 maintainer 路径；Portfolio 给出"优先升职 vs 优先转方向"两套组合。
3. **T4 资源冲突**：5h/周预算下，从 5h+4h+3h 三个机会中只保留 5h 那条，另外两条被丢弃并写明原因，
   `resource_conflict = False`。

## 9. 失败案例（如实记录）

1. **语言/材料类缺口找不到 Bridge**：T1 的"Japanese N2"缺口与 T3 的语言缺口在本轮候选池里没有真实机会
   → `gaps_with_bridge` 覆盖率降到 0.5–0.86。系统如实输出 `no_real_bridge_found`，没有用课程凑数。
2. **T3 覆盖只有 0.5**：`network`（教授接触）与 `research`（研究经历）缺口各自只有一个候选桥接，
   说明**研究型 Bridge 的来源召回明显不足**（见第 10 节）。
3. **T4/T5 没有 Gap**（一个没有目标机会、一个目标模糊）→ `graph_connected=False`。
   这是正确行为，但指标上拉低了 `graph_connected_rate`，需在解读时区分"没有 Gap"与"连不上"。
4. **首轮实现缺陷**：非技能类 Gap 用 token 匹配 → 中文缺口名匹配不到英文 tag，Bridge 恒为空；
   `roles_present` 只统计主角色 → 低投入项被当成"now"。两处均已修并有测试。

## 10. 暴露出的 Source Intelligence 需求

| 需求 | 证据 | 后续动作 |
|---|---|---|
| **研究型 Bridge 来源不足** | T3 的 `research` / `network` 缺口各只有 1 个 Bridge；实验室开放讲座、教授招募页几乎没有被召回 | Source Intelligence 优先补：大学实验室/教授主页/研究型 seminar |
| **语言类 Bridge 来源不足** | 语言缺口依赖 `language` 类别，现有来源基本是考试机构官网 | 补：语伴社群、大学语言中心、公司语言支持计划 |
| **evergreen 社区角色的官方入口难找** | T2 的 maintainer 路径只有 1 个候选 | 补：CNCF/开源基金会 contributor 页面清单 |
| **JS 渲染平台页读不到** | 上轮已记录（LFX） | 与 Source Intelligence 一起解决 |

这些是**真实失败驱动的**输入，不是预先建设的庞大 source 库。

## 11. 是否存在"为组成 Portfolio 而塞弱机会"

**没有。** 证据：

- 角色有硬条件（`low_cost ≤2h`、`high_upside` 需 `future_optionality=high` 或高价值 outcome、
  `explore` 需 layer/novelty 达标），不达标不出现
- T4 只有 1 个角色（`now`），T5 有 3 个（`now/low_cost/explore`），T3 没有 `high_upside` ——
  都是"达标才出现"的结果
- 有测试 `test_roles_are_earned_not_padded` 固定这一行为
- 丢弃项必须写明原因，不存在"硬塞进栏位"的路径

## 12. 下一步建议

1. **Source Intelligence（按需，不预先建设）**：按第 10 节的三条真实缺口做最小版本 ——
   研究型来源（实验室/教授）、语言类来源、开源基金会 contributor 页。
2. **Gap 覆盖率提升**：当前 0.64 主要由"研究/语言类缺口无 Bridge"拉低，
   与第 1 点同一根因，做完 Source Intelligence 后重测。
3. **`graph_connected_rate` 口径修正**：应排除"无 Gap"场景（当前分母把 T4/T5 也算进去了）。
4. **Portfolio 与 C/D/E 的整链回归**：把 Gap→Bridge→Portfolio 接到真实 Persona（C/D/E）上跑一次，
   验证"从缺什么 → 现实里补什么 → 一组可执行下一步"在全链上成立。
5. 仍待处理：IoT 最终验证 67% < 80%（`benchmarks/known_failures.json`，声明的 FAIL）。
