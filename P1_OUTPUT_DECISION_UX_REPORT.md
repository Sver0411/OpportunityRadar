# P1 Output & Decision UX 报告（2026-09-21）

**本轮范围**：只做输出与决策表达层，**V3 Core 保持 Frozen** —— 未改 Match/Utility 权重、
Evidence gate、Freshness、Source registry、Gap relevance、Bridge 评分、Portfolio 分配器、
taxonomy、profile schema。唯一新增文件是 `scripts/presentation.py`（纯表达层，不做判断）。
测试 **396 → 482**。附录证据：`usertests/output-ux/`（含 `REGISTRY.md` 五 persona 渲染结果）。

---

## 1. Decision Confidence

`presentation.decision_confidence(profile, rows, gaps)` → `high / medium / low`，**不参与排序**
（返回里没有 score/match 字段，有测试固定）。信号：`goal_clarity`、`profile_completeness`、
`time_budget_known`、`financial_budget_known`、`location_known`、`eligibility_known`、
`evidence_completeness`。关键约束（goal / 时间预算 / 地区）任一未知即**不允许 high**。

| 档位 | 允许的说法 | 禁止的说法 |
|---|---|---|
| high | 「你的主线可以优先放在…」 | 绝对 / 保证 / 唯一正确路线 |
| medium | 「从目前信息看…更值得先验证」 | 最优 / 最佳 / 你现在必须 / 唯一正确路线 |
| low | 「目前值得试的几种方向」「如果你更在意 X → A」 | 以上全部 + 建议你放弃 / 你应该选择 |

五个 persona 的实际档位：**A low**（目标与资源都未知）、**B medium**、**C medium**、
**D medium**、**E low** —— 与各自缺失的信号一致，不是拍脑袋。

## 2. Output Adapter

`scripts/presentation.py`：`decision_confidence` → 语气；`participation_wording` → 参与措辞；
`recommendation_card` → 卡片；`render_answer` → 回答骨架（含长度控制与自检）；
`output_metrics` → 本轮 8 个指标。卡片最多 5 个用户可读字段
（为什么适合你 / 补什么缺口 / 投入 / 能留下什么 / 下一步价值）+ `还需要确认`，
字段缺就少写，**不机械模板化**（`present_fields` 记录实际有几个字段）。

**资源精度防护**按**依据**判定，而不是一律禁止：

| 写法 | 依据全无 | 只有 weekly_time | 两者都有 |
|---|---|---|---|
| `60% / 25% / 15%` | ❌ 拦 | ❌ 拦 | ✅ 允许 |
| `每天 1.5 小时` | ❌ 拦 | ✅ 允许 | ✅ 允许 |
| `3h + 1h + 1h = 5h` | ❌ 拦 | ✅ 允许（Case C/D 那类） | ✅ 允许 |

预算未知时输出 `主线 / 辅线 / 低成本试错` + 「你的可用时间还未知，所以暂不做具体比例分配。」

**实测中发现并修掉的 4 个真缺陷**（都是看真实渲染结果发现的，不是想象出来的）：

1. **内部推理泄漏进用户字段**：`为什么现在值得看` 里曾出现
   `页面限定学历 ['undergraduate','master']，画像未提供学历 → 无法判断`。
   改为：只写用户真的表达过的匹配理由；判断不了的项移到 `还需要确认`，并加 `humanize_reason()`
   去掉 Python 列表语法与内部术语（结构化原文另存 `needs_confirmation_details`）。
2. **凭空断言匹配**：给 E（什么都没说）写了「地点/远程方式与你的偏好相符」「与你的目标直接相关」。
   改为：只有画像里**真的存在**该偏好（`interests` / `skills` / `goals` / 地区字段）时才允许引用，
   否则退化为「与你已说明的情况有交集」。
3. **未核实却给肯定说法**：官方页自相矛盾的 IGIIDeation 被写成 `Registration open`。
   改为：`verification_status ∈ {unverified, conflicting, expired}` 一律降为待确认说法。
4. **`effort` 是字符串时崩溃**：真实存档记录里 `effort` 既有 dict 也有字符串 → 适配层 AttributeError。
   已兼容，非小时数写法改为「self-paced（官方未给出小时数）」。
   另修一个指标误报：占位文案「官方页未写明投入强度」被算成"可见投入"。

## 3. Explore Diversity

`explore_focus()` 只在 `career_direction == explore` 时启用（有明确目标时完全关闭，有测试）。
维度是**与 category 正交的表达轴**（`build / contribute / research / volunteer / community /
creative / entrepreneurship / cross_domain`），**不是新 taxonomy**：`AXIS_BY_CATEGORY` 只引用
已有的 13 个 category，模块不新建类别枚举（有测试）。

`explore_coverage()` **达标才出现**：只列出真的命中了的维度，缺的写进 `missing_axes`，
不为凑数塞弱结果。`technical_share()` 报技术类占比，用于盯「技术类占满主推荐」。

## 4. Category-aware Participation Wording

底层 `eligibility_verdict` 一字未改，只换说法（有测试断言 `verdict` 被原样保留）：

| 类型 | 措辞 |
|---|---|
| 开源类 | Open participation / Contribution prerequisites / Restricted / Unknown |
| 赛事类 | Registration open / Eligibility needs confirmation / Not currently open |
| 社群类 | Open to join / Prerequisites apply / Invitation or selection required |
| 求职·奖学金·升学 | 保留 Eligible / Probably Eligible / Unknown / Probably Ineligible / Ineligible |

周期已结束 → 一律 `Not currently open`（覆盖任何资格结论）。

## 5. Self-directed Fallback 分离

`self_directed_fallback()` 产出 `kind: "self_directed"`、`not_an_opportunity: true`、**没有 zone**；
`split_recommendations()` 把真实机会与自建路径分开，并报告 `mixed` 标志；
`render_answer()` 把它们放进独立的 `self_directed` 段。即使被误标成 `recommended_now`，
`mixed` 也会被抓出来（有测试）。指标 `self_directed_mixed_with_real_opportunity_count = 0`。

## 6. 五个 Persona Before / After

**先说方法的诚实交代**：本轮原计划派 5 个独立子代理会话，但**子代理配额被限流**
（需等到 02:56 重置），因此实际做法是：

- **A / B**：由本会话真实联网新跑（A 用 2 搜 3 抓；B 用 2 搜 2 抓），真实候选、真实官方页核验。
- **C / E**：使用各自**已存档的真实候选**（真实验证过），**重新跑真实 gate** + 新输出层
  —— 正好隔离出本轮要测的东西：同一批输入、换表达层。C 复算出 4 条 recommended、E 复算出 2 条，
  与当初记录一致。
- **D**：本轮 D 的 prompt（5 年后端转 AI）**没有存档会话**；最接近的真实 baseline 是
  `case-b-professional`（3 年嵌入式转 Edge AI，6h/周）。该记录没有 evidence 块，
  因此对它做**表达层对照**（沿用记录里已判定的 zone），**不假装重跑过 gate**。此差异如实记录。

| Case | 分区 | confidence | 主推荐 | 资源分配 | 自检违规 |
|---|---|---|---|---|---|
| A 物联网大三 | 1 / 4 / 1 | **low** | 开源之夏 | 定性（无预算） | 0 |
| B 日本修士 | 2 / 1 / 1 | medium | OIST 实习 + 東大研究生 | 定性（无预算） | 0 |
| C 升 Senior | 4 / 1 / 3 | medium | 4 条（含 CNCF TAG 等） | 记录里无预算 → 定性 | 0 |
| D 转 AI（表达层对照） | 沿用记录 | medium | 4 条 | 6h 已知 → 可量化 | 0 |
| E 无明确目标 | 2 / 7 / 0 | **low** | CyLab + OWASP | 定性（无预算） | 0 |

**B 是本轮最有代表性的一例**（用户点名要求突出 OIST）：主推荐 2 条，两条都带完整缺口链 ——

```
### OIST Research Internship — Spring 2027 round
- 为什么现在值得看：地点/远程方式与你的偏好相符；与你的目标直接相关
- 补的缺口：你现在缺 **教授 / 实验室联系人** → 这条机会能补它
- 投入：每周约 40 h
- 能留下什么：真实实验室研究经历、教授推荐信潜力、研究实习结业记录
- 下一步价值：官方定位就是为后续申请研究型学位积累研究经历
- 参与方式：Unknown
- 建议动作：值得进一步核实（可参与且证据完整，但你的时间预算还没给出）
- 还需要确认：页面限定学历 undergraduate, master, graduate，你的资料未提供学历，无法判断；…
```
（官方核验：Spring 2027 轮申请 **2026-10-15 23:59 JST** 截止；资格为本科最后两年 / 硕士任何年级 /
已毕业者；在读需本校同意。 **没有**把「明年申请」写成「现在就能申」）

**before 的实际情况，必须说清楚**：我把 C/D/E/B 四处旧 transcript 扫了一遍 ——
**旧回答里没有出现百分比、每天小时数、最优/最佳、你现在必须/唯一正确路线**
（全部 0 命中）。也就是说，本轮**不是**在修一个已经被污染的 before；本轮的价值是：

> 把过去靠会话散文纪律守住的东西，变成**可执行、可测试的契约**（482 测试里有 20+ 条专门盯这些），
> 并在把契约应用到真实渲染结果时，抓出了上面第 2 节那 4 个真缺陷。

## 7. 是否出现 Context Leakage

**0 处**（`persona_context_leakage_count = 0`）。检查方式：对背景字段（skills / interests /
education / experience / languages / nationality / life_stage / constraints）逐值比对，
出现用户原话里没有的内容即报警；跨语言关键词同时匹配（画像存 `working`，用户原话是「工作三年」）。
只看**背景字段**，不查 goals / career_stage 等派生枚举（否则 `goals[].type = "research"` 会误报）。

**本轮真的抓到过一处泄漏并已修**：E 的存档画像里带着**用户从未提过的技术背景**
（`skills` / `education` / `interests` / `goals` / `constraints` 全都有值）——
正是 §9 禁止的「假设技术背景」。已按要求重建为**只含用户原话**的画像，旧画像另存
`case-e-unknown/profile-previous.json` 供对照。A 的画像里有 1 个 `inferred_pending` 推断值
（由专业推断 embedded），已标注为「可驱动搜索，不参与资格判定」。

## 8. 是否还有 Unsupported Precision

**没有**：`unsupported_precision_count = 0`、`strong_claim_with_low_confidence_count = 0`，
五份回答的 `violations` 全为空。但必须指出两个**真实的低分项**（不粉饰）：

| 指标 | 值 | 说明 |
|---|---|---|
| `visible_gap_bridge_rate` | **0.08** | 只有 B 的卡片能看到缺口链（2/3）。**A 为 0 是既冻结规则的直接后果**：A 没有声明目标 → `career_direction = explore` → 所有缺口都被判成 `contextual_gap` → 不做 Bridge 搜索。**C/D/E 为 0 是数据问题**：存档记录从未捕获机会侧 `skills_required`，缺口模型没有原料。 |
| `visible_evidence_output_rate` | **0.28** | 同理：C/D/E 的存档记录没有 `produces`，卡片只能如实写「官方页未写明可留下的产出」。A/B 的记录完整，该字段基本都填上了。 |
| `visible_effort_rate` | 0.68 | 其中 D 是表达层对照（沿用旧记录）。 |

**已据此补上提取要求**（`references/extraction-policy.md` + `SKILL.md`）：
官方页写了就必须捕获 `produces` / `effort` / `skills_required` —— 否则新卡片契约拿不到输入。
这是本轮唯一的"改输入侧"，属于输出契约的依赖，不涉及判断逻辑。

## 9. E 的 Exploration Axis 数量

**4 类**：`build / community / contribute / research`（要求 ≥3，达标）。
E 的画像已被清空到只有用户原话，因此卡片语气是「值得拿来试方向」、资源分配是定性、
`decision_confidence = low`。

**但技术占比 = 1.0（7/7）**，违反 §9「技术类不能因为系统自身偏好占满全部主推荐」。
根因是**候选池来源**：E 的候选来自上一轮那个「3 年级 CS 学生、安全方向」的 fixture 会话，
天然偏技术；`technical_share()` 把这个事实报出来了（指标起作用了，但数据没救）。
要真正验证 E，需要一次**全新空画像的 discovery**（受配额限制本轮没能做）——
这属于下一轮的事，不算通过。

## 10. 是否建议继续改核心

**不建议。** 本轮证据：

- 表达层能独立解决的东西（语气强度、伪精确、参与措辞、缺口链可见、自指导分离、内部术语泄漏）
  都已经做完并锁进测试；剩下 3 个低分项**都不是表达层能修的**：
  1. **A 没有发展缺口** ← 需要动 `career_direction` 的判据（有目标 vs 路线未定之分）→ **核心逻辑**。
  2. **C/D/E 缺口链不可见** ← 需要机会侧 `skills_required` 被捕获（已在提取要求里补），
     以及**真实重跑**这些 case 才有意义 → 数据，不是规则。
  3. **E 候选人全是技术类** ← 需要**空画像重新 discovery** → 数据，不是规则。
- 建议的下一步顺序（都不动核心）：① 用当前空画像对 E 做一次真实 discovery，
  看 `technical_share` 是否真的能降到 1.0 以下；② 按新的提取要求重跑 C（记录 `skills_required`），
  看 `visible_gap_bridge_rate` 是否上升；③ 子代理配额恢复后补做 **5 个独立会话**的版本，
  替换本轮的「A/B 新跑 + C/D/E 存档复用」组合。

**成功标准的自评**：用户不需要知道 Gap / Bridge / Utility 这些词 ——
B 的回答能让用户读懂「为什么推荐（与目标相关）、要投入什么（40h/周 或 未写明）、
能得到什么（研究经历/推荐信/结业记录）、它会把我带向哪里（研究型学位）、
以及哪些还不能确定（学历要求、学校同意、时间预算）」；A/E 的回答在信息不足时
只给方向与对照、并明说「暂不做比例分配」。**这一条达标**；
缺口链的普遍可见性**尚未达标**，原因与后续动作见上。
