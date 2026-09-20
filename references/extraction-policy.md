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

### 1.1 用 `evidence` 结构化记录证据，而不是塞进 notes

`notes` 是自由文本，无法被脚本检查。关键字段的证据写到 `evidence`：

```json
"evidence": {
  "deadline": {
    "status": "explicit",
    "source_url": "https://example.com/program",
    "quote": "Application closes 2026-10-03 23:59 JST",
    "verified_at": "2026-09-14"
  },
  "language_requirement": {
    "status": "unknown",
    "source_url": "https://example.com/program",
    "note": "页面未写明语言要求；不因公司所在地推断"
  }
}
```

需要追踪证据的字段（`scripts/common.py` 的 `EVIDENCE_FIELDS`，`score.py` 会自动指出缺口）：
`application_status`、`deadline`、`education_level`、`student_year`、`graduation_window`、
`major_requirement`、`language_requirement`、`nationality_requirement`、`school_requirement`、
`GPA_requirement`、`compensation`、`organization_size`。

**`application_status` 有两个层次，都要写，且都不是用户自己的申请进度**：

| 位置 | 含义 | 取值 |
|---|---|---|
| 顶层 `application_status` | **机会侧**状态：官方页面观察到的机会本身是否开放 | `open` / `rolling` / `closed` / `not_open` / `unknown` |
| `evidence.application_status` | 该状态的证据 | `{status: explicit, source_url, verified_at}`（`verified_at` 30 天内） |

`rolling` = 官网明确"持续招募、无固定截止"（如开源之夏）。两者缺一，机会都进不了主推荐区；
缺顶层字段时报错会明确写 `top-level application_status`。**不要把** `saved` / `applied` 这类
用户侧跟踪值（`scripts/state.py` 的那一套）填进机会侧字段。

**`required_materials` 不等于缺口**：报名材料分三类去处理 ——
公开产出物（portfolio / demo / writeup / 作品集）才可能构成 portfolio 缺口；
手续类（CV、护照、申请表、身份/学籍证明、报名、费用）进 `logistics_prerequisites`；
其余进 `preparation_items`。后两类**影响 readiness，不影响缺口统计与 Bridge 搜索**。

`status` 取值只能是 `explicit` / `inferred` / `unknown`；
`explicit` 建议附 `source_url`，能附 `quote`（页面原句）更好，便于复核。

### 1.2 evidence 直接决定能否硬性淘汰（必须理解其后果）

`scripts/score.py` 的 **Evidence Gate** 按 `status` 决定字段是否够格做硬性判断：

| status | 硬性淘汰（判不符合） | 说明 |
|---|---|---|
| `explicit` | ✅ | 页面明写，可作为门槛 |
| `inferred` | ❌ | 推断值**不得**用于淘汰，改判 `Unknown` |
| `unknown` | ❌ | 同上 |
| 有条目但该字段缺席 | ❌ | 同 `unknown` |
| 整条记录没有 `evidence` | ✅（兼容旧格式） | 但结论封顶 `Probably Eligible`，并提示 `provenance_unavailable` |

实操含义：**标注要诚实**。把推断出来的要求标成 `explicit` 会导致用户被错误地淘汰；
反之，页面分明写了却标成 `unknown`，会让本来可以确定的判断退化成"信息不足"。
标错方向的代价不对称——**宁可标 `unknown`，也不要为了"看起来完整"而标 `explicit`**。

尚未确认的字段，宁可省略 entry 也不要写 `explicit`。

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
| `country` / `region` / `city` | 页面 | 只写明确写出的地点；由城市推导省/州时标明推断；远程写 `remote: true` 并把 country 置 `null`（若确为全球远程） |
| `education_level` | 页面 | **申请人当前学历门槛**，不是项目授予学位；归一化见 §3；未写 → `null` |
| `program_degree` / `cohort_year` | 页面 | 教育项目授予学位与毕业/入学届别单独记录，绝不当作申请人学历或申请开放年份 |
| `organization_size` / `organization_type` | 可靠机构资料 | "小公司"须有规模与主体证据；未知填 `unknown`，不能从"专精特新"或品牌名推断 |
| `student_year` | 页面 | 归一化见 §4 |
| `graduation_window` | 页面 | 如"2027 年 3 月毕业"、"卒業年度 2028"；未写 → `null` |
| `major_requirement` | 页面 | 原样保留（如 "Electrical Engineering or related field"），不要翻译成"电子相关"后丢失原句 |
| `skills_required` / `skills_preferred` | 页面 | 按要求强度词分流（§5） |
| `language_requirement` | 页面 | 只在明写时填；否则 `null` + 输出说明 |
| `nationality_requirement` | 页面 | 是否有国籍/签证限制；未写 → `null`（**不等于"无限制"**） |
| `school_requirement` | 页面 | 是否限定学校层次/名单 |
| `GPA_requirement` | 页面 | 原样字符串（"3.0/4.0"、"80 分以上"），不要换算 |
| `application_open` / `deadline` / `application_status` | 页面 | 走 `normalize_date.py`；开放状态需逐字段记录官方来源及核验日期，年份不明不要猜 |
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

输出同时给出 `deadline_type`，**五种状态不能混为一谈**：

| deadline_type | 含义 | 记录方式 |
|---|---|---|
| `fixed` | 单一确定日期 | `deadline: "2026-10-03"` |
| `range` | 报名窗口（如 9/20–10/5） | `deadline` 取**结束日**，`application_open` 取开始日；紧迫度以结束日为准 |
| `rolling` | 滚动/招满为止/随時受付 | `deadline: null`，输出标注"滚动招募" |
| `asap` | 尽快、无具体日期 | `deadline: null`，标注"尽快截止" |
| `flexible` | 可协商/弹性 | `deadline: null`，标注"时间可协商" |
| `tbd` | 未定/未公布 | `deadline: null`，标注"待公布" |
| `unknown` | 只有月份/季度精度，或无法解析 | `deadline: null` + 说明精度不足 |

补充规则：

- 年份不明 → 脚本返回 `year_unknown: true`，记录 `deadline: null`，
  改在输出里写"9月20日（年份未在页面标明）"。**不要瞎猜年份。**
- 含时间与时区（`2026-10-03 23:59 JST`）→ 保留原始值、日期部分正常化，
  在 `notes` 标注含时间/时区且**未做 UTC 换算**；不要伪造换算结果。
- 不把 `TBD` / `ASAP` / `Flexible` 当成滚动招募——它们语义不同，混用会误导用户
  （"待公布"和"随时可报"是完全不同的行动建议）。

---


## 6.1 Freshness：这个项目当前还能申请吗（必填判断）

**`deadline = null` 不等于"现在还能申请"** —— 这是真实 Benchmark 暴露的最严重问题（F01/F02）：
已经结束的 2026 赛季，因为截止日没抽出来，被当成当前机会推荐给用户。

抽取时必须给出 `freshness`（`scripts/normalize_date.py` 的 `freshness()` 已实现，可直接调用）：

| 状态 | 含义 | 能否进入 Recommended now |
|---|---|---|
| `open` | 截止日在今天之后 | ✅ |
| `likely_open` | rolling / asap / flexible（无固定截止） | ✅ |
| `unknown` | 判断不了（tbd、无 deadline 且周期不明） | ❌ → Worth verifying |
| `closed` | 周期已结束（去年、季节已过、活动已结束） | ❌ → excluded |
| `expired` | 截止日已过 | ❌ → excluded |
| `future` | 未来周期（如 2027 赛季），申请通常尚未开放 | ❌ → Worth verifying |

判断依据优先级：`deadline` → `deadline_type` → `event_end` → 周期年份/季节（title、cycle、event 日期）。

保守原则（产品可信度核心）：

> 宁可说"我找到了这个项目，但当前申请状态无法确认"，
> 也不要说"现在可以申请"。

## 6.1b deadline_type 的完整取值（含 evergreen / recurring）

| 取值 | 含义 | freshness |
|---|---|---|
| `fixed` / `range` | 固定日或区间截止 | 按日期 → open / expired |
| `rolling` | 官方持续接受，可能随时关闭 | likely_open |
| `evergreen` | 长期存在、没有报名周期（contributor / community / certification 路径） | **evergreen**（需"当前可参与"证据） |
| `recurring` | 周期性开放（每年/每届） | 按周期年份 → future / closed / recurring |
| `asap` / `flexible` | 尽快 / 可协商 | likely_open |
| `tbd` | 官方未定 | unknown |
| `unknown` | 无法判断 | unknown |

**evergreen ≠ verified open**：长期存在不等于今天能参与。只有页面给出"当前可参与"证据
（`evidence.application_status` 为 explicit 且状态为 open）时，才允许进入 actionable zone。

## 6.2 主推荐的证据前提（P0，来自 C/D/E 验收）

`recommended_now` 不是"看起来可以申请"，而是**有当天的官方观测**：

```json
"verification_status": "verified_official",
"application_status": "open",
"evidence": {
  "application_status": {"status": "explicit",
                         "source_url": "https://<official>/...",
                         "verified_at": "YYYY-MM-DD"},
  "deadline":           {"status": "explicit",
                         "source_url": "https://<official>/...",
                         "verified_at": "YYYY-MM-DD"}
}
```

- 缺 `evidence.application_status` → 无论页面看起来多合适，都只能进 **Worth verifying**。
- 结构化证据必须在**打开页面时**记录（`verified_at` 就是那天）；事后凭记忆补写等于伪造。
- C/D/E 三组真实验收的教训：候选 100% 没有这个结构 → 真实 gate 一条都认证不了，
  主推荐区等于不可达。这是协议要求，不是 gate 过严。

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
