# 真人测试指标（Round 1）

> 定义在测试**之前**固定下来，避免事后找理由。

## A. 当场记录的三个行为指标

| 指标 | 定义 | 怎么取 |
|---|---|---|
| **Action Intent Rate** | 用户明确表示"准备采取行动"的机会数 / 展示数 | 当场对话（**这是意图，不是行动**） |
| **Observed Immediate Action Rate** | 用户**当场**真的做了动作的机会数 / 展示数 | 观察到：打开报名页 / 注册账号 / 收藏官方页 / 开始填表 / fork repo / 打开 issue / 加入活动 |
| **Familiarity Rate** | 推荐中用户**原本已经知道**的比例 | 主观问题 3 的反面（不是"没用"，是"已知道"） |

只记录**观察到的**行为。用户说"我会去看"算 Intent，不算 Immediate Action。

## B. Follow-up（3–7 天后，轻量）

| 指标 | 定义 |
|---|---|
| **Follow-up Action Rate** | 在 follow-up 确认"实际行动了"的机会数 / 当时表示有兴趣的机会数 |
| **Intent → Action 衰减** | 1 − Follow-up Action Rate（意图到行动的流失） |

Follow-up 只需一次轻量确认（消息即可），不做自动化。

## C. 主观指标

| 指标 | 定义 |
|---|---|
| **Surprise Rate** | 用户说"原来完全不知道"的机会数 / 展示数 |
| **False Positive Rate** | 用户说"明显不适合我"的机会数 / 展示数 |
| **Confirmed Miss Rate** | 用户提出"应该出现却缺失"的机会中，**经核实确实是真实漏召回**的比例 |
| **Repeat Intent** | 主观问题 6 回答"会"的比例 |
| **Time-to-action** | 从看到回答到说出/做出下一步的时间 |

### Confirmed Miss 的核实流程（不许直接把"用户说缺"算作 Miss）

对用户提到的每个"应该有"的机会，逐条核实并分类：

| 分类 | 含义 | 算不算 Miss |
|---|---|---|
| `query_miss` | 存在且相关，但查询没命中 | ✅ |
| `source_miss` | 存在且相关，但来源没覆盖 | ✅ |
| `ranking_miss` | 抽到了但排序太靠后被忽略 | ✅ |
| `verification_loss` | 存在但验证失败被降级 | ✅ |
| `profile_misunderstanding` | 系统理解错了用户 → 应记 Profile 缺陷 | ✅（记到 profile） |
| `out_of_scope` | 不属于 13 类机会范围 | ❌ |
| `not_a_real_miss` | 不真实存在 / 不适合该用户 / 用户已知 | ❌ |

## D. 第一阶段重点看的四个

```
Follow-up Action Rate      ← 真正有没有做
False Positive Rate        ← 推了不该推的
Surprise Rate              ← 有没有发现想不到的
Confirmed Miss Rate        ← 有没有漏掉重要的
```

## E. 系统侧指标（辅助定位，不替代真人观察）

`final_recommendation_verification_pct`（≥80%）、`expired_leakage`（0）、
`unverified_actionable_leakage`（0）、`gap_coverage_rate`、
`portfolio_resource_conflict_rate`（0）、`source_stale_leakage`（0）。

## F. 判读规则（先定好）

- Follow-up Action Rate 低而 Action Intent 高 → **意图到行动断裂**（readiness / 预算 / 门槛问题）
- False Positive Rate > 20% → 资格或相关性判据有问题（P0/P1 级）
- Surprise 高但 Follow-up 低 → 机会"有意思但不可执行"
- 用户说"太多了" → 记为 **UX 假设**，不要立刻写死规则（如"预算未知时最多 3 条"）

## G. 第一轮不做的事

不追求统计显著性；不边测边改（除非数据丢失 / 程序不可运行 / 严重隐私问题）；
不伪造任何 session；不用 LLM judge 替代真人行为。
