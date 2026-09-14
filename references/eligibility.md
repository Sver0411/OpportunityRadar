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

## 4. 地区特定规则

### 中国
- **应届生身份**由毕业年份决定。校招/提前批/补录几乎都限定毕业年份 →
  `graduation_window` 缺失时只能是 `Unknown`。
- 保研/夏令营/预推免绑定"推免资格"（学校层次 + 排名），无排名信息 → `Unknown`。
- "在校生/应届生"用词差异要保留原句。

### 日本
- 企业筛选按**「卒業年度」（毕业年度）**，不是当前学年。
  页面写「2028年3月卒業見込」→ `graduation_window` 填该值。
- 「インターンシップ」分 有給 / 無給、短期 / 長期、選考直結型（表现好可直通内定）
  —— 这些影响价值判断，写进 `notes` 与 `value`。
- 「外国籍可」「日本語能力 N 以上」若不写明，**不要推断**（见 anti-hallucination 规则）。

### 英美 / 欧洲
- Internship 常伴随 work authorization 要求（是否需要 sponsorship）。
  页面写 "must be legally authorized to work" → 归入 `nationality_requirement`。
- Placement year / Pflichtpraktikum 对在读年级有强绑定。
- 学生签证工作时长限制（如英国 term-time 20 小时）可能让"长期实习"不可行 →
  在 output 的 △ 里提示，不要自作主张判定 `Ineligible`。

### 远程 / 全球项目
- 明确写 "open to students worldwide" → 国籍条件为 Explicit 满足。
- 未写国家限制但项目明显本地化 → `Unknown`，并在 △ 里提示。

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
