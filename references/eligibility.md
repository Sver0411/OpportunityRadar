# Eligibility Engine

Step 10。目标：给用户一个**可行动**的资格判断，而不是一个看起来权威的 Yes/No。

## 1. 五种判定（只有一个正确选项）

| 判定 | 定义 | 证据要求 |
|---|---|---|
| `Eligible` | 所有硬性条件都已 Explicit 确认满足 | 每条硬性条件都有官方页面原句支撑 |
| `Probably Eligible` | 硬性条件基本满足，但存在语义条件或未明写的项 | 至少一条关键条件为 Inferred / Unknown |
| `Unknown` | 关键条件缺失，无法判断 | 页面根本没写资格范围，或缺申请人自身信息 |
| `Probably Ineligible` | 存在一条可能不满足的硬性条件 | 需指出是哪一条，说明为何仍不确定 |
| `Ineligible` | 明确不满足某条硬性条件（或已过期） | 需引用页面上明确的门槛与用户的明确信息 |

**禁止**：一律输出 Yes/No；把 `Unknown` 说成"应该可以"；
在用户信息不足时给出 `Eligible`。

## 1.1 页面对资格什么都没写 → `Unknown`

如果页面没有给出任何可确认的资格条件（`education_level`、`student_year`、
`graduation_window`、`nationality_requirement`、`school_requirement`、
`GPA_requirement`、`language_requirement` 全为空）：

```
Eligibility = Unknown
```

**不是** `Probably Eligible`。理由：**"没写要求"不等于"用户大概率符合要求"**。
`scripts/score.py` 按此实现（`missing_source` 分支）。

三种情形的区别：

| 情形 | 结论 |
|---|---|
| A. 完全没有资格信息 | `Unknown` |
| B. 若干明确条件都满足，但还有语义条件（如 `related field`） | `Probably Eligible` |
| C. 所有明确硬条件都确认满足，且不存在影响资格的未知项 | `Eligible` |

不要因为"页面没写更多内容"就自动给 `Eligible`。

## 1.2 Evidence Gate：只有 explicit 证据才能硬性淘汰

`opportunity.evidence.<field>.status` 决定该字段是否够格做硬性判断：

| status | 能否用于**硬性淘汰**（判为不符合） | 能否支撑乐观结论 |
|---|---|---|
| `explicit` | ✅ 可以 | ✅ 可以给 `Eligible` |
| `inferred` | ❌ **不可以** | ❌ 最多 `Probably Eligible` |
| `unknown` | ❌ 不可以 | ❌ 最多 `Probably Eligible` |
| 无该字段条目（`missing`） | ❌ 不可以 | ❌ 最多 `Probably Eligible` |
| 整条记录没有 `evidence` 结构（`legacy` 旧格式） | ✅ 可以（向后兼容） | ❌ 最多 `Probably Eligible`，并提示 `provenance_unavailable` |

例子：

```json
{
  "language_requirement": { "language": "Japanese", "exam": "JLPT", "min_level": "N2" },
  "evidence": { "language_requirement": { "status": "inferred" } }
}
```

即使用户没有 N2，也**不能**判 `Probably Ineligible` —— 页面并没有明确写这条要求。
正确输出：`Unknown` + 提示"language_requirement 为 inferred，不能作为硬性门槛"。

实现见 `scripts/score.py` 的 `evidence_status()` / `is_hard_evidence()` / `add()`。

## 1.3 `Ineligible` 与 `Probably Ineligible` 的边界

`Ineligible` 只用于**无歧义的确定性冲突**；涉及措辞解释的一律用 `Probably Ineligible`。

| 条件 | 冲突时的判定 |
|---|---|
| 报名已截止 | `Ineligible` |
| `education_level` 不符（枚举值） | `Ineligible` |
| `student_year` 不符 | `Ineligible` |
| `graduation_window` 不在窗口内（按月比较） | `Ineligible` |
| 国籍/工作许可措辞冲突 | `Probably Ineligible` |
| 学校名单/层次无法完整解析 | `Probably Ineligible` 或 `Unknown` |
| GPA 同体系且低于要求 | `Probably Ineligible` |
| 语言成绩明确未达等级 | `Probably Ineligible` |

`Ineligible` 的记录会从结果列表中移出，并进入 excluded 清单（附原因）。

## 1.4 两条不可违反的判定原则

### 原则一：硬条件优先于语义判断

页面明确写了、用户也明确表述过的确定项（deadline、学历、年级、毕业年份、
国籍/工作许可、学校限制、GPA、语言成绩）——**模型判断不能推翻它**。

```
页面：PhD only         用户：本科（明确）
模型 verdict：Eligible
→ 最终必须是 Probably Ineligible / Ineligible，并在理由里写明被硬条件覆盖
```

合并规则（`scripts/score.py` 的 `merge_verdict()` 已实现）：

| 硬条件结论 | 模型 verdict 的影响 |
|---|---|
| 明确冲突（Ineligible / Probably Ineligible） | **不可推翻**，直接采用硬条件结论 |
| 硬条件全部满足（Eligible） | 只能更保守（可降级），不能更乐观 |
| 因**画像缺信息**而 Unknown | 模型可判断（它可能在对话里拿到了画像之外的信息） |
| 因**页面缺信息**或口径不可比而 Unknown | 模型最多给到 Probably Eligible |

模型能做的语义补充：`related field` 类专业判断、经验相关性、"strong background" 这类
模糊要求——这些只影响 `Eligible` 与 `Probably Eligible` 的区分。

### 原则二：画像缺失 ≠ 不满足

Profile 是渐进式构建的。**用户没填语言成绩，不代表不会这门语言。**

```
机会：要求 Japanese N2 以上
画像：有 Japanese 记录，但 exam/score/level 为空
→ Unknown（信息不足，需向用户确认）
```

只有用户**明确表示不具备**时才允许向不满足方向判断。约定写法：
profile 的语言条目里 `level` 或 `score` 填 `none` / `no` / `不会` / `无`。

```
画像：{"language": "Japanese", "level": "none"}   ← 明确不会
机会：要求 Japanese N2 以上
→ Probably Ineligible
```

同理适用于：GPA 未提供、学校未提供、年级未提供、国籍未提供、毕业时间未提供。
这些一律 `Unknown` + 说明"补上这项我就能给出确定判断"。

---

## 2. 判断顺序（确定性优先）

按此顺序逐条过。**任何一条明确不满足 → 直接给结论并停止下推**（除非用户问的是细节）。

```
1. 时间窗口      deadline 是否已过 / 是否在报名期 / 是否滚动招募
2. 学历          education_level ∩ 用户学历
3. 年级 / 毕业年份 student_year、graduation_window（日本按卒業年度）
4. 国籍 / 签证    nationality_requirement、work authorization、CPT/OPT/在留資格
5. 学校限制      school_requirement（是否限定名单/层次）
6. 专业          major_requirement
7. GPA           GPA_requirement
8. 语言          language_requirement
9. 年龄 / 其它    age、性别/健康等特殊限制（如存在）
10. 语义条件     "related discipline"、"relevant experience"、"strong background"
11. 材料          required_materials 是否用户可产出（作品集、提案、推荐信）
```

语义条件（第 10 步）放在最后：它不该让一条本来该死的硬性条件"复活"，
只影响 `Eligible` 与 `Probably Eligible` 的区分。

**`scripts/score.py` 已实现的确定性检查**（逐项累积，取最严重的结论；
不存在"第一个满足就通过"的短路）：

| 条件 | 判定方式 |
|---|---|
| 时间窗口 | 截止日已过 → `Ineligible`；`rolling` 不视为过期 |
| 学历 | 页面列表 vs 画像学历（`any` 表示不限） |
| 学年 | 页面学年 vs `current_year` |
| 毕业时间 | **按月比较**区间（见 §4.4） |
| 国籍 / 工作许可 | 页面限制信号 vs 画像 `nationality` + `constraints.visa` |
| 学校限制 | 页面学校要求 vs 画像 `school` |
| GPA | **仅在同评分体系内比较**，不做换算 |
| 语言 | 见 §1.5 原则二与 §4.3 |
| 专业 | 语义判断，只标记 `needs_semantic_check`，不产生硬冲突 |

只有全部有数据的硬条件都确认满足时才输出 `Eligible`；任一项信息缺失即 `Unknown`。

---

## 3. 语义条件处理：`or related field`

这是最高频的模糊门槛。处理方式：

| 用户专业 | 页面写 | 判定 | 说明话术模板 |
|---|---|---|---|
| IoT 工程 | Electrical Engineering or related field | `Probably Eligible` | "物联网工程通常与 EE/CS 存在较高相关性，但最终以组织方定义为准。" |
| 物联网工程 | Computer Science required | `Probably Eligible`（偏保守） | "页面写 CS 要求；物联网工程一般覆盖编程与系统课程，但是否属其定义的 CS 需向组织方确认。" |
| 机械工程 | Mechatronics or related field | `Probably Eligible` | "机械工程与机电一体化在课程上有较大交集。" |
| 日语专业 | Engineering or related field | `Probably Ineligible` | "与工程类学科关联度低；若项目接受跨专业（页面未写明），仍可尝试。" |
| 数学 | "Quantitative background required" | `Eligible` | 明确满足。 |

**规则**：
- 组织方定义优先。页面若有"详见 FAQ/募集要項"的说明链接，去读它，不要用直觉。
- 保留页面的原始措辞（英文原句），再加一句中文判断。
- 跨专业不等于没机会：如果页面有"跨专业欢迎/専攻不問"字样，判定上升一档。

---

## 4. 地区特定规则放在 locale 层

资格判定的**机制**（下面 4.1–4.4）在 Core 里；**地区特有的口径**属于 locale 知识：

| 地区 | 特有概念 | 位置 |
|---|---|---|
| 日本 | 卒業年度、インターン 形态、在留資格、有給/無給 | `references/locales/jp.md` |
| 中国 | 应届生身份、保研/推免资格、夏令营、CET | `references/locales/cn.md` |
| 美国 | work authorization、CPT/OPT、sponsorship、REU | `references/locales/us.md` |
| 英国 / 爱尔兰 | placement year、graduate scheme、right to work | `references/locales/uk.md` |
| 德国 | Pflichtpraktikum、Werkstudent、HiWi、CEFR | `references/locales/de.md` |
| 其他地区 | —— | `references/locales/generic.md`（运行时按需处理） |

**只在目标地区需要时加载对应文件。** 没有对应文件的国家按通用规则处理，功能不受影响。

通用原则（不分地区）：

- 资格线按当地口径读（毕业年份 / 应届身份 / 学年），不要把一个地区的口径套到另一个地区。
- 只有当页面**明确写出**限制时（国籍、签证、学校、语言等级），才可能产生否定结论；
  没写就是 `Unknown`，不是"默认满足"也不是"默认不满足"。

### 远程 / 全球项目
- 明确写 "open to students worldwide" → 国籍条件为 Explicit 满足。
- 未写国家限制但项目明显本地化 → `Unknown`，并在 △ 里提示。

### 4.1 国籍 / 工作许可

页面出现限制性措辞（`citizens only`、`must be a US citizen`、`国内在住`、
`no sponsorship`、`legally authorized to work`）时：

| 情况 | 判定 |
|---|---|
| 页面明确写"国籍不限 / open to all nationalities" | `Eligible`（该条件满足） |
| 画像提供了国籍或签证状态，且与要求相符 | `Eligible` |
| 页面不提供签证赞助，画像标注需要赞助 | `Probably Ineligible` |
| 画像**未提供**国籍与签证 | `Unknown` + 提示补信息（**不是**不满足） |
| 有国内/地区限制，但页面没写出具体国家 | `Unknown`（信息不足以逐字比对） |

注意区分："页面没写国籍要求" ≠ "无国籍限制"，只是 `nationality_requirement: null`。

### 4.2 学校限制

页面限定学校名单、层次或"仅本校学生"。画像有学校且能对应上 → `Eligible`；
画像没提供学校 → `Unknown`；有学校但无法确认是否在名单内 → `Unknown`（宁可不确定）。

### 4.3 语言成绩

| 情况 | 判定 |
|---|---|
| 页面要求某语言，画像**完全没有该语言的记录** | `Unknown`（缺失不等于不会） |
| 画像有该语言但没有成绩/等级 | `Unknown` |
| 画像有成绩且达到要求 | `Eligible` |
| 画像有成绩但未达要求 | `Probably Ineligible` |
| 画像明确标注不会该语言（`level: "none"`）而页面有硬性要求 | `Probably Ineligible` |
| 页面未写明语言要求 | 不参与判断（`language_requirement: null`），并在 △ 提示"语言要求未写明" |

绝不允许："因为是日本企业，所以推断要求 N2"。

### 4.4 毕业时间（按月比较，不看年份就通过）

把页面的毕业时间要求解析成**月份区间**再比较，例如：

| 页面要求 | 用户毕业时间 | 判定 |
|---|---|---|
| `2027-09 ~ 2028-06` | `2027-06` | 不在窗口 → `Probably Ineligible` |
| `2027-09 ~ 2028-06` | `2028-03` | 在窗口内 → `Eligible` |
| `2028-03`（日本 3 月卒業見込） | `2028-06` | 不在窗口（不同届）→ `Probably Ineligible` |
| `Graduating between Sep 2027 and Jun 2028` | `2028-03` | 在窗口内 |
| 只有年份（`2027`） | `2027-06` | 按年份比较并通过，但需注明置信度较低 |
| 无法解析 | — | `Unknown` |

**仅年份相同不能作为通过依据。**

---

## 5. 信息缺失怎么办

1. **用户信息缺** → 不要停任务。按现有信息判断并在结论后列出"这会影响判断"的项：
   > `Unknown`（判断依据不足：页面要求高三/大四在读，你未提供年级）
2. **机会信息缺** → 检查是否有 FAQ / 募集要項 / PDF 简章；
   都没有 → `Unknown` + "页面未写明资格范围"，并把这项列入用户的待确认事项。
3. **绝不**为了给用户一个结论而假定缺失的一方。

---

## 6. 输出模板

```
资格：Probably Eligible
✓ 接受本科生（官方页面明确）
✓ 专业要求 "Electrical Engineering or related field"，与你专业高度相关
△ 语言要求页面未写明（需向组织方确认）
```

```
资格：Ineligible
✗ 页面明确要求 2027 年 3 月毕业，你预计 2028 年毕业
```

```
资格：Unknown
? 页面仅写 "students"，未区分学历与年级
```

**禁止话术**："你一定能申上"、"必须去试"、"这个肯定不行"（除非有明确硬性冲突）。
判断要给依据，不要给鼓励。

---

## 7. 自检

- [ ] 每条硬性条件都能指回官方页面原句吗？
- [ ] 有把 Inferred 当成 Explicit 用吗？
- [ ] 到期/停办的项有没有被误标为可申请？
- [ ] 跨专业项的措辞是否保留了"以组织方定义为准"？
- [ ] 有没有因为用户信息缺失就直接放弃判断（应给 `Unknown` + 待补信息）？
