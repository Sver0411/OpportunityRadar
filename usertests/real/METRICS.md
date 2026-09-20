# 真人测试指标

## 行为指标（主）

| 指标 | 定义 | 怎么取 |
|---|---|---|
| **Click Rate** | 点开的机会数 / 展示数 | session 记录 |
| **Save Rate** | 收藏（saved）数 / 展示数 | session 记录 + `.opportunity-radar/` |
| **Action Rate** | 用户明确表示"会去做"的机会数 / 展示数 | 最重要的指标 |
| **False Positive Rate** | 用户说"明显不适合我"的机会数 / 展示数 | 主观问题 4 |
| **Surprise Rate** | 用户说"原来不知道"的机会数 / 展示数 | 主观问题 3 |
| **Repeat Intent** | 主观问题 6 为"会"的比例 | 主观问题 6 |
| **Time-to-action** | 从看到回答到说出下一步的时间 | 观察 |
| **Miss Rate** | 用户主动提到"这个我早就在做/知道"的比例 | 主观问题 3 的反面 |

优先看三个：**Action Rate / Surprise Rate / False Positive Rate**。

## 系统侧指标（辅助，用于定位问题）

| 指标 | 说明 |
|---|---|
| `final_recommendation_verification_pct` | 主推荐里官方核实占比（≥80%） |
| `expired_leakage` / `unverified_actionable_leakage` | 必须为 0 |
| `gap_coverage_rate` | 发展缺口里有 Bridge 的比例 |
| `portfolio_resource_conflict_rate` | 必须为 0 |
| `source_stale_leakage` | 历史页面被当成当前机会的数量（必须 0） |

## 判读规则（先定好，避免事后找理由）

- Action Rate 低于 20% → 优先怀疑"推荐与用户真实处境脱节"，而不是文案问题
- Surprise Rate 高但 Action Rate 低 → 机会"有意思但不可执行"（readiness / 预算问题）
- False Positive Rate 高于 20% → 资格或相关性判据有问题
- 用户说"太多了" → 记录为 UX 假设（**不要立刻写死规则**，如"预算未知时最多 3 条"）

## 汇总

第一轮结束后写 `usertests/real/SUMMARY.md`：每类用户的三个主指标 + 原话引用 + 系统侧指标 + 明确列出的失败。
**不得用 LLM judge 的评分替代真人行为。**
