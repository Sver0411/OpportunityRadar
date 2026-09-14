# OpportunityRadar

**Find the opportunities you didn't know to search for.**
**发现那些你根本不知道该搜什么的机会。**

A reusable **Personal Opportunity Discovery Protocol** for web-capable AI agents.
它不是一个网站、不是一个招聘平台、不是一个 Agent，也不是一段 Prompt 模板——
它是一套可安装的协议，让任何支持联网搜索的 Agent 从"随便搜几个结果"升级为：

```
Understand → Expand → Discover → Verify → Filter → Rank → Explore
```

面向大学生、硕博研究生、应届生与职业早期用户。

---

## 1. 为什么普通搜索不够

普通 Agent 会把用户的问题直接变成一次搜索：

```
用户：帮我找几个实习。
Agent：搜索 "IoT internship" → 返回几个结果。
```

问题不在搜索结果，而在**用户不知道该搜什么**。用户不会想到去搜
`solutions engineer intern`、`农业 IoT 开放创新命题`、`Maker Faire 学生展位`
——但这些恰恰可能是最适合他的机会。

OpportunityRadar 强制 Agent 按固定顺序工作：

```
读取用户情况 → 构建搜索空间 → 展开查询 → 跨类别搜索 → 发现候选
→ 回官方来源验证 → 结构化 → 去重 → 资格判断 → 排序 → 探索相邻方向 → 解释
```

差异来自这 13 个环节，而不是某一句话写得好：

| 环节 | 裸 Agent 通常 | OpportunityRadar |
|---|---|---|
| 分类 | 只看"实习/工作" | 13 类机会体系（含科研、开源、竞赛、资助、兴趣、社区） |
| 查询 | 用户的字面词 | 按专业族推导的搜索矩阵（更专/同层/相邻/远邻） |
| 语言 | 只搜英文 | 当地语言 + 英文双跑（中/日/德/韩/英） |
| 配比 | 全部 exploit | 70% 直接 / 20% 相邻 / 10% 可迁移探索 |
| 来源 | 聚合站结果直接用 | Tier A–D 分级，A/B 才能确认事实 |
| 资格 | 给个 Yes/No | 五级判定 + 依据 + 缺失项 |
| 去重 | 无 | URL 规范化 + 标题/机构/截止日相似度 + 冲突报告 |
| 排序 | 搜索引擎顺序 | Match 与 Priority 分离（含 deadline 紧迫度） |
| 记忆 | 每次重来 | 本地 seen/saved/ignored + 变化检测 |
| 缺口 | 给学习路线 | 用真实机会反推当前该补什么 |

---

## 2. 它明确不是什么

- ❌ 不是招聘网站、比赛聚合站、SaaS 后端
- ❌ 不是独立 Agent（不自己实现浏览器、搜索引擎、爬虫、登录系统）
- ❌ 不是 Web Dashboard / React 应用 / 移动 App
- ❌ 不做账号系统、云数据库、付费流程
- ❌ 不代用户投递、报名、发邮件（未经当轮明确授权）

它复用宿主 Agent 已有的 Web Search / Browser / Fetch / Shell / Python / 文件读写 /
Memory / MCP 能力，只补充协议、分类体系、策略、规则与确定性脚本。

---

## 3. 安装

Skill 是纯文件包，放进宿主 Agent 的 skills 目录即可：

```bash
# 通用做法：<你的 Agent 的 skills 目录>/opportunity-radar/
cp -r OpportunityRadar ~/.workbuddy/skills/opportunity-radar        # WorkBuddy
cp -r OpportunityRadar ~/.codebuddy/skills/opportunity-radar        # CodeBuddy
cp -r OpportunityRadar ~/.claude/skills/opportunity-radar           # Claude Code 示例
cp -r OpportunityRadar <项目>/.<agent>/skills/opportunity-radar      # 项目级安装
```

要点：

- **目录名用 `opportunity-radar`**，与 `SKILL.md` frontmatter 的 `name` 保持一致
  （GitHub 仓库名可以是 `OpportunityRadar`）。
- 只需要 Python 3.8+ 标准库，无第三方依赖、无网络请求。
- 宿主 Agent 必须有联网能力，否则 Skill 会明确回复：
  `Opportunity discovery requires a web-capable host agent.`

---

## 4. 目录结构

```
OpportunityRadar/
├── SKILL.md                          # 协议核心：触发规则、13 步工作流、横切规则、自检
├── README.md
├── LICENSE                           # MIT
├── .gitignore
│
├── references/                       # 按需加载的领域知识（不进 SKILL.md 主体）
│   ├── opportunity-taxonomy.md       # 13 类机会 + 子类 + 来源 + 多语言 query 模式 + 重叠消解表
│   ├── search-strategy.md            # 搜索矩阵、Query 扩展规则、70/20/10、本地语言、预算与停止规则
│   ├── trust-policy.md               # Tier A–D、发现 vs 确认、冲突处理、新鲜度
│   ├── extraction-policy.md          # 字段级抽取规则、Explicit/Inferred/Unknown、反幻觉
│   ├── eligibility.md                # 五级判定、确定性优先顺序、语义条件与地区规则
│   ├── ranking.md                    # Match vs Priority、组件权重、多样性配额、价值评估
│   ├── output-format.md              # 输出模板、长度纪律、JSON 产物、缺口快照话术
│   ├── profile-building.md           # 渐进式画像、何时该问、记忆复用、最小可用画像
│   └── state-and-feedback.md         # seen/saved/ignored 语义、变化检测、反馈影响边界
│
├── schemas/
│   ├── profile.schema.json           # 用户画像（字段缺失一律 null）
│   └── opportunity.schema.json       # 机会记录（主/次分类 + 多标签 + 验证状态）
│
├── scripts/                          # 纯标准库，确定性任务用代码而不是模型
│   ├── normalize_date.py             # 多语言日期/区间/滚动招募 → ISO；年份不明不猜
│   ├── dedupe.py                     # URL 规范化 + 相似度聚类 + canonical 选取 + 冲突报告
│   ├── score.py                      # Match/Priority 分项打分 + 资格预判 + 多样性自检
│   └── state.py                      # seen/saved/ignored + 变化检测 + 权重建议
│
└── examples/
    ├── profile.example.json          # 画像格式示例（需求文档验收画像）
    ├── opportunity.example.json      # 机会记录格式示例
    ├── opportunity.batch.example.json # 8 条批量输入（含 3 条重复）用于演示 dedupe/score
    ├── dates.example.txt             # 26 种日期写法的测试/演示输入
    └── discovery-output.example.md   # 最终输出格式示例（虚构数据）
```

> ⚠️ `examples/` 里所有机构与事实**均为虚构**，只用于演示格式与脚本，禁止当作已验证的真实机会。

---

## 5. 触发示例

**应该触发：**

```text
我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？
我最近有点闲，有什么值得做的吗？
有没有适合我的比赛 / 实习 / 科研项目 / 开源项目？
有什么适合我专业的东西？有没有含金量高的活动？
有没有什么我可能完全不知道的机会？
我想提高以后找嵌入式实习的竞争力，现在做什么最好？
我现在缺什么？为什么很多机会我都申请不了？
```

**不应该触发（普通查询）：**

```text
AWS 是什么？                    → 直接回答
TOEIC 什么时候考试？             → 直接回答
帮我改简历 / 翻译这个 JD          → 不属于发现流程
```

边界规则：同一个话题如果接着问"**适不适合我 / 值不值得参加 / 根据我的情况看看**"，
就从普通查询转为机会发现，此时触发。

---

## 6. 工作流的四个模式

| 模式 | 触发说法 | 权重调整 |
|---|---|---|
| **A. 常规发现** | "最近有什么适合我的机会" | 按声明的目标均衡覆盖 |
| **B. 非求职** | "我不想找工作，就是最近有点闲" | ↓ Career/Education，↑ 竞赛/开源/项目/技能/活动/兴趣 |
| **C. 未知机会** | "有什么我可能完全不知道的机会" | Adjacent + Explore 提到 ~45% |
| **D. 能力反推** | "我想以后做 X，现在做什么最好" | 搜真实 X 机会 → 统计真实要求 → 反向搜索能补缺口的机会 |

Mode D 是最能体现差异的一条：**不给学习路线，给"用真实机会反推的当下行动"。**

---

## 7. 确定性脚本的实际用法

以下命令与输出均在本机 Python 3.13 下实测通过。

### 7.1 日期归一化

```bash
python3 scripts/normalize_date.py "9月20日-10月5日" --default-year 2026 --now 2026-09-14
```

```json
{
  "iso": "2026-09-20", "end": "2026-10-05",
  "precision": "day", "year_unknown": true,
  "days_remaining": 6, "expired": false,
  "notes": ["原文未写年份，按 --default-year 2026 填充（请复核）"]
}
```

覆盖 26 种写法（含 `Dec 20 - Jan 5, 2027` 的跨年区间推导、`随時受付` / `常年招募`
识别为滚动招募、`September 2026` 只到月精度、无法解析时明确"不猜测"）：

```bash
python3 scripts/normalize_date.py --file examples/dates.example.txt --default-year 2026
```

### 7.2 去重

```bash
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --format text
```

```text
input=8  clusters=5  removed=3

[c001] size=3 canonical=nagi-robotics-2027-summer-internship-program
  title: 2027 Summer Internship Program
  org  : Nagi Robotics, Inc.
  - merged in: nagi-robotics-summer-internship-2027
  - merged in: nagi-robotics-2027-internship
  ! conflict deadline: 2026-10-03(C,A) vs 2026-10-17(C)
  ! conflict official_url: careers.nagi-robotics.example/students/summer(C,A) vs .../summer-2027(C)

might be duplicates (LLM review):
  ? nagi-robotics-summer-internship-2027 <-> nagi-robotics-robot-hackathon-2027  score=0.629
```

它做了三件确定性的事：**URL 规范化**（剥掉 `utm_*`、`ref`、尾斜杠）、
**相似度聚类**（标题/机构/截止日/国家/类别加权，机构差异大时禁止自动合并）、
**冲突报告**（同一机会不同来源的截止日不一致 → 明确指出以官方为准）。
模糊重复不自动合并，而是标 `maybe` 交给模型判断。

### 7.3 打分（决策辅助）

```bash
python3 scripts/dedupe.py --input examples/opportunity.batch.example.json --output /tmp/clusters.json
python3 scripts/score.py --profile examples/profile.example.json \
                         --opportunities /tmp/clusters.json --today 2026-09-14 --format table
```

```text
| # | 机会 | 类别 | Match | 紧迫 | Priority | 档 | 资格 | 主要理由 |
|---|---|---|---|---|---|---|---|---|
| 1 | 2027 Summer Internship Program | career | 88 | 68 | 85 | High | Probably Eligible | 命中目标 internship（priority=high） |
| 2 | Nagi Robotics Robot Hackathon | competition | 69 | 35 | 64 | Medium | Unknown | 命中目标 competition |
| 3 | Tokyo Embedded Challenge 2026 | competition | 63 | 50 | 61 | Medium | Unknown | 命中目标 competition |
| 4 | Kagura University Undergraduate Research Program | research | 65 | 35 | 60 | Medium | Unknown | 命中目标 research |
```

要点：

- **Match ≠ Priority**：`Priority = 0.85×Match + 0.15×Urgency`，所以"匹配 88 但两天后截止"
  会排在"匹配 95 但半年后截止"前面。
- **未知不作 0 分**：页面没写技能要求 → 中性 50，而不是 0，避免错杀信息不全的机会。
- **资格预判会说不确定**：上例中 Kagura 项目页面写了 JLPT N2，而画像没有成绩 →
  判定 `Unknown`，理由"画像未提供对应成绩/等级，无法确认达标"，而不是假装达标。
- 输出还包含 `diversity`（类别数、adjacent/explore 是否有货、单类占比是否超 50%），
  直接对应 `references/ranking.md` 的多样性配额。

> 分数只用于排序辅助。展示给用户时用 `High/Medium/Low` 档次 + 理由，
> 不要把 87.3 这种"科学精确"假分数当结论。

### 7.4 本地状态

```bash
python3 scripts/state.py init
python3 scripts/state.py mark-seen --input .opportunity-radar/last-run.json
python3 scripts/state.py feedback saved --id nagi-robotics-robot-hackathon-2027 \
        --category competition --tags robotics,hackathon
python3 scripts/state.py list --status saved
python3 scripts/state.py suggest
```

变化检测只关注 8 个字段（deadline / application_open / cost / compensation /
education_level / student_year / language_requirement / official_url）：

```json
{ "new": [], "changed": ["kagura-university-undergraduate-research-2026"], "repeat": 7,
  "details": { "kagura-university-undergraduate-research-2026": [
    { "field": "deadline", "from": "2026-11-30", "to": "2026-12-15" } ] } }
```

第二次运行同一批输入 → 全部 `repeat`，不再重复推荐。
`suggest` 只输出权重建议，**不会偷偷改写画像**。

### 7.5 本地状态文件

```
.opportunity-radar/
├── profile.json     # 可选画像（宿主没有 Memory 时才需要）
├── seen.json        # 首次/最近出现时间、被跟踪字段哈希、变更日志
├── saved.json       # interested / saved / applied
├── ignored.json     # ignored / not_relevant
└── last-run.json    # 上一轮结构化产物
```

整个目录已在 `.gitignore` 中忽略；状态全程留在本地，不发起任何网络请求。

---

## 8. Source Trust（来源可信度）

| 级别 | 例子 | 用途 |
|---|---|---|
| **A** | 官方网站、企业官网、大学官网、政府、实验室、赛事官网 | 可作为事实依据 |
| **B** | 学校就业中心、学术组织、行业协会、官方合作机构 | 可确认，冲突时以 A 为准 |
| **C** | LinkedIn、招聘平台、比赛/活动聚合站、技术社区 | **只用于发现** |
| **D** | 博客、论坛、个人帖子、转载、非官方公众号 | 只用于发现 + 线索 |

规则：**C/D 用来发现，A/B 用来确认。** 第三方说截止 9/20、官方说 9/25 →
采用官方并在输出里写明差异。找不到官方页面就写"未找到官方确认来源"，
**不允许**凭空给一个"官方链接"。

---

## 9. Eligibility（资格判断）

五级判定，禁止一律 Yes/No：

`Eligible` / `Probably Eligible` / `Unknown` / `Probably Ineligible` / `Ineligible`

先过确定性条件（时间窗口 → 学历 → 年级/毕业年份 → 国籍签证 → 学校 → 专业 → GPA →
语言 → 年龄），再处理语义条件（`or related field` 一类）。语义条件只影响
`Eligible` 与 `Probably Eligible` 的区分，不能让一条本来不满足的硬性条件"复活"。

跨专业话术（示例）：

> 页面写 `Electrical Engineering or related field`，你的专业是物联网工程
> → `Probably Eligible`，但需说明"物联网工程通常与 EE/CS 存在较高相关性，
> 最终以组织方定义为准"。

地区规则已内置：中国"应届生身份"按毕业年份、日本按「卒業年度」而非学年、
英美需注意 work authorization、欧洲区分 Pflichtpraktikum。

---

## 10. 验收测试（需求文档 §52–54）

| # | 输入 | 期望行为 |
|---|---|---|
| 1 | 我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？ | 使用画像；覆盖 ≥5 类；做 Query 扩展；中/英/日三语搜索；真实机会；优先官方来源；给资格判定；去重；给推荐理由；至少含 Adjacent / Explore |
| 2 | 我不想找实习，最近有什么值得做的？ | **不继续无脑推实习**；转向竞赛/科研/开源/项目/技能/活动/兴趣 |
| 3 | 我想以后做 Embedded AI，但是不知道现在应该做什么。 | 搜真实 Embedded AI 机会 → 统计常见要求 → 反推可参与的竞赛/开源/项目/科研/技能机会，而**不是**只输出"学 C++ / 学 RTOS / 学 TinyML" |

各模式对应的输出形态见 `examples/discovery-output.example.md`。

---

## 11. 自我审查（需求文档 §55.16）

| 问题 | 结论 |
|---|---|
| 是否做成了网站？ | 否。全部是 Markdown / JSON Schema / 标准库 Python，无任何 Web 代码。 |
| 是否只是 Prompt？ | 不是。除协议外还有 13 类分类体系、可复制执行的多语言 query 模板、4 个实测可跑的确定性脚本、2 个 JSON Schema、seen 状态与变化检测。 |
| 是否真的比裸 Agent 更系统？ | 是。若删掉本 Skill，裸 Agent 会退化为"一次搜索 → 给几个实习"，缺的正是分类枚举、搜索矩阵、语言覆盖、来源分级、资格分级、去重、Match/Priority 分离、状态与缺口分析。 |
| 是否存在互相矛盾的规则？ | 已逐条对齐：分类 id、五级判定名、Trust Tier、评分权重、状态字段在 SKILL.md / references / schemas / scripts 中取值一致；`scripts/score.py` 的 WEIGHTS 与 `references/ranking.md` 的权重表逐项相同。 |
| 是否存在 Agent 无法执行的步骤？ | 无外部依赖：联网步骤用宿主已有的 Web Search / Fetch / Browser；不依赖任何私有 API；无联网能力时按 SKILL.md §0 明确拒绝。 |

---

## 12. 当前限制

- **依赖宿主联网能力**：没有 Web 能力时不降级到"猜测"，而是明确拒绝执行。
- **不保证覆盖全市场**：缺口统计只在"本次扫描到的样本"内成立，输出中强制标注样本量。
- **需要模型判断的部分**：语义资格（`related field`）、模糊重复、价值评估仍需 LLM，
  脚本只提供确定性信号与分项。
- **时间敏感**：机会信息过期很快（竞赛 14 天、实习 30 天、奖学金 60 天的复核阈值），
  长期使用需要定期重跑并注意 `last_verified`。
- **语言覆盖**：多语言 query 模板以中/英/日为主，德/韩为基础覆盖，其他语种需现场推导。
- **不做自动投递**：默认只做发现—验证—判断—解释—整理；申请动作始终由用户自己完成。

---

## 13. 许可

MIT，见 [LICENSE](LICENSE)。
