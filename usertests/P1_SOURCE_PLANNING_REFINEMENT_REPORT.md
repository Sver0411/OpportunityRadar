# P1 报告：Source Planning Refinement（阶段适配 · 页面时效 · Gap 噪声）

日期：2026-09-20 · 基线 `5e30348` · 范围：① stage × family 可用性 ② 陈旧页面判据 ③ 修完 gap 噪声后重跑 Case C
测试：**356 → 378 全绿** · 指标：`usertests/_si_metrics.py`（含 refinement 段）

---

## 1. Stage × Source Family 规则

`scripts/sources.py` 新增 `STAGE_FIT`（每个 family × stage → `high` / `medium` / `low` / `never`），
`family_stage_fit()`、`applicabity_note()`，并让 `plan_queries()` **按适配度排序**：

```
high（主力） → medium（视情况） → low（优先级低，排在最后，被预算自然截断） → never（默认跳过）
```

| family | undergraduate | working | founder |
|---|---|---|---|
| `summer_research` | **high** | **low** | low |
| `research_seminar` / `research_institute` / `graduate_school` | medium | **high** | — |
| `academic_society` | medium | **high** | — |
| `working_group` / `maintainer_program` | medium | **high** | high |
| `contributor_guide` / `community_event` / `mentorship_program` | high | high | high |
| `official_exam_body` | high | high | — |

规划输出里每个 query 带 `stage_fit` / `family_selected` / `family_downweighted` / `family_skipped`，
可以回答"**是没搜到，还是 planner 判断不值得搜**"。

## 2. applicability 与 eligibility 的区别（硬规则）

| 概念 | 作用 | 取值范围 | 能否决定用户能不能参加 |
|---|---|---|---|
| **Source Family Applicability** | 决定**去哪找**、花多少预算 | high/medium/low/never | **不能** |
| **Eligibility** | 决定**用户能不能参加** | Eligible / Probably Eligible / Unknown / … | 能 |

- 有测试固定：`summer_research` 对在职者的 fit 是 `low`，但一个写明
  "working professionals accepted" 的真实项目**仍然判为可申请**（不会被 family 默认值过滤）。
- 因此 stage 只影响搜索优先级与预算，**绝不参与资格判定**。
- `never` 级也留了出口：官方明确接受该阶段时仍可命中（文案也这么写）。

## 3. source freshness / 陈旧页面判据

新增 `source_freshness()`，取值：`current` / `likely_current` / `stale` / `historical` / `unknown`。
判据（保守优先）：归档措辞 → 最后更新日期 → 标题/URL/摘要里的年份（最晚年份 < 今年 → historical；
= 今年 → likely_current；> 今年或出现"下次/次年/now open" → current）→ 无信号 → unknown。

**与 opportunity freshness 严格分开**（有测试）：

| | source_freshness | opportunity freshness |
|---|---|---|
| 回答 | 这个页面/公告是不是当前信息 | 这个机会现在是否开放 |
| 用法 | 页面能否作为"当前"证据 | 能否进主推荐 |

例：`Global Challenge 2027` 的页面是 **current**（当前信息），但机会本身是 **future** →
不进主推荐。反过来，`Summer Research Program 2024` 的页面在 2026 年是 **historical** →
可以 discovery，但**不能满足当前证据**。

## 4. 新 failure reason

`SOURCE_FAILURE_TYPES`（三分类不变，reason 细分）：

```
source_not_found            process
source_found_current        fact        ← 新增：找到了，且是当前信息
source_found_not_current    fact        ← 新增：找到的是历史/陈旧页面
source_found_no_opportunity fact
source_found_not_applicable fact        ← 新增：来源对当前阶段不适配
page_not_verifiable         infrastructure
js_rendered / blocked       infrastructure
```

`evidence.check()` 现在会在 `source_freshness ∈ {historical, stale}` 时返回
`missing: source_freshness:current(...)`，`demotion_reason()` 给出
`source_found_not_current`（fact）—— 历史页面**可以 discovery，不能满足当前证据**。

## 5. Case C Gap before / after

| 指标 | before（上一轮） | after（本轮） |
|---|---:|---:|
| `gaps_total` | 16 | 16 |
| `development_gaps` | 混算（含 logistics） | **14** |
| `logistics_prerequisites` | 混在 gap 里 | **2**（CNCF Slack 账号、GitHub 账号）已剥离 |
| `gap_noise_rate` | 0.125（隐性） | **0.125**（显式测量，且不再进分母） |
| `gap_coverage_rate` | 0.562（分母被灌大） | **0.643**（只对发展缺口计） |
| 幸存缺口性质 | 混有"Slack/GitHub" | **公开影响力 / ownership / 技术影响力 / 网络** |
| gate 结果 | recommended 4 | **recommended 4 / worth_verifying 1 / excluded 3**（0 处标注不一致） |

**诚实评价**：修复**真实但影响温和** —— 剥离的 2 条本来也不是"可被机会桥接的硬缺口"，
所以覆盖率只从 0.562 到 0.643。它真正的价值是让"发展缺口"这一列不再被手续项污染。

## 6. logistics 是否彻底退出 Gap 分母

**是。** `gaps.is_logistics()` 把手续类前置（Slack / Discord / GitHub profile / 表单 / 报名 /
费用 / CV / 成绩单 / 邮箱…）归入 `logistics_prerequisites` 字段：

- **不进入** `development gaps`、`gap_coverage_rate` 分母、Bridge 搜索
- **仍然进入** `readiness.missing_items`（有测试：缺 GitHub 账号会被算进准备度缺项）
- 有测试固定"缺 GitHub 账号不会触发 GitHub 学习项目/认证这类错误 Bridge"

## 7. stage-inapplicable queries 是否下降

| 场景 | `stage_inapplicable_query_rate` | `stage_family_precision` | 6 条 query 的 fit |
|---|---:|---:|---|
| working（研究缺口） | **0.00**（上一轮是 family 未排序，summer_research 会占据首位） | **1.00** | high×5, medium×1 |
| undergraduate | **0.00** | **1.00** | high×6 |

对照组（不做阶段排序、把 low 适配 family 放前面）低适配 query 数 > 0，证明排序确实起作用。
Case C 的真实运行同样 `stage_inapplicable_query_rate = 0`、`stage_family_precision = 1.0`。

## 8. source stale leakage 是否为 0

**是。**

- 合成检查：`Summer Research Program 2024` → historical；`Programme 2025` → historical；
  `Programme 2026` → likely_current → **leakage = 0**
- Case C 真实运行：2025 归档页被判 historical，按过期周期 **excluded**，
  未被当成当前机会；`source_found_not_current_rate` 记录为 0.125（1/8 候选触发了时效判据）

## 9. 是否出现新的 recall 回归

**没有**（`bridge_verified_rate` 0.857、`bridge_actionable_rate` 0.571 与上一轮一致；
`recommended_now` 仍为 4，无 job-board 退化）。

但本轮暴露一个**新的召回/相关性问题**（不是 regression，是新认知）：

- `gaps.py` 会从"用户目标 + 语义判断"推出 `research` / `network` 类缺口，
  但对**后端工程师想升 Senior** 这类目标，"研究经历 / 教授-实验室网络"**相关性偏低**。
  这不是 logistics 修复能解决的 —— 需要"缺口与用户方向的相关性判据"（下一轮候选）。
- `research_institute` 类来源命中陈旧 PDF 的风险已由本节第 3 条覆盖。

## 10. 下一步是否应该处理 IoT 67%

**应该，但排在下面这些之后，单独一轮处理**（本轮按要求保持 FAIL，未顺手改）：

`benchmarks/known_failures.json` 中 IoT `final_verification_pct = 67 < 80` 仍是**声明的失败**，
报告与 `gates.json` 都如实标注。建议顺序：

1. **Gap 相关性判据**（来自第 9 节的新发现）：避免为"升 Senior"这类目标推研究型缺口。
2. **预算收敛的 UX 假设**（按你要求**本轮不写死**）：`budget_unknown=true` + `resource_conflict=null`
   已经正确；"预算未知时最多给 3 条"记为 **UX hypothesis**，等真人测试确认再定规则。
3. **IoT 67%**：单独一轮，不动阈值、不与其他问题混合。

---

### 成功标准核对

| 目标 | 结果 |
|---|---|
| 更少把预算浪费在明显不适合当前阶段的来源 | ✅ 在职者 `stage_inapplicable_query_rate` 0.00，precision 1.00 |
| 更少把历史页面误认为当前机会 | ✅ stale leakage 0，历史页面只能 discovery |
| 没有因为这些约束错杀官方明确适合的用户 | ✅ applicability ≠ eligibility（有测试） |
| Gap 分母不再被手续项污染 | ✅ logistics 移出发展缺口，仍保留在 readiness |
