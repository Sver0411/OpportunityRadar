# Output format examples

> ⚠️ **格式示意，数据全部为虚构。** 这些示例用于说明 `references/output-format.md` 的排版与信息密度，
> 不代表任何真实机会。真实运行时必须联网搜索并回官方来源验证。
>
> 故意给出**两个不同的人**，避免让单一画像看起来像"默认用户"：
> 一个 CS/安全方向、目标美国 + 远程；一个设计方向、目标法国 + 全球。
> 注意两者得到的语言、类别与机会类型完全不同 —— 这正是 OpportunityRadar 应有的行为。

---

## Example A — CS student, security + open source, US / remote

输入（对应 `examples/profiles/cs-student.example.json`）：

```text
I'm a third-year CS student into security and open source. What's worth doing this semester?
```

Locale 计划（由目标地区推导，不是固定语言清单）：

```text
regions: us              primary locale: en-US        secondary: （无）
load files: references/locales/generic.md, references/locales/us.md
```

输出：

> 按「CS 大三 + Python/Linux/Git + 关注 security/open source，目标美国 + 远程」搜了一轮，
> 覆盖 竞赛 / 开源 / 实习 / 资助 / 项目 5 类，筛出 5 条值得看的（含 2 条你可能不会想到去搜的方向）。
> 画像里的 GPA 已填，毕业时间已填，所以实习类可以给出确定判断。

**1. Northstar Labs Security Research Internship（美式实习）**
类型：Career / Security · 12 周全职，Austin，有薪
为什么适合你：
- 接受本科（页面明确 `undergraduate`）
- 硬性技能 Python / Linux 与你的技能栈匹配
- 毕业窗口 `Dec 2027 – Aug 2028` 与你的 2028-05 相符
资格：Eligible（GPA 3.7/4.0 ≥ 要求的 3.0/4.0）
截止：2026-11-01
注意：△ 页面要求 `must be legally authorized to work in the US`，你标注为美国公民 → 无影响
价值：Career High / Portfolio Medium / Research Medium
官方来源：https://northstar-labs.example/careers/security-intern-2027

**2. Atlas Open Source Mentorship Program（远程，门槛低）**
类型：Open Source / Skill Development · 约 5 h/周，远程，有津贴
为什么适合你：
- 面向新贡献者，与你的开源目标直接对应
- 产出公开 PR → 可写进简历
- 明确 remote
资格：Eligible（无学历/年级限制 `.any`）
截止：滚动招募（无固定截止）
注意：△ 页面只写 `English (working proficiency)`，未给等级 → 无法量化，需自行判断
价值：Skill High / Portfolio High / Networking Medium
官方来源：https://atlas-oss.example/mentorship

**另一个方向（你可能不会想到去搜这些）**
- Security 方向的 CTF 联赛 — 与你现有技能完全对口，且是安全岗最直接的可见证据（Competition）
- 开源项目的 `good first issue` 清单 — 比"再学一门课"更快形成公开产出（Open Source / Explore）
- 会议 Travel Grant — 学生做报告可申请，用于把课程项目变成一次公开演讲（Funding / Adjacent）

**已见过（2 条）**：Northstar Labs 相关页面（上次推荐，截止未变）
**下一步（你自己执行）**：① 11-01 前提交 Northstar（需要 CV + 成绩单）；② 先挑 1 个 good first issue 试水

---

## Example B — Design student, games + 3D, France / global

输入（对应 `examples/profiles/design-student.example.json`）：

```text
设计专业，喜欢游戏和 3D，想找比赛和作品集项目，远程/全球都行。
```

Locale 计划：

```text
regions: france          primary locale: fr-FR        secondary: en
load files: references/locales/generic.md
```

输出：

> 按「设计大二 + Figma/Blender + 关注 design/game/art，目标法国 + 全球远程」搜了一轮，
> 覆盖 竞赛 / 兴趣 / 项目 / 活动 4 类（未把求职类作为主力），筛出 4 条值得看的。
> 你的画像里没有毕业年份，所以实习类我只标了 Unknown，没有替你假设。

**1. Mira Design Foundation Student Award（作品集导向）**
类型：Competition / Design · 远程投稿，法国主办
为什么适合你：
- 接受本科（页面明确 `undergraduate`）
- 评审依据是提交的作品，与你的 portfolio 目标一致
- 与 design / illustration 兴趣重合
资格：Eligible
截止：2026-12-05（法语页面写 `5 décembre 2026`，已归一化）
注意：△ 需要项目陈述（法/英均可，页面未写明）
价值：Portfolio High / Networking Medium / Career Low
官方来源：https://mira-design.example/student-award-2026

**2. Studio Vela Global Game Jam（全球，48 小时）**
类型：Hobby / Competition · 线上，全球开放
为什么适合你：
- 与 game / 3D 兴趣直接对应，门槛低、产出快
- 允许 1–5 人组队、可跨校
资格：Eligible（`any` 学历）
截止：2027-01-10（活动 01-22 ~ 01-24）
注意：△ 主题在开始时才公布
价值：Portfolio High / Interest High / Career Low
官方来源：https://studio-vela.example/gamejam

**另一个方向（你可能不会想到去搜这些）**
- 城市文化机构的展览志愿者/展陈协助 — 对设计专业是真实的行业接触（Event / Explore）
- 开源设计系统贡献 — 把 Figma 能力变成公开可验证的产出（Open Source / Adjacent）
- 跨校联合毕业设计项目 — 比个人作品更能体现协作（Project / Adjacent）

**下一步（你自己执行）**：① 12-05 前投稿 Mira（作品 + 陈述）；② 组 2–3 人报名 Game Jam

---

## 两个示例对比说明了什么

| | Example A | Example B |
|---|---|---|
| 目标地区 | 美国 | 法国 + 全球 |
| 主语言 | `en-US` | `fr-FR`（+ 英文补充） |
| 加载的区域知识 | `us.md` | 仅 `generic.md` |
| 主力类别 | 开源 / 竞赛 / 实习 / 资助 | 竞赛 / 兴趣 / 项目 |
| 硬条件类型 | work authorization、GPA、毕业窗口 | 学历、作品要求 |

同一套协议，两个人得到的搜索语言、类别配比与判据完全不同 —— 因为语言与地区来自运行时，
而不是来自 Skill 作者的偏好。
