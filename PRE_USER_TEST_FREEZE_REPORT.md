# Pre-User-Test Freeze Report

日期：2026-09-20 · 类型：Hygiene Patch（不新增任何核心能力）· 测试：**386 → 396 全绿** · CI 3.8 / 3.12 通过

---

## 1. 一致性问题是否修复

| # | 问题 | 状态 |
|---|---|---|
| 1 | **Local state 契约不一致**：`sources.json` 已实现但文档未列出 | ✅ 修。`common.STATE_FILES` 成为唯一事实来源（6 个文件），SKILL.md 与 `references/state-and-feedback.md` 同步列出；`sources.json` 只允许 8 个字段（source / category / region / runs / last_checked / last_success / historical_yield / failure_type），并在两处文档明确**禁止**保存页面正文、搜索结果全文、个人信息、凭据；新增 4 条测试（文档一致性、字段白名单、yield 落盘字段实测、state 目录名单一来源） |
| 2 | **benchmark 历史 vs 当前语义混淆**（`active_failures = 0` 却 `all_pass = false`） | ✅ 修。拆成两层：`_metrics-stabilization.json` 里新增 `historical`（round-2 快照 67%、`historical_all_pass = false`）与 `current`（`active_failures = 0`、`current_all_pass = true`）；`gates.json` 的 67% **原样保留**、只多 `status: resolved` 标记；新增 3 条测试（active 为空 ⇔ current_all_pass 为真、历史快照不得改写、resolved 条目保留全部历史字段） |
| 3 | **Action Rate 定义错误**（把"我会做"当成行动） | ✅ 改名并拆分：`Action Intent Rate`（意图）+ `Observed Immediate Action Rate`（当场观察到的动作：打开报名页 / 注册 / 收藏官方页 / 开始填表 / fork repo / 打开 issue / 加入活动） |
| 4 | 缺少真正的 follow-up | ✅ 新增 `Follow-up Action Rate`（3–7 天后确认实际采取行动 / 当时表示有兴趣）与 `Intent → Action 衰减`；SESSION_TEMPLATE 增加 follow-up 段与表格 |
| 5 | **Miss Rate 定义错误**（"早就知道"不是漏召回） | ✅ 改为 `Familiarity Rate`（原本已知道的比例）；真正的 `Confirmed Miss Rate` 来自主观问题"应该出现却没出现"，并附 7 类核实分类（query_miss / source_miss / ranking_miss / verification_loss / profile_misunderstanding / out_of_scope / not_a_real_miss，只有前五类才算） |
| 6 | 指标清单 | ✅ 调整为 9 项，重点四项：**Follow-up Action Rate / False Positive Rate / Surprise Rate / Confirmed Miss Rate** |
| 7 | **SI provenance 被污染**（stage 变体 query 强挂 `ordered[0]`） | ✅ 修。新增 `_family_for_query()`：一条 query 只有真的含某 family 的领域词才挂该 family，否则 `family=None`（mixed）；测试会校验"有 family 的 query 必须匹配该 family 的领域词"（该测试当场抓出 `research internship / visiting student` 未登记 marker 的真实缺口） |
| 8 | **硬编码年份** | ✅ 修。`CURRENT_MARKERS` 移除写死的 `2027`，"下一自然年"判断改为 `today.year + 1` 动态完成；新增测试禁止 marker 里出现任何 4 位年份 |

**附带**：`usertests/real/METRICS.md` 重写、`SESSION_TEMPLATE.md` 增加 Intent / Immediate / Follow-up 与 Miss 核实表、`README.md` 增加 follow-up 步骤与"不边测边改"硬要求。

## 2. 当前测试数

**396 个 unit tests，全部通过**（其中本轮新增 10 个契约类测试）。

## 3. active FAIL 是否仍为 0

**是。** `benchmarks/known_failures.json` 的 `known_failures` 为空数组；已解决的 IoT 67% 保留在
`resolved_failures` 中（含 old_value / new_value / threshold / root_cause / fix / 失败分类）。

## 4. current_all_pass 是否机器可读

**是。** `benchmarks/_metrics-stabilization.json`：

```json
"current":   {"active_failures": 0, "current_all_pass": true, "checked_at": "2026-09-20"}
"historical":{"snapshot": "round-2 gates.json", "iot_final_verification_pct": 67,
              "historical_all_pass": false}
```

并有测试保证 `active_failures == 0 ⇔ current_all_pass == true`，且历史 67% 不被改写。

**快速 regression 四项泄漏全 0**：expired leakage 0 / unverified actionable leakage 0 /
source stale leakage 0 / portfolio resource conflict 0。主推荐核验率：IoT 100%、Case B 100%。

## 5. 真人测试指标最终定义

| 类别 | 指标 | 定义 |
|---|---|---|
| 当场 | **Action Intent Rate** | 表示"准备行动"的机会 / 展示数 |
| 当场 | **Observed Immediate Action Rate** | **当场观察到动作**的机会 / 展示数 |
| 当场 | **Familiarity Rate** | 用户原本已知道的比例 |
| 主观 | **Surprise Rate** | "原来完全不知道" / 展示数 |
| 主观 | **False Positive Rate** | "明显不适合我" / 展示数 |
| 主观 | **Confirmed Miss Rate** | 经核实确为真实漏召回 / 用户提出的缺失项 |
| 主观 | **Repeat Intent** | 问题 6 回答"会"的比例 |
| 主观 | **Time-to-action** | 从看到到说出/做出下一步的时间 |
| Follow-up | **Follow-up Action Rate** | 3–7 天后确认实际行动 / 当时有兴趣 |

**重点四项**：Follow-up Action Rate、False Positive Rate、Surprise Rate、Confirmed Miss Rate。
判读规则与 Miss 七分类核实流程见 `usertests/real/METRICS.md`（事先固定，避免事后找理由）。

## 6. 是否已经正式冻结 V3 Core

**是。** `DEVELOPMENT.md` 顶部已加标记：

```
V3 Core Status: Frozen for Real User Testing   （冻结于 2026-09-20）
```

含义：真人测试前**不再因为开发者自己的想象添加规则**；此后只有
`真实用户失败 → 复现 → 定位 → 最小修复 → 回归测试` 这一条路径可以改核心逻辑。
冻结期间禁止新增：Watch / Delta Scan、Application Lifecycle、更多 locale、更多 source family、
新 taxonomy / ranking / profile 字段、ML / 向量库 / crawler / UI。

## 7. 第一轮 5 人测试现在是否可以直接开始

**可以直接开始。** 招募对象与顺序：

| 用户 | 类别 |
|---|---|
| U1 | A 大学生 |
| U2 | B 研究生 / 准备升学 |
| U3 | C Early Career |
| U4 | D Mid Career / 转行 |
| U5 | E 没有明确目标 |

执行纪律（已写进 `usertests/real/README.md`）：

1. **不边测边改**：U1→U5 全部结束、汇总完 `SUMMARY_ROUND1.md` 之后才动代码；
   只有出现数据丢失 / 程序完全无法运行 / 严重隐私问题才中止修复。
2. 每人一次 session（30–40 分钟）+ 一次 3–7 天后的轻量 follow-up。
3. 记录只用代号，session 存 `usertests/real/sessions/`（已 gitignore）。
4. 不伪造任何数据，负面反馈原样保留。

**下一步不是写代码，是找 5 个真人来用。**
