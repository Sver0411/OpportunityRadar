# Extraction Policy — 结构化抽取与反幻觉

Step 8 的执行规范。目标：把网页变成 `opportunity.schema.json` 记录，
且**不制造任何页面上没有的事实**。

---

## 1. 核心三态：Explicit / Inferred / Unknown

每个重要字段在抽取时都要自问属于哪种状态：

| 状态 | 定义 | 使用场景 |
|---|---|---|
| **Explicit** | 页面上明确写出，可引用原句 | 硬性资格判断优先使用 |
| **Inferred** | 由页面信息合理推导，但未明写 | 只能作参考，必须标注 |
| **Unknown** | 页面没写 | 写 `null`，**不要填推测值** |

规则：
- 硬性条件（学历、年级、国籍、语言、GPA、deadline）**必须 Explicit 才能用于
  判定 `Eligible` / `Ineligible`**；用 Inferred 时最高只能给 `Probably Eligible`。
- 在输出里，Unknown 要显式写出来（"△ 页面未明确语言要求"），
  因为这本身就是对用户有价值的信息。

### 反幻觉的典型例子（必读）

> 某日本企业页面没有写语言要求。
>
> ❌ 错误：`language_requirement: "JLPT N2"`（因为"日本企业一般都要求 N2"）
> ✅ 正确：`language_requirement: null`，
>    输出写 "Japanese requirement: Not explicitly specified（页面未明写）"
>
> 理由：这是日本企业 ≠ 这条招聘要求日语等级。要求可能在别的页、可能不要求、
> 也可能只要求日常会话。任何推断都可能让用户错判自己能不能申请。

同理禁止：
- 看到"接受本科生"就推断"研究生也接受"。
- 看到"2026 年 9 月截止"就推断"2027 年也会同期开放"。
- 看到导师研究方向就推断"他在招 RA"。
- 看到"paid internship"就推断具体薪资。
- 看到公司总部在某国就推断工作地点在某国。

---

## 2. 字段级规则

| 字段 | 来源要求 | 规则 |
|---|---|---|
| `title` | 页面标题 | 保留官方名称原文（可加中文/英文简注）；不要自创营销化标题 |
| `organization` | 主办/招聘主体 | 用官方主体名；不要把品牌子产品当主体 |
| `primary_category` / `secondary_categories` | 判断 | 见 `opportunity-taxonomy.md` §14 消解表 |
| `summary` | 页面 | ≤2 句、纯事实、无形容词堆砌、不复述"这是一个很好的机会" |
| `country` / `city` | 页面 | 只写明确写出的地点；远程写 `remote: true` 并把 country 置 `null`（若确为全球远程） |
| `education_level` | 页面 | 归一化见 §3；未写 → `null` |
| `student_year` | 页面 | 归一化见 §4 |
| `graduation_window` | 页面 | 如"2027 年 3 月毕业"、"卒業年度 2028"；未写 → `null` |
| `major_requirement` | 页面 | 原样保留（如 "Electrical Engineering or related field"），不要翻译成"电子相关"后丢失原句 |
| `skills_required` / `skills_preferred` | 页面 | 按要求强度词分流（§5） |
| `language_requirement` | 页面 | 只在明写时填；否则 `null` + 输出说明 |
| `nationality_requirement` | 页面 | 是否有国籍/签证限制；未写 → `null`（**不等于"无限制"**） |
| `school_requirement` | 页面 | 是否限定学校层次/名单 |
| `GPA_requirement` | 页面 | 原样字符串（"3.0/4.0"、"80 分以上"），不要换算 |
| `application_open` / `deadline` | 页面 | 走 `normalize_date.py`；年份不明不要猜 |
| `event_start` / `event_end` | 页面 | 同上；注意区分报名截止与活动日期 |
| `cost` | 页面 | 报名费/参加费；免费写 `"free"`；未写 `null` |
| `compensation` | 页面 | 薪资/奖金；**明确无薪要写出来**（"unpaid"、"無給"、"无薪"） |
| `prize` / `funding` | 页面 | 奖金池、资助额度；未写 `null` |
| `team_requirement` | 页面 | 是否需组队、人数、是否允许跨校 |
| `time_commitment` | 页面 | "每周 20 小时"、"3 个月全职"；未写 `null` |
| `required_materials` | 页面 | 简历/CV/成绩单/提案/作品集 |
| `official_url` / `discovery_url` | 见 `trust-policy.md` | 必区分 |
| `trust_tier` | 判断 | A/B/C/D |
| `verification_status` | 判断 | verified_official / partially_verified / unverified / conflicting / expired |
| `last_verified` | 实际验证日期 | YYYY-MM-DD |

缺字段一律 `null`。**不要为了让记录"看起来完整"而填值。**

---

## 3. `education_level` 归一化

| 取值 | 对应表述 |
|---|---|
| `high_school` | 高中生、高校生、high school |
| `undergraduate` | 本科生、学部生、大学生、bachelor |
| `master` | 硕士、修士、修士課程、master's |
| `phd` | 博士、博士課程、doctoral |
| `postdoc` | 博士后、ポスドク |
| `any` | 明确写"不限学历/any level" |
| `null` | 未写 |

多值用数组（如 `["undergraduate", "master"]`）。不确定的模糊表述
（如 "students"）→ `null` + 标注 "页面仅写 students，未区分学历"。

---

## 4. `student_year` / 时间线归一化

- 中国场景：**"应届生"身份**由毕业年份决定 → 优先记录 `graduation_window`；
  页面写"大三/大四/研一"时填 `student_year`（数字）。
- 日本场景：企业按**「卒業年度」（毕业年度，非当前学年）**筛选 →
  必须记录 `graduation_window`；「学部生」「修士」进 `education_level`。
  「インターンシップ」不区分年级的，`student_year: null`。
- 英美场景：`freshman/sophomore/junior/senior` → 1/2/3/4。
- 页面写"在读学生"而无年份 → `student_year: null`。

---

## 5. 要求强度词 → required / preferred

| 语言 | required 信号 | preferred 信号 |
|---|---|---|
| EN | required, must, essential, minimum | preferred, nice to have, plus, advantageous, a bonus |
| CN | 必须、要求、需、需具备、熟练掌握（视语境）、硬性 | 优先、加分、有…者优先、熟悉者优先、最好 |
| JA | 必須、応募資格、要件、～以上 | 歓迎、尚可、あると望ましい、できれば |

模糊表述（"strong technical background"、"related discipline"、
"～に関する知識がある方"）→ 归入 `skills_preferred` 并在
`notes` 标注 "语义条件，需人工判断"，而不是塞成硬性要求。

---

## 6. 日期处理

任何日期字符串先过脚本，不要手写转换：

```bash
python3 scripts/normalize_date.py "9月20日" --default-year 2026 --now 2026-09-14
```

- 年份不明 → 脚本返回 `year_unknown: true`，记录 `deadline: null`，
  改在 `summary`/输出里写"9月20日（年份未在页面标明）"。
- 范围（"9月20日–10月5日"）→ `application_open` + `deadline` 分别记录。
- "Rolling / 常年 / 招满即止 / 随時" → `deadline: null`，在输出标注"滚动招募"。
- 时区：页面写了时区就保留（`2026-09-25T23:59+09:00`）；没写不要补。

---

## 7. `tags` 生成

3–8 个短标签，用于后续检索与兴趣匹配：

- 技术栈：`esp32`、`python`、`ros`、`fpga`、`tinyml`
- 领域：`embedded`、`edge-ai`、`robotics`、`photography`
- 性质：`remote`、`paid`、`unpaid`、`beginner-friendly`、`portfolio-output`、`team-required`
- 资格：`undergraduate-ok`、`no-gpa-requirement`、`local-language-required`

只用页面能支撑的标签，不要凭感觉添加 `prestigious`、`high-value` 这类主观标签。

---

## 8. 抽取产物与校验

1. 记录写入 JSON 文件（如 `.opportunity-radar/last-run.json`），
   结构符合 `schemas/opportunity.schema.json`。
2. `id` 生成：`<org-slug>-<title-slug>-<year>` 全小写连字符
   （如 `sony-embedded-internship-2027`）；同一条机会的 id 必须**稳定**，
   否则 Seen State 会失效。
3. 抽取后自检：
   - [ ] 有无字段是我"推"出来但页面没写的？（→ 改 `null` 或降级为 Inferred）
   - [ ] `deadline` 是否过了脚本？
   - [ ] `official_url` 是我真的打开过并读到该事实的页面吗？
   - [ ] `verification_status` 与 3 项关键事实的确认情况一致吗？
4. 同一批记录送 `scripts/dedupe.py` 去重（Step 9）。
