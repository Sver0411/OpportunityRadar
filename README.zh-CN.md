<div align="center">

**简体中文** | [English](./README.md)

# 📡 OpportunityRadar

**发现那些你根本不知道该搜什么的机会。**

[![tests](https://github.com/Sver0411/OpportunityRadar/actions/workflows/test.yml/badge.svg)](https://github.com/Sver0411/OpportunityRadar/actions/workflows/test.yml)
[![license](https://img.shields.io/badge/license-MIT-3DA639)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](#-辅助脚本)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-534AB7)](#-安装)
[![runtime deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen)](#-辅助脚本)

把一句“最近有什么适合我的机会？”变成 13 步协议 🎯
**理解你 → 展开搜索空间 → 发现 → 验证 → 筛选 → 排序 → 探索相邻方向**

覆盖 13 类机会 🗂️ · 回官方来源验证 🛡️ · 按目标地区选语言 🌏 · 自动去重 🧹 · 判定可解释 📝

*面向支持 Agent Skills 且具备联网能力的宿主 · 不注册、不上云、无遥测 🏠*

</div>

---

## 🚀 快速开始

```bash
# 1) 安装 —— 目标目录名必须是 opportunity-radar
git clone https://github.com/Sver0411/OpportunityRadar.git opportunity-radar
cp -r opportunity-radar ~/.workbuddy/skills/opportunity-radar   # 或换成你所用 Agent 的 skills 目录
```

然后直接提问即可。OpportunityRadar 自身不需要额外 API Key
（宿主的联网搜索能力可能有它自己的配置）：

```text
我是大三 CS 学生，关注安全和开源，这学期有什么值得做的？
```

任何专业、任何地区都适用 —— 用哪些语言搜、适用哪些规则，都来自**你的画像**，
而不是 Skill 里的示例：

```text
生物学本科生，想找暑研和资助，欧洲优先。
设计专业，喜欢游戏和 3D，想找比赛和作品集项目，远程/全球都行。
我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？
```

想先验证确定性脚本那一层？

```bash
python3 -m unittest discover -s tests -t tests        # 完整单元测试，只用标准库，不联网
python3 scripts/normalize_date.py "9月20日-10月5日" --default-year 2026 --now 2026-09-14
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --format text
```


---

## 🧭 为什么需要 OpportunityRadar

普通搜索回答的是错误的问题。让一个通用 Agent“帮我找几个实习”，它会搜 `IoT internship`，
返回几个链接，然后停下。但难点从来不在搜索，而在于**用户不知道该搜什么**。

OpportunityRadar 用一套协议（而不是一段 Prompt）补上这个缺口：

| 环节 | 裸 Agent | OpportunityRadar |
|---|---|---|
| 范围 | 实习 / 工作 | 13 类机会，含科研、开源、资助、兴趣、社区 |
| 查询 | 用户的字面词 | 按专业族推导的搜索矩阵（更专 → 同层 → 相邻 → 可迁移） |
| 语言 | 只搜英文 | 按目标地区决定语言：优先当地语言，英文只在国际召回有增益时补充 |
| 配比 | 全是直接相关 | 70% 直接 / 20% 相邻 / 10% 可迁移且意想不到 |
| 来源 | 排名靠前的就用 | Tier A–D 分级，只有官方来源才能确认事实 |
| 资格 | 猜一个 Yes/No | 五级判定 + 决定性依据 |
| 去重 | 不处理 | URL / 标题 / 机构 / 周期聚类，并报出冲突 |
| 排序 | 搜索引擎顺序 | Match 与 Priority 分离，带截止紧迫度 |
| 记忆 | 每次都重来 | 本地 seen / saved / ignored 状态与变化检测 |
| 缺口 | 泛泛的学习建议 | 从真实机会反推出的要求频次 |

---

## 🎁 能发现什么

| 类别 | 例子 |
|---|---|
`career` | 暑期/寒假/远程/海外实习、研究型实习、校招、Graduate Program、兼职、校园大使
`research` | Research Assistant、本科科研、实验室招募、Summer Research、Visiting Student、论文合作
`competition` | 编程、算法、CTF、AI/CV/NLP/LLM、数据科学、IoT、嵌入式、FPGA、机器人、无人机、数学建模、Hackathon、设计、商业案例
`education` | 考研保研、夏令营、交换、联合培养、双学位、短期课程
`language` | JLPT / TOEIC / IELTS / TOEFL / GRE / CET / TOPIK、语言比赛、语言奖学金、语言交换
`skill_development` | 技术认证、学生云/GPU/API 资源、Bootcamp、开发者培训、开发板计划
`open_source` | GSoC 类项目、mentorship、贡献者计划、good first issue、Bounty、Beta Program
`hobby` | 摄影、无人机、汽车、航空、游戏、Game Jam、音乐、写作、设计、Maker、3D 打印
`funding` | 奖学金、科研/差旅/参会资助、创业基金、设备与云资源、学费减免
`event` | 技术大会、开发者大会、学术会议、Workshop、Meetup、开放日、Career Fair
`project` | 企业命题、开放创新、Capstone、公益技术项目、Build Challenge、数据集项目
`entrepreneurship` | 创业赛、加速器、孵化器、校园创业、Demo Day、联合创始人招募
`networking` | 导师计划、校友 mentorship、学生分会、专业协会、社区负责人

完整的子类清单、典型来源与多语言 query 模板见
[`references/opportunity-taxonomy.md`](references/opportunity-taxonomy.md)。

---

## ⚙️ 工作原理

13 个步骤，没有捷径（“搜一次然后给结果”不算这套协议）：

```
画像 → 目标地区 → 语言计划（locale）→ 搜索空间 → query 矩阵 → 发现候选
→ 找到官方来源 → 验证 → 结构化 → 去重 → 资格判断 → 排序
→ 探索相邻方向 → 返回最值得看的
```

完整的分步协议在 [`SKILL.md`](SKILL.md)；其中三条规则决定了全部设计：

- **硬条件优先于模型判断。** 页面写明“仅限博士”而用户是本科，结论就是不符合资格，
  即使模型更想给出肯定答案。语义判断只负责 `related field`、经验相关性这类模糊表述。
- **画像缺失 ≠ 不满足。** 渐进式画像本来就会有缺项；用户没填语言成绩是 `Unknown`，不是
  不符合。只有用户**明确表示**不具备时才会给出否定结论。
- **只有 explicit 证据才能淘汰你。** 每个关键字段都带 `evidence.status`：
  `inferred` / `unknown` 的值不能用来判不符合，只能把结论降为 `Unknown` 交语义复核。
  完全不带 `evidence` 的旧格式记录仍可判断（legacy 模式），但结论封顶在 `Probably Eligible`。
- **页面对资格什么都没写 → `Unknown`，不是"大概率符合"。**
- **已验证优先于看起来完整。** 事实只从官方来源断言，未确认的一律标注出来。

---

## 📦 安装

Skill 包就是一组文件。把本仓库内容复制到宿主 Agent 的 skills 目录下，
**目录名必须是 `opportunity-radar`**（要与 `SKILL.md` frontmatter 里的 `name` 一致）：

```bash
# 目标目录名必须是 opportunity-radar
git clone https://github.com/Sver0411/OpportunityRadar.git opportunity-radar
cp -r opportunity-radar ~/.workbuddy/skills/opportunity-radar      # WorkBuddy
cp -r opportunity-radar ~/.codebuddy/skills/opportunity-radar      # CodeBuddy
cp -r opportunity-radar ~/.claude/skills/opportunity-radar         # Claude Code
cp -r opportunity-radar <你的项目>/.<agent>/skills/opportunity-radar # 项目级安装
```

无需安装依赖。辅助脚本只依赖 Python 3.8+ 标准库。

GitHub 仓库名是 `OpportunityRadar`，但安装后的 skill 目录名必须是 `opportunity-radar`。

### 环境要求

| 能力 | 用途 | 缺失时 |
|---|---|---|
| 联网搜索 | 发现机会、当地语言查询 | 无法进行发现，Skill 会明确说明并停止 |
| 页面抓取 / 浏览器 | 回官方来源确认事实 | 事实标记为未经确认 |
| Python 3.8+ | 确定性辅助脚本（`scripts/*.py`） | 走 Protocol-only 模式：同样 13 步，人工判断，不声称确定性结果 |
| 文件写入 | 本地状态、JSON 产物 | 跳过状态功能，其余功能不受影响 |
| 宿主 Memory | 复用已知画像 | 只问一次，或缓存到 `.opportunity-radar/profile.json` |

---

## 💡 使用示例

### 示例 1 —— 常规发现（美国 CS 学生，安全 + 开源）

```text
我是大三 CS 学生，关注安全和开源，这学期有什么值得做的？
```

预期行为：从画像解析目标地区（`us` → `en-US`，加载 `us.md`）；用画像里的兴趣扩词
（security / open source，而不是固定的专业词表）；覆盖多个类别（竞赛、开源、实习、资助、项目）；
返回一个带资格判定、截止日与官方来源的短清单。

### 不同的人，得到完全不同的计划

同一套协议，因为语言、类别与判据都来自运行时画像，不同的人会得到不同的搜索计划：

| 画像（见 `examples/profiles/`） | 解析出的语言 | 加载的区域知识 | 主力类别 |
|---|---|---|---|
| **CS** —— 安全、开源 · 美国 / 远程 | `en-US` | `generic.md`、`us.md` | 开源、竞赛、实习 |
| **生物** —— 实验 + 数据分析 · 德国 / 荷兰 | `de-DE`、`nl-NL`（+ `en`） | `generic.md`、`de.md` | 科研、资助、活动 |
| **设计** —— Figma / Blender、游戏 · 法国 / 全球 | `fr-FR`（+ `en`） | 仅 `generic.md`（还没有 `fr.md`，照常工作） | 竞赛、项目、兴趣 |
| **IoT** —— C / ESP32 · 日本 / 中国 / 远程 | `ja-JP`、`zh-CN`（+ `en`） | `generic.md`、`jp.md`、`cn.md` | 实习、竞赛、科研 |

最后一行是**受支持的场景之一，不是默认用户**。可以自己跑一下：

```bash
python3 scripts/locales.py --profile examples/profiles/design-student.example.json
```

### 示例 2 —— 不找工作

```text
我不想找工作，就是最近有点闲，有什么值得做的吗？
```

预期行为：降低求职/升学类权重，转向竞赛、开源、项目、技能计划、活动与兴趣机会，
不会继续无脑推实习。

### 示例 3 —— 能力反推

```text
我想以后做 Embedded AI，但是不知道现在应该做什么。
```

预期行为：先搜**真实**的 Embedded AI 机会，统计它们真正要求什么，再去找能补上这些要求的
竞赛/项目/开源/技能计划 —— 而不是输出一份泛泛的“学 C++ / 学 RTOS”清单。

### 示例 4 —— 缺口分析

```text
我现在缺什么？为什么很多机会我都申请不了？
```

预期行为：报告“本次扫描到的机会”里的要求频次，例如“扫描到的 23 条里，RTOS 出现在 9 条”，
并为每个缺口配可参与的机会。始终标注样本量，绝不宣称这是全市场统计。

输出格式的完整走查（虚构数据）见
[`examples/discovery-output.example.md`](examples/discovery-output.example.md)。

---

## 🧱 项目结构

```
OpportunityRadar/
├── SKILL.md                          # 协议核心：触发规则、模式、13 步、规则、自检
├── README.md  README.zh-CN.md        # English / 简体中文
├── DEVELOPMENT.md                    # 设计决策、验收场景、QA 清单
├── LICENSE  .gitignore
├── references/                       # 按需加载，一个文件一个关注点
│   ├── opportunity-taxonomy.md        # 13 类、来源、多语言 query 模式
│   ├── search-strategy.md             # 搜索矩阵、扩展规则、70/20/10、预算
│   ├── profile-building.md            # 渐进式画像、何时该问、记忆复用
│   ├── trust-policy.md                # Tier A–D、发现 vs 确认、新鲜度
│   ├── extraction-policy.md           # 字段规则、证据状态、反幻觉
│   ├── eligibility.md                 # 硬条件顺序、五级判定、缺失数据处理
│   ├── ranking.md                     # Match vs Priority、权重、覆盖度、价值评估
│   ├── output-format.md               # 输出模板、长度纪律、JSON 产物
│   ├── state-and-feedback.md          # seen/saved/ignored、变化检测、缺口话术
│   └── locales/                       # 区域知识，只在目标地区需要时加载
│       ├── README.md                  # 加载模型：generic 常加载，国家文件按需
│       ├── generic.md                 # 地区 → 语言解析、未收录地区、动态检测
│       ├── cn.md  jp.md  us.md  uk.md de.md
├── schemas/
│   ├── profile.schema.json            # 用户画像（JSON Schema draft 2020-12）
│   └── opportunity.schema.json        # 机会记录（含 evidence 证据结构）
├── scripts/                          # 确定性辅助脚本，纯标准库、不联网
│   ├── common.py                      # 单一事实来源：枚举、URL、ID、contract 校验
│   ├── locales.py                     # 目标地区 → 搜索语言 + 需要加载哪些区域文件
│   ├── normalize_date.py              # 截止日 → ISO + deadline_type + 紧迫度
│   ├── dedupe.py                      # 周期感知聚类、冲突报告
│   ├── score.py                       # 资格预判、Match/Priority 分项
│   └── state.py                       # seen/saved/ignored、变化检测、反馈
├── examples/                         # 虚构数据，用于演示格式与脚本
│   ├── profiles/                      # 四个不同画像（CS / 生物 / 设计 / IoT-日本）
└── tests/                            # unittest 测试（标准库；jsonschema 可选）
```

> `examples/` 下所有数据**均为虚构**，每个文件内都有声明。不要把其中的机构与事实当作真实机会引用。

---

## 🔧 辅助脚本

确定性的事情交给代码而不是模型：日期、去重、基础评分、状态。每个脚本都能独立运行。

### `normalize_date.py` —— 截止日与时间窗口

```bash
python3 scripts/normalize_date.py "Sep 20 - Oct 5, 2026" --now 2026-09-14
```

```json
{
  "iso": "2026-09-20",
  "end": "2026-10-05",
  "deadline_type": "range",
  "urgency_days": 21,
  "days_until_start": 6,
  "days_until_end": 21,
  "year_unknown": true,
  "notes": [
    "原文未写年份，按 --default-year 2026 填充（请复核）",
    "紧迫度以区间截止端点为准（urgency_days = days_until_end）"
  ]
}
```

关键行为：`rolling` / `asap` / `flexible` / `tbd` 是**四种不同状态**（“随时可报”和“日期未公布”
对应完全不同的行动建议）；年份缺失会如实报告，绝不编造；时间与时区原样保留，不做虚假的 UTC 换算。
26 个示例输入见 [`examples/dates.example.txt`](examples/dates.example.txt)。

### `dedupe.py` —— 去重

```bash
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --format text
```

```text
input=15  clusters=13  removed=2

[c001] size=3 canonical=nagi-robotics-2027-summer-internship-program
  title: 2027 Summer Internship Program
  org  : Nagi Robotics, Inc.
  - merged in: nagi-robotics-summer-internship-2027
  - merged in: nagi-robotics-2027-internship
  ! conflict deadline: 2026-10-03(A,C) vs 2026-10-17(C)
```

三重防护避免过度合并：**周期守卫**（同一官方 URL 常被多年复用，2026 与 2027 保持独立）、
**保守的 URL 规范化**（只删 `utm_*` 与明确点击追踪参数，path 保留大小写）、
**聚类一致性检查**（阻止 A~B、B~C 却把 A 与 C 并到一起）。来源之间的冲突会被报出，
而不是静默选择。

### `score.py` —— 资格预判与排序分项

```bash
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --output /tmp/clusters.json
python3 scripts/score.py --profile examples/profiles/cs-student.example.json \
                         --opportunities /tmp/clusters.json --today 2026-09-14 --format table
```

```text
| # | 机会 | 类别 | Match | 紧迫 | Priority | 档 | 资格 | 判定来源 |
|---|---|---|---|---|---|---|---|---|
| 1 | Atlas Open Source Mentorship Program | open_source | 78 |  | 78 | Medium | Unknown | hard_constraint |
| 2 | Mira Design Foundation Student Award | competition | 79 | 35 | 72 | Medium | Eligible | hard_constraint |
| 3 | Northstar Labs Security Research Internship | career | 72 | 50 | 69 | Medium | Unknown | hard_constraint |
| 4 | Lumen Global Business Case Challenge | competition | 74 | 35 | 68 | Medium | Probably Eligible | hard_constraint |
| 5 | Nagi Robotics Robot Hackathon | competition | 73 | 35 | 67 | Medium | Eligible | hard_constraint |
… 共 12 条入选、1 条被排除
```

示例批量刻意横跨 5 个地区与 6 种机会类型（全球/远程、美国、欧洲、中国、日本），
这样确定性逻辑是在一个混合世界上面被检验的，而不是只跑某个国家的实习。

其中几点：

- **`Eligible` 与 `Probably Eligible` 的区别**：前者的每项硬条件都带 `evidence.status: explicit`；
  后者完全没有 `evidence` 结构（旧格式），因此结论封顶。
- **`Unknown`**：Northstar 那条需要画像里一个以另一种形式存在的字段（毕业窗口），
  OSS mentorship 那条则根本没写资格条件 —— 两者都不会被当成"大概率符合"。
- 被排除的那条是届别冲突（要求 `2028-03` 毕业、画像为 `2028-05`）：代码、references 与 README
  对"无歧义的枚举/日期冲突 = `Ineligible`"是一致的。

### `state.py` —— 本地记忆

```bash
python3 scripts/state.py init
python3 scripts/state.py mark-seen --input .opportunity-radar/last-run.json
python3 scripts/state.py feedback saved --id <id> --category competition --tags robotics
python3 scripts/state.py list --status saved
python3 scripts/state.py suggest
```

变化检测跟踪 8 个字段（`deadline`、`application_open`、`cost`、`compensation`、
`education_level`、`student_year`、`language_requirement`、`official_url`）。
只追加 `utm_*` 参数**不算**变化。`suggest` 只输出权重建议，永远不会改写画像。

### `locales.py` —— 运行时决定搜索语言

**用哪些语言搜、要加载哪些区域知识**，都从画像推导，不来自固定清单：

```bash
python3 scripts/locales.py --profile examples/profiles/biology-student.example.json
```

```text
regions: germany, netherlands
primary locales: de-DE, nl-NL
optional locales: en
load files:
  - references/locales/generic.md
  - references/locales/de.md
```

英文只在国际召回有增益时才加。没有区域文件的地区走通用规则，未收录的地区回落到
通用规则 + 英文：

```bash
python3 scripts/locales.py --countries Kenya      # regions: remote（未收录: Kenya）→ en，仅 generic
python3 scripts/locales.py --detect "https://www.univ-xyz.fr/offres"   # fr-FR ← 域名后缀
python3 scripts/locales.py --detect "研究室のインターン募集"              # ja-JP ← 含假名
python3 scripts/locales.py --list-locales         # 收录 24 个地区，其中 5 个有专门文件
```

### `common.py` —— 共享基础

枚举、URL 规范化、ID 生成与轻量 contract 校验都放在这里，
让 `dedupe.py`、`score.py`、`state.py` 不可能各自漂移。

```bash
python3 scripts/common.py --url "https://www.Example.com/Path/To/Page/?b=2&utm_source=x&a=1"
# example.com/Path/To/Page?a=1&b=2

python3 scripts/common.py --validate examples/opportunity.batch.example.json
# checked=8 errors=0
```

---

## 🛡️ 来源验证与可信度

| 级别 | 例子 | 用途 |
|---|---|---|
| **A** | 官方项目/企业/大学/政府/实验室/赛事官网 | 可作为事实依据 |
| **B** | 学校就业中心、学术组织、行业协会、官方合作机构 | 可确认；与 A 冲突时以 A 为准 |
| **C** | LinkedIn、招聘平台、竞赛/活动聚合站、技术社区 | **仅用于发现** |
| **D** | 博客、论坛、个人帖子、转载、非官方文章 | 只用于发现与线索 |

规则：C/D 负责发现，A/B 负责确认。第三方说 9/20、官方说 9/25 时，采用官方日期并写明差异。
找不到官方来源时直接写“未找到官方确认来源”——**绝不编造链接**。新鲜度按类型跟踪
（竞赛 14 天、实习 30 天、奖学金 60 天、常年开放资源 180 天）。

---

## 🔒 本地状态与隐私

```
.opportunity-radar/
├── profile.json     # 画像缓存（宿主没有 Memory 时才需要）
├── seen.json        # 首次/最近出现时间、被跟踪字段哈希、变更日志
├── saved.json       # interested / saved / applied
├── ignored.json     # ignored / not_relevant
└── last-run.json    # 上一轮结构化产物
```

数据全部留在本地文件系统，脚本不发起任何网络请求。该目录已在 `.gitignore` 中忽略，且完全是可选的
—— 没有它 Skill 也能完整工作。不存储凭据、联系方式或文档。

申请与联系动作（提交表单、发邮件、报名、上传个人信息）不属于本发现流程，始终由用户自己完成。

---

## ⚠️ 已知限制

- **需要具备联网能力的宿主。** 没有联网时 Skill 会明确说明并停止，而不是靠猜。
- **没有全市场统计。** 缺口分析描述的是本次实际扫描到的样本，并每次都注明这一点。
- **仍需要判断力**：`related field` 类专业资格、模糊重复、价值评估仍需模型参与；
  脚本提供的是确定性信号，不是结论。
- **天然时效性。** 依赖某条结果前，请先复核 `last_verified`。
- **区域知识深度不均**：有专门文件的是 `cn` / `jp` / `us` / `uk` / `de`；其他地区走通用规则 +
  页面语言动态检测，能用，但更依赖直接读官方页面。
- **不做自动投递。** 只负责发现、验证、判断与解释。

---

## ✅ 测试

```bash
python3 -m unittest discover -s tests -t tests
```

使用标准库 `unittest`；`jsonschema` 是可选的，仅用于 Schema 元校验与正/反向用例。
测试覆盖：日期语义、URL/ID 契约、去重防护、资格判定权威顺序、缺失数据策略、状态流转、
Schema 契约，以及跨文件一致性（枚举与权重必须与 `scripts/common.py` 一致）。

维护说明、设计决策与联网验收场景见 [DEVELOPMENT.md](DEVELOPMENT.md)。

---

## 📄 许可证

MIT —— 见 [LICENSE](LICENSE)。
