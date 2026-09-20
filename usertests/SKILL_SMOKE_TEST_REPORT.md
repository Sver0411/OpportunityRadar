# Skill 端到端实测报告（2026-09-20）

**测试方式**：真实调用**已安装**的 skill（`~/.workbuddy/skills/opportunity-radar`），
真实联网（6 次搜索 + 5 次抓取），**全部使用真实机会**，不是 fixture。
画像取真人测试 A 类：物联网工程大二、杭州 + 可远程、每周 8 小时、预算低。

结论先说：**链路跑得通，端到端可用**；同时暴露 **6 个真缺陷**（5 个是我的实现 bug，
1 个是文档/契约矛盾），已全部修好并加回归测试。测试数 **396 → 424**。

---

## 1. 链路是否跑通

| 步骤 | 结果 |
|---|---|
| 区域/语言解析 | ✅ `regions=[china, remote]`、`primary=zh-CN`、`optional=en`、`place_hints=['杭州']` |
| 来源规划 | ✅ gap→intent→family→query，18 个 family 正常输出 |
| 去重 | ✅ 7 → 7 clusters（无误合并） |
| 真实 gate 分区 | ✅ **推荐 1 / 需确认 4 / 排除 2** |
| Gap 模型 | ✅ 发展缺口 1 条 + 手续 8 项 + 资格约束 1 条 |
| Bridge | ✅ 只对发展缺口搜索；无荒谬桥 |
| Portfolio | ✅ 预算 8h / 计划 5h / 冲突 False，超预算项带原因丢弃 |
| 产出回答 | ✅ 见第 5 节样例 |

---

## 2. 六个真缺陷（全部实测复现 + 已修）

### F1 语言泄漏：所有用户都会收到日语 query（最严重）

**现象**：`region=China`、`primary_locale=zh-CN` 的画像，`plan_queries()` 产出
`コントリビュート 方法`、`メンターシップ 応募`。
**根因**：`SOURCE_FAMILIES[*]["intents"]` 与 `STAGE_INTENT_OVERRIDES` 把日语**写死成通用第二语言**
（19 个 family 里 15 个带日语模板）。
**影响**：违反本项目自己的契约（"语言中立 intent 模板"）；污染 `source_family_hit_rate`；
CN/US 用户的搜索预算被日语 query 消耗。
**修法**：日语整体移入 `LOCALE_INTENTS[family]["ja"]`；新增 `zh` 变体（中文是 CN 主 locale）；
`plan_queries()` 依据 `locales.resolve_locales()` 决定发哪些语言，英文作语言中立底座。
**验证**：CN → `[zh, en]`、JP → `[ja, en]`、US/未知 → `[en]`；CN 计划里日语 0 条。

> 附带发现：语言标注一开始我用字符启发式（有假名=ja，有汉字=zh），结果 5 条**纯汉字日语**
> 模板（`学会 学生会員`、`模擬試験`、`研究助成 公募`）被误标成 `zh`。已改为**语言取自模板表本身**。

### F2 契约矛盾：`application_status: "rolling"` 被 schema 拒绝

**现象**：schema 的顶层 `application_status` 枚举是 `open/closed/not_open/unknown`，
**不含 `rolling`**；而 `evidence.py` 的 `PARTICIPATION_OPEN_STATUSES = ("open","rolling")`
依赖它 → **那条 rolling 分支永远不可达**。滚动招募的机会（正是 OSPP）无法在 schema 合法前提下
被表达成"可参与"。
**修法**：schema 枚举加 `rolling`；枚举唯一事实来源移到 `common.OPPORTUNITY_APPLICATION_STATUSES`，
由测试锁死"schema 枚举 == common 枚举"且 `PARTICIPATION_OPEN_STATUSES ⊆ schema 枚举`。
**效果**：OPSS 从"进不了主推荐"变成 **推荐 1 条**。

### F3 报错看不出是哪个字段（同名坑）

**现象**：缺顶层字段时报 `evidence.application_status(application_status)`，无法判断
缺的是顶层机会侧字段还是 evidence 子键；而顶层 `application_status` 与 `state.py` 里
**用户侧**跟踪状态（`saved/applied`）**同名**，极易填错且静默降级。
**修法**：报错写明 `top-level application_status（机会侧 open/rolling…）`；
填入用户侧取值时**显式报错**而不是静默降级；文档补一张两层次对照表。

### F4 手续/材料污染发展缺口（违反项目自己的硬规则）

**现象**：一条中文学生的运行里，11 个"缺口"中 6 个是报名材料 ——
`online application`、`passport copy`、`supervisor approval`、`个人资料`、
`身份证/学籍在线验证报告`、`项目申请书`。它们**各自触发 Bridge 搜索**，
产出「缺护照复印件 → 桥接到开源之夏」这类结论。
这正是 SKILL 明令禁止的："Gap = 缺 GitHub 账号 不能让系统去找 GitHub 学习项目"。
**根因**：`required_materials` 被整体映射成 `portfolio` 缺口；`is_logistics()` 模式过窄；
`nationality_requirement`（"仅限外国护照"）被当成用户的 `location_visa` 缺口。
**修法**：材料三分流 —— 公开产出物（portfolio/demo/writeup/作品集）才可能算缺口；
手续类进 `logistics_prerequisites`；其余进 `preparation_items`。
国籍要求进 `eligibility_constraints`。三者都不进缺口分母、不触发 Bridge 搜索。
同时去掉 `[:5]` 截断（截断 = 静默丢弃）。
**效果**：缺口 **11 → 2**（只剩真实的 `Git` 技能缺口 + 1 条 contextual）；
荒谬 Bridge **全部消失**。

### F5 中英能力词无法互相识别 → 幻影缺口

**现象**：机会要求写「嵌入式」「嵌入式开发」，画像写 `skills=[C, Python, ESP32]`
+ `interests=[embedded]` → 字面 token 无交集 → 报"你缺嵌入式"。
**根因**：`gaps._covered()` 只做字面 token 比对，且**不看 `interests`**。
（同类问题在 `graph.py` 已用 `GAP_TYPE_SIGNALS` 修过，`gaps.py` 漏了。）
**修法**：新增 `common.SKILL_EQUIVALENTS`（中文→英文**直译**，只收直接翻译不做语义外推）；
`_covered()` 纳入 `interests`、支持中文子串互含。
**关键约束**：**不许把整个兴趣同族组映射过来** —— 「会 ESP32」≠「会 RTOS」，
所以 `_covered("RTOS", profile)` 仍必须是 `False`（有测试固定）。

### F6 CLI 参数名不一致（agent 可用性）

`normalize_date.py` 用 `--now`，`score.py` / `evidence.py` 用 `--today`。
实测中我自己就调错了一次。已把 `--today` 加为别名并加一致性测试。

---

## 3. 我自己用错的 3 处（说明 skill 的 agent 可用性问题）

| 我调错的 | 正确用法 | 性质 |
|---|---|---|
| `sources.py --region CN`（地区用中文/裸词） | 可以工作，但区域应走 `locales.py` 解析 | 文档可更明确 |
| `normalize_date.py --today` | 当时只接受 `--now` | **已修（F6）** |
| `portfolio.build_portfolio(gaps=...)` | 参数名是 `bridges=` | 签名与直觉不符，见下 |

还有一次我把 `constraints.preferred_country` 写到了画像顶层，脚本**不报错**，
直接把中文学生当成 Global/Remote + 纯英文跑（`region_source=default_remote`）。
这是**静默失败**：字段放错位置没有校验。本轮未改（属 profile 校验范围），
**建议列入真人测试后的小修**。

---

## 4. 观测指标（修复前 → 修复后）

| 指标 | before | after |
|---|---|---|
| 语言泄漏（CN 计划里的日语 query） | **4/6** | **0/6** |
| 主推荐条数（同一批候选） | **0** | **1**（OSPP） |
| 发展缺口数 | **11**（其中 6 条是材料） | **2**（1 条真实 + 1 条 contextual） |
| 荒谬 Bridge（由材料触发的 Bridge 搜索） | **6 条缺口 → 每条约 2 个桥** | **0** |
| `logistics` / `preparation` / `eligibility_constraints` 是否被记录 | 部分丢失（`[:5]` 截断） | 全部记录，不截断 |
| 测试数 | 396 | **424** |

---

## 5. 用户最终会收到的回答（实测产出）

> **本轮结论**：扫了竞赛 / 开源 / 研究 / 求职 4 类，共 7 个候选，验掉 2 个已结束的。
> 现在真正能开始的是 **1 个**，另有 4 个需要你先确认一下。

**① 开源之夏 2026（OSPP）— 现在就可以开始**
- 为什么适合你：官方学生指南写明**全年持续开放、无固定截止**（2026-09-20 核验）✓
  面向年满 18 周岁高校在校生，中国籍可参加 ✓ 线上协作，符合你"中国 + 可远程"✓
  结项有税前劳务报酬 + 结项证书，成果是**合入上游的 PR** —— 对本科生是硬通货 ✓
- 你要投入：开发周期 2–4 个月，建议每周与导师沟通 1–2 次（约 5h/周）
- 你要产出：合入上游的 PR、结项报告、结项证书
- 资格：**Probably Eligible**（学历相符；需身份证 + 学籍在线验证报告）
- △ 注意：2026 聚焦基础软件与 RISC-V，需要在项目列表里自己挑嵌入式/边缘相关的项目；
  一名学生同时只能申请/承担 **1 个**项目
- 官方来源：https://summer.ospp.ac.cn/ · 学生指南 https://docs2026.summer.ospp.ac.cn/help/student%20guide

**② 需你先确认的 4 个**

| 机会 | 为什么不能直接推荐 |
|---|---|
| 全国大学生嵌入式芯片与系统设计竞赛 — 设计专项赛 / FPGA 赛道 | 官网在 6–12 月窗口内，但**只有月份区间、没有"现在可报名"的声明** → 先问院系/组委会。应用赛道 2026 已 4/20 截止 |
| KAUST Microelectronics Winter Camp 2027 | 9/24 截止（还有 4 天），但要求**高年级本科 + GPA≥3.5 + 赴沙特 6 周**；你大二且偏好中国/远程 → 更适合当未来目标 |
| 全志科技 2027 届校储实习（嵌入式软件） | 只在高校就业网看到转载，官方招聘门户未核实是否接受非 2027 届 |
| USTC 科研实习 | 官方页明确**仅限持外国护照的非中国籍公民** → 中国籍不适用（系统按"画像未声明国籍"处理为信息不足） |

**③ 已排除**：2026 全国大学生物联网设计竞赛（报名 6/15 截止、总决赛 8 月已结束）·
第二十届 iCAN（报名 8/31 截止）

**④ 缺口 → 桥接**
- **Git**（本轮 5 个目标机会里 1 个把版本控制列为硬要求）→ 不建议为它单独找课程：
  最容易补的地方就是 ① 的贡献流程本身（提 PR 就是 Git 实战）
- **导师同意**（研究型机会的主要卡点）、CV / 成绩单 / 护照 / 身份学籍证明 / 在线申请
  属于**准备事项**，不是能力缺口 —— 已单独列出，别和"你缺什么能力"混在一起

**⑤ 本周可执行的配置（按每周 8 小时）**
- 5h/周 → 开源之夏：**本周只做两件事** —— 读 3 个项目详情、给导师发第一封邮件
- 剩 3h：等嵌入式竞赛报名状态确认后再投入（它要 6h/周，若开放就要把 OSPP 降到 2h/周）
- 因超预算放弃：全志实习（40h/周）、USTC（仅外籍）、KAUST（赴沙特 6 周）

---

## 6. 对真人测试的影响

- 修 F1 之前，**中文用户的搜索会掺入日语 query** —— 这会直接污染 5 个真实 session 的召回，
  必须在本轮修掉（已完成）。
- 修 F4/F5 之前，中文用户会看到「你缺护照复印件」「你缺嵌入式」这类**荒谬缺口**，
  是最容易让真人当场说"这系统不行"的失败类型（已消除）。
- **未修、留给真人测试后**：① 画像字段放错位置无校验（静默失败）② `INTEREST_ALIASES`
  仍无中文词（中文用户填中文兴趣时 `interest_fit` 会偏低）③ `build_portfolio` 参数名
  与直觉不符。

**结论**：skill 可以进入真人测试；本轮修复的都是"不修就会让真人误判系统"的缺陷，
没有新增功能。
