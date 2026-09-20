# Opportunity Taxonomy

13 个一级分类。每条 Opportunity 必须有 1 个 `primary_category`，可以有多个
`secondary_categories`，以及任意个自由 `tags`。

分类不是标签墙，而是**搜索空间的枚举清单**：Step 2 用它决定"这次要找哪几类"，
Step 4 决定"每类发哪些 query"。本文件给出每一类的**典型来源**与 **language-neutral
intent templates**；具体用哪种语言、本地用词怎么写，由 `references/locales/` 在运行时
按目标地区决定，不写死在本文件里。

> **职责分工**：本文件回答"有哪些类型的机会、典型来源是什么、通用的 search intent 是什么"。
> **"每个地区具体怎么搜、用哪些词"属于 locale 层**（`references/locales/`），
> 由目标地区在运行时决定，不在本文件里写死语言。
>
> 使用规则：不要只读某一类。开放性问题（"最近有什么适合我的"）至少覆盖 5 类。
> 类别是"发现入口"，不是"最终推荐"。同一件事可以从多个类进入，去重后自然收敛。

---

## 0. 分类 ID 表（与 schema、脚本共用，不可改名）

| id | 中文名 | 一句话范围 |
|---|---|---|
| `career` | 职业机会 | 实习、校招、兼职、企业学生计划 |
| `research` | 科研机会 | RA、本科科研、实验室、研究实习 |
| `competition` | 竞赛 | 学科/算法/AI/硬件/设计/商业比赛 |
| `education` | 升学与教育 | 考研保研、留学、夏校、交换 |
| `language` | 语言 | 语言考试、语言比赛、语言项目 |
| `skill_development` | 技能与资源 | 认证、训练营、云资源、学生开发包 |
| `open_source` | 开源 |  mentorship、贡献、赏金、社区计划 |
| `hobby` | 兴趣 | 摄影/无人机/音乐/游戏/创客等兴趣型机会 |
| `funding` | 资助 | 奖学金、grant、资源资助、减免 |
| `event` | 活动 | 大会、workshop、meetup、宣讲、开放日 |
| `project` | 项目 | 企业课题、capstone、共创、数据集项目 |
| `entrepreneurship` | 创业 | 创业赛、加速器、孵化、团队招募 |
| `networking` | 人脉与社区 | mentor、alumni、学生分会、专业协会 |

---

## 1. `career` — 职业机会

**子类：** 暑期实习 / 寒假实习 / 日常实习 / 长期实习 / 远程实习 / 海外实习 /
研究型实习 / 秋招 / 春招 / 提前批 / 补录 / Graduate Program / 管培生 /
校园兼职 / 技术兼职 / Freelance / 校园大使 / Developer Ambassador /
企业学生计划 / 企业人才培养计划

**典型 Tier A 来源：** 企业校招官网（`careers.*`、`*.com/campus`、`*.com/newgrad`）、
企业学生计划专页、大学就业中心官网、企业官方招聘页（多为当地语言版本）。

**Intent templates**（语言中立）：

```
<field> internship / intern
summer / winter / off-cycle <field> internship
<field> placement / co-op (UK-style year-long placement)
<field> graduate program / new grad / entry level
<organization> student program / campus recruiting
<field> research internship
<field> remote / part-time / freelance
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 聚合站（招聘平台、LinkedIn）只用于**发现**；投递入口与截止日必须回官网确认。
- "研究型实习"同时属于 `research`，默认 primary 取 `career`、`research` 进 secondary。
- 校招时间线强绑定毕业年份：不同地区按不同口径筛选（有的看毕业年度、有的看"应届"身份），
  具体判定规则见对应 locale 文件；没有毕业年份时不要把往届信息当成有效机会。

---

## 2. `research` — 科研机会

**子类：** Research Assistant / 本科科研 / 科研实习 / Summer Research / 实验室项目 /
企业研究院 / 教授招募 / 大学生科研计划 / 开放课题 / 研究训练计划 / 论文合作 /
Poster / Workshop / 学术项目 / Visiting Student / Research Internship

**典型 Tier A 来源：** 大学实验室官网、教授个人主页、院系研究项目/招募页面、
企业研究院（R&D）页面、学术组织官方公告（ACM/IEEE/SIG 等）。
学术域名可用于快速判断来源层级：`*.edu` / `*.ac.jp` / `*.ac.uk` / `*.edu.cn` / `*.uni-*.de` 等。

**Intent templates**（语言中立）：

```
<field> undergraduate research
<field> research assistant / RA position
summer research program <field>
<field> lab opening / lab recruiting students
professor <field> recruiting
<field> visiting student / research internship
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 教授直接招募通常没有正式招聘页，`official_url` 可以是实验室/教授页面，
  但必须在 `verification_status` 标注来源类型（个人页 vs 项目页）。
- "本科生能不能进实验室"是硬性条件，务必确认页面是否明确写了年级/学历范围。
- 不要因为"教授在做这个方向"就推断"在招人"。

---

## 3. `competition` — 竞赛

**子类：** 编程竞赛 / 算法比赛 / CTF / AI 比赛 / CV / NLP / LLM / Agent /
数据科学 / IoT / 嵌入式 / 电子设计 / FPGA / 芯片 / 机器人 / 无人机 / 无人车 /
数学建模 / Hackathon / 创新创业 / 商业案例 / 摄影 / 设计 / 视频 / Game Jam /
汽车 / 航空航天 / 农业科技 / 能源 / Maker

**典型 Tier A 来源：** 赛事官网、主办方官网（企业/Kaggle/学术会议）、
行业协会赛事页、大学赛队或教务公告。

**Intent templates**（语言中立）：

```
<topic> competition for students
<topic> challenge (open call)
<topic> hackathon / game jam
<topic> contest / award (design, hardware, case)
<topic> student prize
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 竞赛的价值差异极大：区分"有奖金/有评审/有公开作品集产出"与"纯报名制水赛"。
- 团队限制（`team_requirement`）常是硬门槛（是否允许跨校、是否需 3 人以上）。
- 报名截止 ≠ 作品提交截止，两者都要记录（`deadline` 与 `event_end`）。

---

## 4. `education` — 升学与教育

**子类：** 考研 / 保研 / 夏令营 / 预推免 / 调剂 / 直博 / Master / PhD /
Research Student / 海外硕士 / 海外博士 / 交换 / 联合培养 / 双学位 /
Summer School / Winter School / Visiting Student / 短期课程

**典型 Tier A 来源：** 大学院系官网（招生页、summer program 页）、
研究生院官网、国际处/交流办公室、官方夏校页。

**Intent templates**（语言中立）：

```
<field> summer school / winter school
<field> master / PhD program application
<field> exchange program / joint degree
<field> visiting student / research student
<field> short course
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 升学类信息年份耦合极强（招生年度 / 政策年度），务必写清"哪一届"；
  不要把往年的简章当成本年机会（各地区具体口径见 locale 文件）。
- 海外项目必须单独核对语言成绩与财政证明要求，二者常是硬性条件。

---

## 5. `language` — 语言

**子类：** JLPT / TOEIC / IELTS / TOEFL / GRE / GMAT / CET / TOPIK / 其他语言考试 /
考试报名 / 模考 / 语言比赛 / 翻译比赛 / 演讲比赛 / 语言奖学金 / 语言交换 /
短期语言项目

**典型 Tier A 来源：** 考试主办方官网（JLPT 官方、ETS、IELTS 官方、CET 教务）、
使馆/文化机构（JASSO、Goethe、Alliance Française）、语言学校官方页。

**Intent templates**（语言中立）：

```
<exam> test dates / registration
<language> competition / speech contest
<language> scholarship / exchange
<language> intensive course
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- **纯查询不触发本 skill**（"TOEIC 什么时候考试" → 直接答）。
  只有当用户问"我要不要考 / 考哪个对我有用"时才进入发现流程。
- 语言成绩常是其他机会的门槛：在 Mode D 中它是高频缺口项。

---

## 6. `skill_development` — 技能与资源

**子类：** AWS / Azure / GCP / Cisco / Red Hat / 技术认证 / 学生免费认证 /
Bootcamp / Workshop / Developer Training / 企业培养计划 / GPU Credit /
Cloud Credit / API Credit / 教育软件 / 学生开发包 / 开发板计划

**典型 Tier A 来源：** 云厂商学生计划页（GitHub Student Pack、AWS Educate 类页面）、
认证官方页、厂商开发者计划页。

**Intent templates**（语言中立）：

```
<vendor> student program / student pack
free certification for students <vendor>
cloud / GPU / API credits for students
developer training / bootcamp
dev board / hardware program
education software for students
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- "资源型机会"（credit、开发板、教育 license）常被忽略但即时可用，
  尤其适合 Mode B / Mode D。
- 明确写清申请门槛（是否需要学校邮箱、是否需要项目提案）。

---

## 7. `open_source` — 开源

**子类：** GSoC / Mentorship / 开源实习 / Contributor Program / Good First Issue /
Help Wanted / Bounty / Maintainer 招募 / Developer Community / RFC / Proposal /
Beta Program

**典型 Tier A 来源：** 项目官网 / GitHub 仓库文档（CONTRIBUTING、`good first issue` 标签）、
基金会官方页（如 GSoC 官方站）、项目 blog 的招募公告。

**Intent templates**（语言中立）：

```
open source mentorship program
good first issue <topic>
<project> contributors wanted
paid open source internship
bounty <topic>
beta / early access program <topic>
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 开源机会的**时间线极强**（GSoC 类项目一年一轮，提案期短），
  必须确认本年度是否在报名窗口，过期就不要当推荐。
- "有 good first issue"≠"有 mentorship 名额"。

---

## 8. `hobby` — 兴趣

**子类：** 摄影 / 无人机 / 汽车 / 航空 / 游戏 / Game Jam / 音乐 / 写作 /
设计 / 视频 / 动漫 / Maker / 3D 打印 / 户外 / 创客活动

**典型 Tier A 来源：** 厂商社区官方活动页（相机/无人机/汽车品牌）、
展会官网、兴趣协会、Maker Faire 类活动官网、赛事官网。

**Intent templates**（语言中立）：

```
<hobby> competition / contest
<hobby> community event / meetup
<brand> student program
<hobby> ambassador / creator program
maker / build challenge <hobby>
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 兴趣类必须**真正参与搜索**，不是 profile 的装饰字段。
  在 Mode B 中它是一等公民。
- 兴趣类机会常常也有真实价值（作品集、社群、装备资助），
  在 `value` 里用 `interest_value` / `portfolio_value` 体现，而不是硬塞 career 价值。

---

## 9. `funding` — 资助

**子类：** 国家奖学金 / 学校奖学金 / 企业奖学金 / 助学金 / Research Grant /
Travel Grant / Conference Grant / 创业基金 / 学生基金 / 交流资助 / 比赛资助 /
设备资助 / GPU 资源 / 云资源 / 学费减免

**典型 Tier A 来源：** 学校奖学金管理页、基金会官网、会议官网的 travel grant 页、
企业 CSR/奖学金页、政府/机构资助页。

**Intent templates**（语言中立）：

```
<field> scholarship / fellowship
<field> research grant
<field> travel grant / conference grant
student fund / project funding
equipment / cloud / GPU funding
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 资助类常与其它类重叠：会议 travel grant 会随 `event`、`research` 一起出现，
  此时按"用户最可能从这个入口找"决定 primary。
- 金额、名额、是否需参赛/参会证明都要记录，缺则 `null`。

---

## 10. `event` — 活动

**子类：** 技术大会 / Developer Conference / 学术会议 / Workshop / Seminar /
Meetup / Webinar / Open Day / Career Fair / 校招宣讲 / 实验室开放日 / 社区活动

**典型 Tier A 来源：** 大会官网、大学官网公告、企业开发者大会页、
学会会议页、实验室 open day 公告。

**Intent templates**（语言中立）：

```
<topic> conference (student tickets)
developer conference registration
<field> open day / lab open day
career fair / job fair <field>
seminar / webinar / workshop <field>
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 活动类门槛低、时效强：把"报名截止 / 举办日期 / 是否免费 / 是否线上"写清楚。
- 学生票、免费票、志愿者名额常常是真实入口，值得单独搜。

---

## 11. `project` — 项目

**子类：** 企业真实课题 / 企业命题 / Open Innovation / Capstone /
学生联合项目 / 公益技术项目 / Build Challenge / Hardware Build /
Research Prototype / 产品共创 / 数据集项目

**典型 Tier A 来源：** 企业开放创新页、比赛命题页、学校 capstone 合作公告、
NGO/公益组织技术项目页、数据集官方项目页。

**Intent templates**（语言中立）：

```
open innovation challenge <topic>
company capstone project <field>
build challenge / hardware build
civic tech / non-profit project
dataset / open data project
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 项目类最适合"想积累作品但不想被长期绑定"的用户（Mode B）。
- 交付物是否可公开（能否进作品集）是重要判断点，能查到就写进 `value.portfolio`。

---

## 12. `entrepreneurship` — 创业

**子类：** Startup Competition / Accelerator / Incubator / 校园创业 / 创业基金 /
创业训练营 / Demo Day / 创业团队招募 / 联合创始人招募 / 企业创新挑战

**典型 Tier A 来源：** 孵化器/加速器官网、创业赛官网、大学创业中心、
政府/园区创业扶持页。

**Intent templates**（语言中立）：

```
student startup competition
university accelerator / incubator application
startup founders program students
co-founder wanted (student)
demo day <field>
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 与 `funding` / `competition` 高度重叠；区别在于"是否以组建/经营团队为核心"。
- 对没有团队的用户，`team_requirement` 与"是否可单人报名"是决定性问题。

---

## 13. `networking` — 人脉与社区

**子类：** Mentor Program / Alumni Mentorship / Industry Mentor /
Developer Community / Research Community / Student Chapter / Campus Lead /
专业协会 / 技术社区 / 学生组织

**典型 Tier A 来源：** 企业 mentor 计划页、校友会/学校官方页、学生分会官方页、
专业协会（ACM/IEEE/学会）学生会员页、社区官方 program 页。

**Intent templates**（语言中立）：

```
<organization> mentorship program
student chapter <society>
campus ambassador / campus lead program
alumni mentoring program
<field> community / professional association
```

> 用 `references/locales/generic.md` 的规则把这些 intent 本地化到目标地区语言；具体的当地用词见对应的 locale 文件（如 `jp.md` / `cn.md` / `de.md`）。

**注意：**
- 这类机会门槛最低、发现难度最高，是 Mode C（未知机会）的主力。
- 报名成本低 → 适合作为"低风险入口"推荐给还没有明确方向的新用户。

---

## 14. 重叠消解表（保持分类一致性）

同一件事可以从多个入口发现。为避免不同会话分类漂移，按下表定默认主类：

| 具体机会 | primary | secondary |
|---|---|---|
| GSoC | `open_source` | `career`, `skill_development`, `funding`, `networking` |
| 企业暑期实习 | `career` | — |
| 企业研究型实习 | `career` | `research` |
| 教授实验室招募本科生 | `research` | — |
| Game Jam | `competition` | `hobby`, `project` |
| 摄影/设计大赛 | `competition` | `hobby` |
| Maker Faire 参展 | `event` | `hobby`, `project` |
| 云厂商学生 credit | `skill_development` | `funding` |
| 会议 Travel Grant | `funding` | `event`, `research` |
| 企业命题挑战赛 | `competition` | `project`, `career` |
| 校园大使 | `career` | `networking` |
| 学生分会 / mentor 计划 | `networking` | `skill_development` |
| 创业训练营 | `entrepreneurship` | `skill_development`, `funding` |
| 夏校 / Summer School | `education` | `research`（研究型时） |
| 学生免费认证 | `skill_development` | `career` |

`tags` 用自由短标签补充检索维度，例如 `esp32`、`tinyml`、`remote`、`paid`、
`beginner-friendly`、`portfolio-output`。标签数量控制在 3–8 个。

---

## 15. 反模式

- ❌ 只查 `career` 然后把结果包装成"综合推荐"。
- ❌ 把 `hobby` 当作"用户随便填的字段"而跳过搜索。
- ❌ 用分类名单凑数：13 类各来一条，用户看不完也用不上。
- ❌ 给"考试报名时间"这类纯查询打上 `language` 类当成机会推荐。
- ❌ 一条机会挂 5 个 primary 类。primary 只有一个。

---

## 14. 职业阶段含义（V3：扩展现有类别，不新增一级分类）

同一个 category 对不同人生阶段意味着完全不同的东西。下面只做**扩展**，不动 13 个一级分类。

### career
- 学生：internship / campus recruiting / graduate program / student ambassador
- 职场：experienced hire / lateral move / internal mobility / referral / remote role /
  international role / contract / freelance / consulting / fractional role /
  senior / staff / lead / management role / specialist role

### education
- 学生：undergraduate / master / PhD / exchange / summer school
- 职场：part-time master / professional master / MBA / EMBA / executive education /
  certificate programme / career conversion programme / company-sponsored study /
  short-term overseas programme
- 注意：`education_level` 是**申请人当前学历门槛**；项目授予的学位写 `program_degree`。

### research
- 学生：undergraduate research / RA / summer research / lab opening
- 职场：industrial research / industry-academia collaboration / research consortium /
  technical committee / standards participation / whitepaper collaboration /
  patent collaboration / visiting researcher / research fellowship

### networking
- 学生：student society / mentor programme / alumni / conference
- 职场：industry association / professional committee / expert network / mentor programme /
  founder community / technical community / conference speaker / community organizer /
  professional society

### entrepreneurship
- 学生：startup competition / campus incubator / idea contest
- 职场：accelerator / incubator / startup grant / founder programme / cofounder matching /
  venture studio / entrepreneur-in-residence / open innovation / corporate venture programme

### 产出视角（不是新分类，是 outcome facet）
同一个机会可以同时是 `competition` 且 `portfolio: High`、`skill: High`、
`financial: Low` —— **"没工资"不等于"没价值"**。见 schema 的 `outcomes`。
