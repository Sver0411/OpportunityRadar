<p align="center">
  <img src="assets/opportunity-radar-hero.svg" alt="OpportunityRadar — Personal Opportunity Intelligence" width="100%">
</p>

<p align="center">
  <strong>简体中文</strong> · <a href="./README.en.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/Sver0411/OpportunityRadar/actions/workflows/test.yml"><img src="https://github.com/Sver0411/OpportunityRadar/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="SKILL.md"><img src="https://img.shields.io/badge/Agent-Skill-8B5CF6" alt="Agent Skill"></a>
  <a href="scripts/"><img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="scripts/"><img src="https://img.shields.io/badge/runtime-stdlib_only-10B981" alt="Standard library only"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-111827" alt="MIT License"></a>
</p>

<p align="center">
  <b>Discover unknowns.</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>Verify reality.</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>Decide with evidence.</b>
</p>

---

> ### 机会的第一道门槛，不是竞争力，而是你是否知道它存在。
>
> OpportunityRadar 把一句模糊的「我接下来能做什么？」变成一组经过官方核实、符合真实约束、值得投入时间的机会决策。

它不是静态清单，也不是换了包装的关键词搜索。它是一套面向 Agent 的 **Personal Opportunity Intelligence**：理解人，展开搜索空间，发现未知选项，核实关键事实，判断资格与准备度，最后构建一组能执行、能解释、还能打开后续通道的 Opportunity Portfolio。

<br>

## 01 / 从链接列表，到决策系统

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>◈ DISCOVER</h3>
      <b>搜索用户没有说出口的可能性</b><br><br>
      从目标、阶段、兴趣、地区和约束出发，覆盖 13 类机会；除了主流路径，也主动寻找 Adjacent / Explore 方向。
    </td>
    <td width="33%" valign="top">
      <h3>◇ VERIFY</h3>
      <b>让每个重要结论都能追溯</b><br><br>
      聚合站负责发现，官方页面负责确认。开放状态、截止时间、资格要求和申请入口都经过证据门槛。
    </td>
    <td width="33%" valign="top">
      <h3>◆ DECIDE</h3>
      <b>把“适合”翻译成“现在怎么选”</b><br><br>
      分离 Match、Priority 与 Utility，在时间和预算约束下组织主线、桥接机会、低成本试错与长期选项。
    </td>
  </tr>
</table>

```text
你是谁        搜索空间        真实候选        官方证据        决策        机会组合        后续通道
  │              │               │               │            │             │               │
  └── profile ───┴── discover ───┴── verify ─────┴── judge ───┴── portfolio ┴── graph ───────┘
```

职业、科研、竞赛、教育、语言、技能发展、开源、兴趣、资助、活动、项目、创业与社群网络——系统可以跨 **13 类机会**建立搜索空间，也可以在用户明确限定后保持极窄的搜索边界。

<br>

## 02 / Evidence before confidence

一条机会不会因为“看起来不错”就进入主推荐。它必须穿过一组明确的门：

<table>
  <tr>
    <td><b>01<br>FRESHNESS</b></td>
    <td><b>02<br>CANONICAL</b></td>
    <td><b>03<br>EVIDENCE</b></td>
    <td><b>04<br>ELIGIBILITY</b></td>
    <td><b>05<br>RESOURCE</b></td>
  </tr>
  <tr>
    <td>当前周期仍然有效</td>
    <td>找到具体官方页面</td>
    <td>关键字段可以追溯</td>
    <td>没有明确硬性冲突</td>
    <td>时间与成本可执行</td>
  </tr>
</table>

因此，结果天然分成三个区域：

| | 状态 | 意义 |
|---:|---|---|
| `01` | **RECOMMENDED NOW** | 官方来源、近期状态与关键证据已核实，没有已知硬冲突。 |
| `02` | **WORTH VERIFYING** | 有价值，但开放状态、来源或资格仍有关键未知项。 |
| `03` | **CLOSED / EXCLUDED** | 已结束、已过期或存在明确冲突，并保留排除原因。 |

**Unknown stays Unknown.** 用户没说，不等于没有；页面没写，不等于满足。系统宁可保留不确定性，也不把缺失信息润色成一个自信的答案。

<br>

## 03 / 三层决策，而不是一个神秘总分

<table>
  <tr>
    <td width="33%" valign="top">
      <code>MATCH</code><br><br>
      <b>适不适合？</b><br>
      背景、兴趣、目标和机会要求之间的重合度。
    </td>
    <td width="33%" valign="top">
      <code>PRIORITY</code><br><br>
      <b>急不急？</b><br>
      开放状态、截止窗口与行动时机。
    </td>
    <td width="33%" valign="top">
      <code>UTILITY</code><br><br>
      <b>值不值得现在投入？</b><br>
      资格、准备度、产出、成本、时间与未来可选性。
    </td>
  </tr>
</table>

一个机会可以高度匹配，却因为每周需要 20 小时而不适合现在投入；也可以临近截止，却因为证据不足而只能进入待核实区。

OpportunityRadar 不向用户展示“83.7214 分”式的伪精确结论，也不预测录取概率。它给出 **High / Medium / Low / Unknown + 理由**。

<br>

## 04 / 机会不是终点，而是图上的一条边

OpportunityRadar 不只问“这个机会是什么”，还会继续问：**完成它以后，你手里多了什么证据，又打开了什么？**

```text
 GAP                  BRIDGE                  EVIDENCE                 UNLOCK
┌──────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ 真实协作  │  ───▶  │ 开源贡献计划  │  ───▶  │ Public PR    │  ───▶  │ Maintainer   │
│ 经历不足  │        │ 5h / week    │        │ Review history│        │ Internship   │
└──────────┘        └──────────────┘        └──────────────┘        └──────────────┘
```

Gap 必须来自真实机会要求或用户明确目标；Bridge 必须是实际发现的机会；Evidence 必须是可展示的产出；尚未找到的后续机会只记录类型，绝不伪造 ID。

这让推荐从“现在能参加什么”进化为：

> **现在做哪件事，能让未来的机会集合发生变化？**

<br>

## 05 / 输出是一组 Portfolio

OpportunityRadar 不机械返回 Top N，而是在用户有限的时间、预算和风险偏好下组合机会。

`NOW`　`BRIDGE`　`LOW-COST`　`HIGH-UPSIDE`　`LONG-TERM`　`EXPLORE`

角色达标才出现，不凑栏目。当已知投入超过每周预算时，系统直接报告资源冲突，而不是声称“已经对齐”。

一条完整推荐会回答：

```text
WHY          为什么它与你有关
ELIGIBILITY  哪些条件满足，哪些仍是 Unknown
OPEN NOW     当前周期是否有官方开放证据
READINESS    离真正开始还差什么
EFFORT       每周投入、准备复杂度与成本
PRODUCES     会留下什么可验证产出
UNLOCKS      这份产出可能打开什么
NEXT         此刻最值得执行的一步
```

<details>
<summary><b>展开查看一张推荐卡的示意</b></summary>
<br>

> ### Open Source Mentorship
> `RECOMMENDED NOW`　`PROBABLY ELIGIBLE`　`5H / WEEK`
>
> **WHY**　目标高度相关，可补真实协作经历并留下公开 PR。  
> **READINESS**　Minor preparation；需要一份英文项目简介。  
> **EVIDENCE**　官方项目页与当前申请入口已核实；时区要求仍需确认。  
> **UNLOCKS**　Public contribution → Maintainer / Internship / Research collaboration.  
> **NEXT**　先确认 mentor 与 issue 的匹配度，再决定是否占用本周预算。

<sub>格式示意，不代表当前存在或开放的真实机会。</sub>
</details>

<br>

## 06 / Ask like a human

不需要先填满画像，也不需要知道正确术语。一句话就能启动：

```text
我是视觉设计专业的学生，最近有什么能留下真实作品的项目？

我在做嵌入式开发，想转向 Edge AI，现在最值得补什么、参加什么？

我暂时不想找工作，想用每周 5 小时做点能打开新方向的事情。

我不知道下一步想做什么，帮我找几种差异足够大的低成本尝试。
```

系统先用已有信息开始，只在缺失项真的会改变结论时追问。本轮请求可以覆盖本轮搜索，但不会悄悄重写长期画像。

<br>

## 07 / Quick start

将仓库放进支持 Agent Skills 的宿主的 skills 目录。最终目录名应为 `opportunity-radar`。

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/Sver0411/OpportunityRadar.git \
  ~/.codex/skills/opportunity-radar
```

然后直接对 Agent 说：

```text
最近有什么真正适合我的机会？也找一些我可能完全没想到的方向。
```

完整发现流程需要宿主能够搜索网页并读取页面。确定性辅助脚本支持 Python 3.8+，只依赖标准库；没有 Python 时仍可按照 [`SKILL.md`](SKILL.md) 执行协议，但日期、去重、评分与状态管理会退化为人工判断。

<br>

## 08 / Under the hood

项目刻意保持轻量：**Skill 负责推理协议，References 负责知识边界，Scripts 负责确定性，Schemas 负责契约，Tests 负责防漂移。**

```text
SKILL.md
   ├── references/     搜索 · 来源 · 资格 · 排序 · Locale · 输出纪律
   ├── scripts/        Date · Dedupe · Score · Evidence · Utility · Graph · Portfolio
   ├── schemas/        Profile / Opportunity contracts
   └── tests/          Unit · Regression · Consistency · CLI smoke
```

| 核心 | 职责 |
|---|---|
| [`score.py`](scripts/score.py) · [`evidence.py`](scripts/evidence.py) | 硬约束、证据门槛、Match / Priority 与推荐分区。 |
| [`readiness.py`](scripts/readiness.py) · [`utility.py`](scripts/utility.py) | 判断离开始还有多远，以及现在值不值得投入。 |
| [`graph.py`](scripts/graph.py) · [`portfolio.py`](scripts/portfolio.py) | 连接 Gap → Bridge → Evidence → Unlock，并服从资源预算。 |
| [`presentation.py`](scripts/presentation.py) | 把结构化结论翻译成克制、清晰、不越界的用户表达。 |

共享枚举和规则集中在 [`scripts/common.py`](scripts/common.py)，Schemas、References 与实现之间的一致性由测试自动检查。完整架构与设计取舍见 [`DEVELOPMENT.md`](DEVELOPMENT.md)。

```bash
python3 scripts/preflight.py
```

预检依次执行编译、完整测试与 Skill package 校验。CI 覆盖 Python 3.8 和 Python 3.12。

<br>

## Design laws

```text
HARD CONSTRAINTS  >  MODEL VIBES
OFFICIAL EVIDENCE >  AGGREGATOR CLAIMS
UNKNOWN           =  UNKNOWN
ELIGIBILITY       ≠  READINESS
MATCH             ≠  PRIORITY  ≠  UTILITY
QUALITY           >  QUANTITY
```

机会会变化。行动前应重新打开官方页面确认；OpportunityRadar 不保证扫描整个互联网，也不保证申请结果。可选画像和状态保存在本地 `.opportunity-radar/`，辅助脚本不会主动上传这些文件。提交申请、发送邮件、注册账号和上传个人资料不在本 Skill 的执行范围内。

<br>

<div align="center">

**The next opportunity should not depend on whether you guessed the right keyword.**

[Read the protocol](SKILL.md) · [Architecture notes](DEVELOPMENT.md) · [MIT License](LICENSE)

</div>
