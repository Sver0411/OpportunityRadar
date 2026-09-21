# RC2 Final Validation Report（2026-09-21）

本轮 = Phase A（补齐真正独立的五 persona 验证）+ Phase B（只处理被独立复现的核心失败）。
测试 **496 → 510**，`preflight` 全绿，CI 全绿（`6a5ad6c`）。工件：
`usertests/rc2-validation/VALIDATION.json`、`/tmp/opportunity-radar-validation/{A..E}/`（五个独立会话的完整产物）。

---

## 1. 五 Persona 是否真正独立完成

**是，五个都完成了。** 每个都是一个独立 agent 会话，各自只写 `/tmp/opportunity-radar-validation/<L>/`，
并且明确禁止读取 `usertests/`、`benchmarks/` 或其它字母的目录：

| Persona | 候选 | 分区（recommended / worth / excluded） | conf |
|---|---:|---|---|
| A | 6 | 3 / 2 / 1 | medium |
| B | 3 | 1 / 2 / 0 | medium |
| C | 5 | **2** / 1 / 2 | medium |
| D | 5 | 3 / 2 / 0 | medium |
| E | 19 | **0** / 9 / 10 | low |

**必须披露的一点**：A 与 B 跑在默认模型上；随后派发 C 时平台返回 `429`（配额 15:21 重置），
我按提示**切换到备用模型**完成了 C/D/E。**独立性保证完全相同**（fresh context / profile / state / 候选池、
互不读取产物），但模型不同 —— 这一点必须写在结论旁边。

## 2. C 的 goal_fit bug 是否独立复现

**"0 个主推荐"这个结果没有复现**（C 这次有 2 条主推荐）。**但根因以更尖锐的形式复现了**：

C 这次找到的最有价值的一条是 **IETF 127**（对"升 Senior"最有 reputation / network / ownership 价值）：
`goal_fit = 15.0`（"不重合"地板），原始 match **54.7** —— **距 55 门槛只差 0.3**，
也就是说它能不能进主线**取决于四舍五入**。另外 **GDG organizer**（match 67、goal_fit 80、高于门槛 12 分）
因为抓取只拿到本地化首页而落在需确认 —— 那是核实问题，不是相关性问题。

**结论：bug 复现成立**，而且比上一轮的"0 条"更能说明问题：高价值条目在主线上是**碰运气**。

## 3. 若复现，如何最小修复（P1-1）

**根因（现有代码的真实缺陷）**：`score.goal_component` 的 outcome 分支遍历的是
`GOAL_TO_CATEGORY`，并把**类别名当 facet 名**去查 `outcomes`。目标 `career` 只映射类别 `career`
→ 只会读 `outcomes["career"]`；而治理席位 / 技术委员会声明的是 `reputation / network / management`
→ **那条腿对跨类别价值是结构性死代码**。

**修法（按你的要求，不加 category alias）**：

```text
User Goal → GOAL_OUTCOME_PROFILE（目标真正想要的 outcome facet + 权重）
          → opportunity.outcomes 命中的 facet
          → 归一化对齐度（分母 = 目标想要的全部权重，不是机会声明的那几个）
goal_fit  = max(类别腿, outcome腿, 15 地板)
```

- `GOAL_TO_CATEGORY` **一字未改**（`career` 仍只映射 `['career']`）。
- 归一化分母用"目标想要的全部"是**反例的守门人**：只声明一个泛 facet 的机会拿不到高分。
- 顺手修了一处同类问题：`goals` 是**字符串**时会静默退化成"没有目标"（→ 15 地板），现改为归一化。

## 4. C 修复前后

**真实批次（C 独立会话的候选）**：

| 条目 | 修复前 match / goal_fit | 修复后 match / goal_fit |
|---|---|---|
| **IETF 127**（升 Senior 最相关） | **55** / 15.0 | **58** / 34.69 |
| Toastmasters | 67 / 80.0 | 67 / 80.0（未变） |
| GDG organizer | 67 / 80.0 | 67 / 80.0（未变） |

**合成反例/正例（§6 要求的四条）**：

| 用例 | goal_fit |
|---|---|
| 正例 1：Senior + 技术委员会（reputation/network/management 高） | 15 → **46.9** |
| 正例 2：Senior + maintainer 路径（公开声誉/ownership） | 15 → **46.9**，并进入 `recommended_now` |
| 反例 1：Senior + 随机 beginner good-first-issue | **15.3**（贴近地板） |
| 反例 2：Career 目标 + 普通娱乐 event | **15.0**（不重合） |
| 回归：纯 career 类别的机会 | **100**（未变） |
| 回归 D：vLLM 生产平台贡献 | ≥60（未被压到地板） |
| 回归 B：研究型机会 vs 无关社区活动 | 高 vs <30（无关项没被抬上来） |

## 5. D Golden 五项

| # | 标准 | 结果 |
|---|---|---|
| 1 | 利用已有后端 career capital | ❌ **未通过**：卡片文本从未出现"5 年/后端"，`skill_fit = 0.0`（硬性技能覆盖 0/3） |
| 2 | 拒绝实习降级路线 | ✅ 主推荐区 0 实习；OSPP（"在校学生"限定）落需确认；LFX 被丢弃 |
| 3 | 识别 AI production / platform bridge | ✅ vLLM（推理/调度/服务/性能，合入主线 PR）+ Airflow（数据管道编排生产经验）；全场 0 门课程 |
| 4 | 6h 资源约束 | ✅（**本轮修好**）此前渲染出"合计约 0.0h/周，与你给出的每周可用时间对齐"，且把"2-6 个月"当成 6 小时/周 —— 已改为：小时未知时**不给总计**，且只认显式小时单位 |
| 5 | 单一 external mainline | ❌ **未通过**：主线槽位给了 `KubeCon CFP`（因为按 urgency 排到首位），vLLM / Airflow 被标为辅线 |

**结论：D = 4/5，不冻结为 Golden Scenario。** 剩下两项（1 与 5）都是**展示/编排层**问题、
不是本轮 Phase B 的范围，已列入下一步。

## 6. B Golden 状态

**通过 —— 可作为 Gap→Bridge Golden Scenario**（独立会话自然产生，不依赖固定网站）：

```text
research gap（用户自述"科研经历比较少"）
  → OIST Research Internship 2027 春（官方核验：截止 2026-10-15，verified_official，证据完整）
  → 可验证研究证据（实验室经历 + 教授推荐信 + 研究陈述素材）
  → 支撑日本 CS 修士申请
```

- 3/3 张卡片可见缺口链；`visible_gap_bridge_rate = 1.0`。
- 自建替代路径（本校找教授做 RA / 自做小项目）**单独成段**，未混入推荐。
- 资格边界守住：用户未声明学历/日语等级时只写"无法判断"，没有替用户假设。
- 未能核实：OIST"当前开放"是由未来截止日推断；JLPT 2027-07 报名未公布；Keio 仅有第三方来源。

## 7. E Explore 状态

**未通过，不冻结为 Explore Golden Scenario。** 自然运行（按 `locales.py --mode C` 自身权重 +
taxonomy 模板构造 query，不人为偏向非技术）：

- 19 个候选 → **主推荐 0** / 需确认 9（展示 5）/ 排除 10；`decision_confidence = low`。
- **呈现集只产生 1 条轴**（`community`，via category）→ 不满足 ≥3。
- 技术占比 **0.421**（按主题；全 19 条）。
- **主导偏差 = 类别分配偏差**：Mode C 把 `open_source/project` 各 0.15，加
  `skill_development/competition/research`，共 **0.615 权重落在工具自己标为技术类的类别上**；
  而唯一使用非技术词汇的那条 query 得到 5/5 非技术候选。**不是排序偏差**（9 条 survivor 全是中性 `match=60`）。
- **主推荐 0 的直接触发是 `verification_status`**（9/9 `evidence_complete=false`），属来源/核实层，
  不是画像造成的（画像的真实后果是 `eligibility_known = 0/19`）。

→ 按你的 §9：**先定位，不扩 taxonomy**。下一步该做的是 Explore-specific query diversification
（最小可验证改动），而不是加类别。

## 8. age blocked count

**本轮 = 0。** 五个独立会话里**没有任何候选是"仅因无法表达年龄而长期 Unknown"**：
- E 的 19 条主推荐为 0，触发项是 `verification_status`（9/9 证据不完整）；
- A/B/C/D 的 Unknown 主要来自**语言 / 国籍 / 学历**未声明；
- 唯一明确引用年龄门槛的是 **UNV（18+）**，而它不在本轮 E 的候选池里（来自上一轮）。

→ 按 §8：**暂缓 schema 扩展**，不因为一个 18+ 项目就动 profile schema。

## 9. 剩余 P1

| ID | 状态 | 说明 |
|---|---|---|
| P1-1 goal_fit 跨类别 | **已修（本轮）** | Goal×Outcome Facets；IETF 55→58 |
| P1-2 语言/国籍/学历未声明 → 主线措辞重复 | **不修（按 §7）** | Missing ≠ Not Qualified 且 Missing ≠ Eligible 都对；未来应问一个**高价值澄清问题**，而不是放松资格门槛 |
| P1-3 schema 无 age 字段 | **暂缓（按 §8）** | 本轮 age 阻塞 = 0 |
| P1-4 轴指标不可信 | **工具已修（本轮）** | 精确 token/短语匹配 + 每条轴带理由 + 补齐 film/poetry/art/design/writing + 歧义类别不再自动授予轴；剩余：轴覆盖仍不由系统保证 |
| P1-5 taxonomy 缺 volunteer/creative/cross_domain 入口 | **不修（按 §9）** | 根因已定位为类别分配偏差 |
| P1-6 空画像措辞重复（裸枚举 "Unknown"） | 部分改善 | community 组已对齐 §6 的三标签；career/hobby 这类不在四组内的类别仍会退化成裸枚举 → **新增 P1-9** |
| **P1-7（D 暴露）** | 新 | 主线槽位按 urgency 排到首位 → "主线 ≈ 最近的截止"，而不是用户最该主攻的方向 |
| **P1-8（D 暴露）** | 部分已修 | `goals` 为字符串曾让 match 全线下挫 10–15 分（已归一化）；但"画像字段形状不合法就静默降级"值得系统性排查 |
| **P1-9（E 暴露）** | 新 | 不在 4 个参与 family 内的类别 → 参与措辞退化为裸枚举 |
| **P1-10（D 暴露）** | 新 | 卡片不体现"已有职业资本"（`skill_fit=0.0` 时也不解释为什么） |

## 10. 是否满足 rc2 条件

**零容忍项全部满足**（`usertests/rc2-validation/VALIDATION.json`）：

```text
persona_context_leakage_count        = 0
unsupported_precision_count          = 0
strong_claim_with_low_confidence     = 0
expired_leakage                      = 0
unverified_actionable_leakage        = 0
source_stale_leakage                 = 0
self_directed_mixed_count            = 0
```

**但 §15 的实质条件有两条不满足**：

- **C：已达标** —— 高价值 + actionable 的机会不再因为 category goal_fit 缺陷掉出主线（55 → 58）。
- **D：未达标** —— Golden 五项只过 4 项（第 1、5 项）。
- **B：已达标** —— Gap→Bridge 模式独立成立。
- **E：未达标** —— 0 条主推荐、呈现集仅 1 条轴。

## 11. 是否已打 `v3.0.0-rc2`

**没有打，也不建议现在打。** 本轮所有 tag 操作均未执行。

**建议的下一步（按优先级，都是最小改动）**：
1. **D 的第 5 项**：主线槽位不再等同于"按 urgency 排第一"，而是与目标最相关的那条（纯展示层）。
2. **D 的第 1 项 / P1-10**：卡片显式体现"你已经有的职业资本"（`skill_fit=0` 时给出解释而不是沉默）。
3. **E 的 Explore query diversification**：针对类别分配偏差做最小改动，然后**只重跑 D 与 E 两个会话**即可判定。
4. 以上完成后重跑一次五会话，若零容忍项仍全 0 且 D/E 通过，再打 `v3.0.0-rc2`。

**流程护栏（§16）已加**：`python3 scripts/preflight.py`（compile → 全部单测 → skill 包校验，
任一步失败退出非 0），并写进 SKILL.md 索引。本轮所有提交都先跑它。
