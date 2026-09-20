# V3 Validation Closure Report（2026-09-21）

**本轮不是开发轮**：`career_direction`、Gap relevance、Bridge scoring、Utility、Match、Portfolio
allocator、source family registry、taxonomy、profile schema、freshness、evidence gate **全部未改**
（§16）。除 §12 说明的两处定位性修正外，只做验证与定位。测试 482 → **485**，CI 全绿。

工件：`usertests/output-ux/`（每 case 的 profile / opportunities / scored / gaps / bridges /
portfolio / answer / validation_report）、`usertests/output-ux/VALIDATION_UNIFIED.json`、
`usertests/output-ux/REGISTRY.md`。

---

## 0. 先说方法限制（读完再看结论）

**§7/§8 要求的「五个 persona 全部独立 session」本轮没做到。** 子代理派发被平台配额限流
（`429 使用量已超出频率限制，将在 02:56 重置`）；我在本轮开始与验证中各试一次，两次都被拒。实际：

| Persona | 实际怎么跑的 | 独立会话？ |
|---|---|---|
| A | 上一轮在本会话内真实联网跑（4 搜 3 抓） | ❌ |
| B | 上一轮在本会话内真实联网跑（2 搜 2 抓） | ❌ |
| **C** | **本轮按新 prompt 重跑**：新建画像（无 Singapore/后端/Python）+ 新候选 + 2 搜 2 抓 | ❌（独立画像，非独立会话） |
| D | **表达层对照**：沿用 `case-b-professional` 已判定的 zone，未重跑 gate | ❌ |
| **E** | **本轮空画像 discovery**：全新画像/候选 + 4 搜 4 抓，旧批次另存 `opportunities-archived-batch.json` | ❌（同上） |

机械独立性做到了（独立 profile / opportunities / state 目录），但 **"fresh conversation context"
没有满足** —— 本轮结论不享受独立会话的抗污染保证。这是本轮最大的未完成项。

---

## 1. E 空画像真实 Discovery 结果

输入只有那一句（生活/在读/技能/目标/预算全空）。画像全空 → `locales.py` 回落 `remote` + 英文；
无 gap → **完全不用 source family**，4 条 query 全是 `general_search`（volunteer / creative /
entrepreneurship / community 四方向）。真实检索 4 次、官方页抓取 4 次。7 个真实候选，
真实 gate：**推荐 3 / 需确认 4 / 排除 0**，`decision_confidence = low`。

| 主推荐 | 参与措辞 | 投入 | 本轮官方核验 |
|---|---|---|---|
| UN Online Volunteering（UNV） | Prerequisites apply | 每次任务 ≤20h/周、≤12 周 | 官方页：18+、**无背景要求**、持续发布任务、**无报酬** |
| MentorsHub Mentorship 2027 | Prerequisites apply | 每月约 1h | 官方页：申请开放、**10/31 截止**、约 21–30 岁、有 commitment fee |
| Weimar Poetry Film Award 2027 | Unknown | 未写明 | 官方页：**任何国家任何年龄**、12/31 早鸟 / 2/28 常规 |

**关键结论**：空画像**不是**必然拿不到主推荐 —— Weimar 官方页写明"any nation and of any age"、
零资格限制，因此能判可参与。而三条主推荐的参与措辞都停留在待确认档，原因是画像没有语言/国籍
（UNV 平台级 18+、Weimar 材料需德/英、MentorsHub 有国籍与年龄阶段门槛），按「缺失 ≠ 不满足」
只能 Unknown —— **行为保守且正确，但信息量低**。

**与上一轮的差异**：上一轮 E 的候选来自一个"3 年级 CS、安全方向"的 fixture 会话（技术池），
`technical_share = 1.0`。本轮空画像 + 无个性化 query 找到的是**非技术供给** → 上一轮的技术垄断
**来自候选池来源，不是当前系统偏置**。

## 2. E 的 technical_share 与 Explore axes

- `technical_share = 0.0`（0/7；判定给理由：关键词 + 是否声明技术技能，而不是"类别是 competition 就算技术"）
- 原始 `explore_axis_count = 5`（`build, community, contribute, entrepreneurship, volunteer`）
- **原始计数不可信**。人工核对后真实轴是 **4 类**：`volunteer`(UNV/Outreach360)、`community`(UNV/MentorsHub/Outreach360)、`creative`(Weimar)、`entrepreneurship`(Hult/venture.ch/Baylor)

**指标本身两个缺陷（只定位，未修）**：

1. `creative` 词表太窄（只有 content/design/writing/podcast/video，**没有 film/poetry/art**）→
   Weimar（诗歌短片奖）被归到 `build`。**一个真实 creative 机会没能产生 creative 轴。**
2. 轴匹配是**子串命中、过于宽松** → 单个 UNV 条目同时命中 5 个轴（build/community/creative/research/volunteer）→
   `axis_count` 被**夸大**。所以 `>= 3` 这个门槛现在**不能当可信 gate**，需要人工核对。

按**人工核实**的口径：轴数 = 4 ≥ 3 ✅；按**原始指标**：5（含 2 个伪轴）⚠️。

## 3. E 技术偏置的 root cause

按你给的六类逐条交代（本轮的最终主推荐里技术类 = 0，所以偏置不存在；以下解释**为什么会出现/不出现**）：

| 来源 | 本轮观察 | 判断 |
|---|---|---|
| **query vocabulary bias** | 4 条 query 全是我按"四个非技术方向"手写的 | **主导且不受系统约束**：空画像时系统不提供任何轴覆盖要求，轴分布完全取决于 agent 写什么 query |
| **source family bias** | 无 gap → 没有使用任何 source family | 本轮不存在；空画像路径绕过了 source intelligence |
| **category allocation bias** | `MODE_WEIGHTS` 只覆盖 13 个 category | **结构性**：13 类里**没有** volunteer / creative(艺术) / cross_domain 的入口，轴只能靠事后关键词识别 → 这三类只能"碰巧被发现" |
| **ranking bias** | match 门槛没有挡住任何条目（Unknown 资格被允许进主推荐） | 本轮不存在 |
| **verification survival bias** | 7 条里 4 条因未核实/无确认窗口掉到需确认 | **存在**：主推荐偏向"官方页写清楚"的组织（UNV / MentorsHub / Weimar），小机构与 SPA 站点天然吃亏 |
| **real opportunity supply** | 非技术供给明显充足且可核实 | 现实供给不是瓶颈 |

**结论**：上一轮 E 的技术垄断 = 候选池来源（CS fixture）；本轮无偏置 = 我刻意写了非技术 query。
**两者都不是系统能力的证明** —— 系统的真实问题是：**空画像时没有任何机制保证轴覆盖**，
这属于 planner/query 层，不是 Match 层。

## 4. C 新 extraction contract 的实际字段覆盖率

C 本轮按新 prompt 独立重跑（画像**不含** Singapore / 后端 / Python；只保留"3 年经验、5h/周、想升 Senior"）。
6 个真实候选，每个都标了缺失**原因分类**：

| 字段 | present | source_absent | extraction_miss | not_applicable |
|---|---:|---:|---:|---:|
| `skills_required` | 0.0 | 3 | **0** | 3 |
| `produces` | **1.0** | 0 | 0 | 0 |
| `effort` | 0.5 | 3 | 0 | 0 |

- `produces` 100% 捕获 → 新契约在最关键的"能留下什么"上生效。
- `effort` 50%：另外 3 条**页面本身就没写**时间承诺（source_absent），不是漏抽。
- `skills_required` 0%：3 条属于"讲者征集/治理席位"这类**本来不列技术技能**的机会（not_applicable），
  3 条是页面确实没写（source_absent）。**`extraction_miss = 0`** —— 三种情况被正确区分开了，
  没有把"页面没有"算成"抽漏"。

## 5. C 的 visible Gap→Bridge 是否改善

**改善了，而且是本轮唯一明确的机制性改善**：

| 指标 | 上一轮（存档批次重跑） | 本轮（新 prompt + 新 discovery） |
|---|---:|---:|
| `visible_gap_bridge_rate` | 0.0 | **0.8** |
| `visible_evidence_output_rate` | 0.0 | **1.0** |
| `visible_effort_rate` | 0.0 | 0.6 |

原因：本轮缺口来自**目标语义**（promotion → `公开影响力证据` + `ownership/跨团队项目证据`），
而新发现的机会（TODO Group 治理席位、OpenSSF TAC 公开参与）正好是这些缺口的真实 Bridge →
6 张卡片里 5 张能看到「你现在缺 X → 这条机会能补它」。

**但同时发现一个 P1（下一节）**：C 的 `recommended_now = 0`。

## 6. 五 Persona 是否真正独立完成

**没有**（见 §0）。可验证的部分做到了：五个独立画像文件、独立候选文件、独立输出目录、
跨 persona 禁止词检查通过。**不可验证也无法补做的部分**：独立会话上下文 —— 受配额限制。

## 7. leakage 是否为 0

**是，0 处。** 检查方式有两层：

1. **你点名的禁止词**（出现在画像的背景字段里、而用户原话没说过 → 记泄漏）：
   - B：`大三` / `ESP32` / `Python` / `嵌入式` → 0
   - C：`ESP32` / `embedded` / `Python` / `嵌入式` → 0（本轮 C 画像重建过，旧画像里的 Singapore/后端 已被剔除）
   - E：`后端五年` / `AI 工程` / `6 小时` / `不辞职` / `Python` / `ESP32` / `嵌入式` → 0 ✅
2. 程序化 `presentation.context_leakage()` → 0

**本轮确实修掉过一处**：上一轮发现 E 的存档画像带着用户从未提过的技术背景（违反 §9），
已按原话重建为空画像，旧画像保留为 `case-e-unknown/profile-previous.json` 供对照。
另：A 的画像里有 1 个 `inferred_pending` 推断值（由专业推断 embedded），已标注为
「可驱动搜索、不参与资格判定」。

## 8. D 是否保持 Golden Scenario

**无法确认，本轮不给结论。** 原因：D 的 prompt（5 年后端转 AI）没有存档会话，本轮用的是
最接近的真实 baseline（3 年嵌入式转 Edge AI）做**表达层对照**，且该记录**没有 evidence 块与
`produces`/`gap` 关联**，因此 5 条 golden 标准里只有 2 条可验证：

| D 的 golden 标准 | 本轮可验证性 | 结果 |
|---|---|---|
| 6h 资源约束不被突破 | ✅ 可验证 | 通过（`visible_effort_rate = 1.0`，无资源冲突） |
| 单一 external mainline（不散成链接堆） | ✅ 可验证 | 通过（4 条主推荐 + 1 条需确认，未膨胀） |
| 利用已有后端经验 | ❌ 记录里没有技能/经历字段 | 无法验证 |
| 拒绝实习降级路线 | ❌ 候选属性不足以判定 | 无法验证 |
| 识别 AI production / platform bridge | ❌ 记录里没有 gap/bridge 关联 | 无法验证 |

→ **D 暂时只能作为"部分 golden"**：它的 5 条标准已写进验收清单（见 §13），等独立重跑后再冻结。

## 9. B 是否可以成为 Gap→Bridge Golden Scenario

**可以，就 Gap→Bridge 那条链而言成立**（本轮数据）：

- 真实核验：OIST Research Internship **Spring 2027 轮，10/15 截止，现在开着**；
  東京大学 研究生（Research Student）制度全年受理（2026-09-20 核验）。
- 缺口来自**用户原话**（"科研经历比较少"）+ 升学目标 → `教授/实验室联系人` + `研究经历/论文/实验室接触`。
- 卡片上能看到完整链路：`你现在缺 教授 / 实验室联系人 → 这条机会能补它`（2/3 张卡片有 gap_filled）。
- 资格边界守住了：OIST 要求"本科最后两年 / 硕士任何年级 / 已毕业"，用户**未说学历**，因此只写
  「你的资料未提供学历，无法判断」，**没有**把"明年申请"写成"现在就能申"。

**结论**：B 可以固定为 **Gap→Bridge golden scenario**（前提是下一轮用独立会话复跑一次同样的结果）。
自建研究项目在 B 的输出里被放在 `self_directed` 单独一段，未混入推荐。

## 10. A 的 contextual-gap hypothesis

**确认成立（机械验证）**：A 没有声明任何 goal → `career_direction = explore` →
`gaps.collect_gaps` 产出的缺口**全部是 `contextual_gap`**，`development_gaps = 0` →
不做 Bridge 搜索 → `visible_gap_bridge_rate = 0.0`。

表示为 **`CORE_HYPOTHESIS_A`**：*A 类用户（在"比赛/开源/实习"之间选择但没有长期目标）会不会
因为所有缺口都被判成 contextual 而显得"不够个性化"？* 本轮**未改 `career_direction()`**(§12)，
留给真人测试验证。注意 A 的其他指标是健康的：`visible_evidence_output_rate = 1.0`、
`visible_effort_rate = 0.8`、1 条推荐 + 4 条需确认。

## 11. 还有没有 P0 / P1 blocker

**没有 P0**：泄漏 0、伪精确 0、强结论 0、主推荐里无过期/未核实条目、自建路径未混入。

**P1（已定位、本轮按 §16 未修，进入 future fix list）**：

| ID | 问题 | 证据 | 影响 |
|---|---|---|---|
| P1-1 | **`goal_fit` 不认 promotion 方向的机会**：C 的目标是 `career`，而机会是 `open_source` / `event` → `goal_fit = 15` → match **51 < 55** → **`recommended_now = 0`** | C 本轮 6 条全部落在需确认 | 最需要建议的晋升型用户拿不到主线（TODO Group SC / OpenSSF TAC 明明 actionable + 证据完整） |
| P1-2 | 语言/国籍未声明 → 所有要求英语的机会都是 Unknown；与 P1-1 叠加后薄画像主线为空 | C 的 6 条 needs_confirmation 首条都是语言 | 薄画像用户的主线恒空 |
| P1-3 | **schema 没有年龄字段**：18+ 类机会（志愿者很常见）无法被表达 | UNV 官方唯一硬要求是 18+，`EVIDENCE_FIELDS` 里没有 age | 我会把与证据矛盾的 `education_level` 删掉，结果是"无限制的机会按无限制处理" → **不够保守** |
| P1-4 | 轴指标不可信：creative 词表缺 film/poetry/art；子串匹配夸大 `axis_count` | Weimar 被标 build；UNV 一条命中 5 轴 | explore 验收指标本身需要修才能当 gate |
| P1-5 | 13 类 taxonomy **没有 volunteer / creative(艺术) / cross_domain 入口** | 三轴的候选只能靠 general_search 碰 | 空画像时的轴覆盖不受系统保证（§3 的主导原因） |
| P1-6 | 空画像下大量机会停在 Unknown，参与措辞重复为待确认档 | E 的 3 条主推荐 | 信息量低；需真人测试判断是否可接受 |

## 12. 是否可以打 `v3.0.0-rc2`

**不建议，本轮不打。** 三条理由：

1. **本轮的核心要求（五个独立会话）没完成** —— 这是"可信基线"的前提条件，不是细节。
2. **P1-1/P1-2 会直接出现在下一次真人测试里**：晋升型用户的回答会是"没有主线，只有 6 条待确认"，
   而这恰恰是最常见的用户类型之一。这不是展示层问题，是 Match 的目标映射问题（所以本轮没动）。
3. **D 的 golden 状态未确认**（§8），B/E 的 golden 也都依赖独立会话复跑。

**建议**：配额恢复后先做 ① 五 persona 独立会话重跑（尤其 D 与 C）→ ② 若 C 仍为 0 主线，
再按"真实失败 → 复现 → 定位 → 最小修复"处理 P1-1/P1-2（这将是唯一允许改 Match 映射的依据）。
在那之前，可以打一个诚实的中间标记（例如 `v3.0.0-rc2-validation-partial`），
但不要把它当作 rc2 基线。

**本轮三处小改动（都是定位/修正性质，非新功能）**：
① `community` 参与措辞对齐 §6 的三标签（原实现自造了第四个 `Unknown`，与你规定的
"Open to join / Prerequisites apply / Invitation or selection required" 不符）；
② E 的三条候选删除了**与自身证据矛盾**的 `education_level`（官方页明确"无学历/无背景要求"），
并据官方原文补了 `nationality_requirement = open to all nationalities`；
③ **仓库卫生测试的误报**：`test_no_placeholders` 把真实组织名 **TODO Group**
（Linux Foundation 下的社区，出现在本轮真实机会名里）当成占位符 —— 这是测试被真实数据暴露的缺陷，
已为正名加白名单（`TODO:` 这类真占位符仍会被抓到）。**必须说明：本轮第一次提交（`594703c`）
是在这个测试失败的情况下提交的**（我当时没检查输出就提交了），修复在随后的提交里。

## 13. Golden Scenario 冻结清单

**D — resource-constrained 转行 golden（待独立重跑确认）**
1. 6h/周 约束不被突破（本轮已验证 ✅）
2. 单一 external mainline，不散成链接堆（本轮已验证 ✅）
3. 利用已有职业资本（后端经验）而不是从零开始
4. 明确拒绝"先拿实习工资降级"路线
5. 识别 AI production / platform bridge 而不是把它当普通课程

**B — Gap→Bridge golden（数据成立，待独立会话复跑）**
缺口（教授接触 / 研究经历）→ 真实 Bridge（OIST 10/15、東大研究生）→ 产出（研究经历、推荐信潜力）
→ 指向（研究型学位申请）；资格边界必须写 Unknown 而不是默认符合。

**E — Explore golden（条件性通过）**
轴数按**人工核实** ≥3（本轮 4）；`technical_share` 记录但不设阈值；
轴指标修好之前，不得用原始 `explore_axis_count` 当 gate。

---

## 附：§10 统一统计

来源：`usertests/output-ux/VALIDATION_UNIFIED.json`

| case | conf | 推荐 | 需确认 | 轴数 | verified_rate | gap_bridge | evidence_output | effort | 伪精确 | 强结论 | 泄漏 | 自建混入 | 方法 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | low | 1 | 4 | 4 | 0.50 | 0.00 | 1.00 | 0.80 | 0 | 0 | 0 | 0 | 上轮本会话内 |
| B | medium | 2 | 1 | — | 1.00 | 0.67 | 0.67 | 0.33 | 0 | 0 | 0 | 0 | 上轮本会话内 |
| C | medium | **0** | 6 | — | 0.875 | **0.80** | **1.00** | 0.60 | 0 | 0 | 0 | 0 | 本轮独立重跑 |
| D | medium | 4 | 1 | — | — | 0.00 | 0.00 | 1.00 | 0 | 0 | 0 | 0 | 表达层对照（未重跑 gate） |
| E | low | 3 | 4 | 5（人工核实 4） | 0.429 | 0.00 | 0.571 | 0.429 | 0 | 0 | 0 | 0 | 本轮独立重跑 |

E 单独：`technical_share = 0.0`（0/7）。

三点读表提醒：① C 的 `推荐 = 0` 是 P1-1 的直接后果，不是展示层 bug；
② D 的 gap_bridge / evidence_output = 0 是因为该记录没有 `produces` 与 gap 关联（表达层对照）；
③ A 的 gap_bridge = 0 是 `CORE_HYPOTHESIS_A`（无目标 → 全部 contextual）。
