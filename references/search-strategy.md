# Search Strategy — 从画像到搜索矩阵

这份文件解决 Step 2–4：**该搜哪几类、每类发什么 query、发多少、什么时候停。**

核心命题：用户不知道自己该搜什么。普通 Agent 会把用户的字面词当查询词
（"IoT internship"）然后返回一批结果。OpportunityRadar 必须先推导搜索空间。

---

## 1. Search Space 构建（Step 2）

### 1.1 三维输入

```
Major / major_family  →  决定 technical field 与相邻学科
Skills                →  决定技术栈层面的精确词
Interests             →  决定跨学科切入点（最容易产生"想不到的机会"）
Goals                 →  决定搜哪几类（不是搜哪些词）
Grade / graduation    →  决定 eligibility 过滤线与时间线
Region / constraint   →  决定语言、地点、remote 与签证条件
```

### 1.2 major_family → 相邻领域映射

专业名只是入口。每一类都往三个方向展开：**更专、同层、相邻**。

| major_family | 更专 | 同层可替换 | 相邻（Adjacent） | 远邻（Explore） |
|---|---|---|---|---|
| iot_embedded | firmware, RTOS, sensor network, edge computing | electronics, EE, mechatronics, instrumentation | robotics, automotive electronics, smart agriculture, digital twin, UAV | solutions engineer, DevRel, technical product, maker program, field application engineer |
| cs_software | backend, distributed systems, compiler, security | data engineering, mobile, HCI, DevOps | fintech, health informatics, GIS, computational biology | developer advocate, technical writer, solutions architect, product manager |
| ai_data | CV, NLP, LLM, RL, TinyML, MLOps | data science, statistics, optimization, analytics | bioinformatics, robotics, autonomous driving, climate modeling | AI product, AI policy/ethics, dataset curation, evaluation engineering |
| ee_electronics | power electronics, RF, ASIC/FPGA, control | communications, MEMS, instrumentation | automotive, aerospace, energy grid, medical devices | test engineering, technical sales, hardware sourcing |
| me_aero | CAD/CAE, thermal, structures, manufacturing | robotics, materials, mechatronics | automotive, UAV, space systems, agri-machinery | industrial design, technical consulting |
| design_media | UI/UX, motion, 3D, illustration | game art, industrial design, film/video, brand | XR, data visualization, creative coding, animation | design system, design ops, product research, exhibition/museum work |
| business_econ | finance, marketing, operations, strategy | accounting, supply chain, HR, entrepreneurship | tech product, venture capital, public policy, consulting | developer ecosystem, community ops, business development |
| lifesci_chem | molecular bio, genomics, analytical chem, ecology | pharma, food science, biotech, neuroscience | bioinformatics, medtech, agritech, environmental science | regulatory affairs, sci-comm, lab automation, clinical coordination |
| health_medical | public health, clinical research, nursing, epidemiology | biomedical engineering, pharmacy, nutrition | health informatics, global health, medical devices | health policy, patient advocacy, health communication |
| environment_agri | climate science, conservation, soil/water, renewable energy | agriculture, forestry, sustainability, energy systems | food systems, urban planning, environmental engineering | ESG analysis, climate communication, field data collection |
| humanities_social_science | history, philosophy, linguistics, anthropology | sociology, political science, psychology, area studies | cultural heritage, cognitive science, migration studies, digital humanities | archives/museums, publishing, user research, cultural program management |
| law_policy | constitutional/contract law, regulation, governance | international relations, public administration, compliance | tech policy, IP, human rights, environmental law | policy analysis, regulatory affairs, civic tech, standards bodies |
| education | pedagogy, curriculum, assessment, teacher training | educational technology, linguistics, psychology | learning analytics, inclusive education, STEM outreach | instructional design, science communication, community education |

每个 major_family 都按同一条原则展开（**更专 → 同层 → 相邻 → 可迁移**），不要只把工程类专业写满、
把其他专业留两三行 —— 那会让搜索结果系统性偏向技术方向。

找不到对应行时，用同一条原则现场推导：**更专 → 同层 → 相邻 → 可迁移能力**。
每一层至少写出 3 个词，再进入下一层。

### 1.3 搜索矩阵（矩阵是内部产物，要真的写出来）

对每一类，产出 `层 × 语言` 的矩阵格。示例（Mode A，IoT 大三，Japan/China/Remote）：

| 类别 | Exploit（直接） | Adjacent（相邻） | Explore（可迁移/想不到） | 语言 |
|---|---|---|---|---|
| career | IoT / embedded / firmware internship | edge AI internship、robotics internship、automotive electronics | solutions engineer intern、developer relations intern、FAE trainee | EN / JA / ZH |
| research | IoT undergraduate research、embedded systems research internship | sensor networks RA、edge AI research student | 産学連携 lab、visiting student program | EN / JA |
| competition | IoT competition、embedded design contest | TinyML challenge、robotics competition | アイデアコンテスト、design award | EN / JA / ZH |
| open_source | ESP32 open source、Zephyr contributor | embedded mentorship、ROS community | good first issue 跨项目、docs/translation 贡献 | EN |
| skill_development | embedded certification、TinyML course | cloud credits students、开发板计划 | GitHub Student Pack 类学生开发包 | EN / JA |
| project | hardware build challenge | open innovation 命题 | civic tech / 数据集项目 | EN / JA |

> 矩阵的价值在于**强制覆盖**。如果某类的 Adjacent / Explore 格子是空的，
> 说明推导还没做完，不是"没有机会"。

---

## 2. Query Expansion 规则（Step 3）

### 2.1 允许的扩展方式

| 方式 | 例子 | 说明 |
|---|---|---|
| 同义/近义 | internship → intern, 实习, インターン, placement, co-op | 提高召回 |
| 技术栈换层 | ESP32 → MCU, 嵌入式, firmware, TinyML | 不偏离用户能力 |
| 应用域扩展 | ESP32 → smart home, wearable, 农业 IoT | 打开发现场景 |
| 角色扩展 | intern → RA, contributor, ambassador, volunteer, mentee | 打开机会类型 |
| 时间线扩展 | intern → 2026 summer, summer 2027, 通年採用 | 保证时效 |
| 资格语言 | 学生 + 大学生 + 学部生 + student | 匹配官方用词 |

### 2.2 防跑偏（硬约束）

1. **可溯源**：每个扩展词必须能追溯到 profile 里的某个信号（技能/兴趣/专业/目标）。
   追不到 → 不搜。
2. **两跳上限**：从 profile 词出发最多扩展两跳（ESP32 → TinyML → edge AI ✅；
   ESP32 → edge AI → AI ethics ❌）。
3. **不复读**：语义等价的 query 只发一次。看到"embedded internship"和
   "internship embedded"不要当成两个 query。
4. **不发明**：不要凭想象编造"某公司应该有的学生计划"。没搜到就是没搜到。
5. **类别均衡**：单类 query 数不超过总数的 1/3（Mode A 之外另按权重表调整）。

---

## 3. 分层比例 70 / 20 / 10

| 层 | 占比 | 定义 | 判定问题 |
|---|---|---|---|
| **Exploit** | 70% | 直接命中用户技能/专业 | "这就是用户已经在找的东西吗？" |
| **Adjacent** | 20% | 相邻领域，能力可迁移 | "同一套能力还能去哪？" |
| **Explore** | 10% | 用户不会想到，但能力可迁移 | "这个人如果换一个岗位名称/场景，还成立吗？" |

**Mode C（未知机会）改为 55 / 25 / 20**，并把 Explore 的定义放宽到
"非传统职业路径、跨专业项目、企业学生计划、mentorship、社区机会、兴趣类机会"。

**最重要的约束**：最终答案里应当**真的出现** Explore 层的条目（前提是它达到了质量与
验证门槛）。如果一开始就搜了 Explore 却没有一条进最终结果，先检查是不是排序把它砍掉了；
如果 Explore 层确实没有合格机会，**用一句话如实说明**，不要拿弱机会凑数。

---

## 4. 语言由目标地区决定（Step 4 必做）

**规则：机会在哪，就用那里的语言搜一次。** 但"哪里"来自运行时，不是固定的语言清单。

```
目标地区（来自 Profile / 当前请求）
      ↓
primary locale（当地语言） + secondary（英文，仅在有国际召回增益时）
      ↓
把本文件的 query intent 本地化成当地用词
```

- 完整规则见 **`references/locales/generic.md`**（永远加载）。
- 具体地区的用词与资格术语见对应 locale 文件（`jp.md` / `cn.md` / `us.md` / `uk.md` / `de.md`），
  **只在目标地区需要时加载**。
- 地区不在 locale 表中 → 照样工作：通用规则 + 英文 + **页面语言动态检测**（`scripts/locales.py --detect`）。

三条容易搞错的地方：

1. **英文不是绝对默认。** 用户明确只看本国机会时（"我要找国内大三暑期实习"），
   不要为了流程完整硬塞一批英文结果；英文只在跨国企业、国际项目、远程机会等处补一轮。
2. **不要用交流语言推断地区。** 用户用中文提问 ≠ 目标地区是中国。
3. **不要用专业推断地区。** 专业是 IoT ≠ 需要日语。

## 5. 模式权重表（Step 0 选定，Step 2 应用）

**权重的单一来源是 `scripts/locales.py` 的 `MODE_WEIGHTS`**（由 `tests/` 校验其覆盖全部
13 个类别与 4 个模式）。这里只说明各模式的**取向**，不重复数字：

| 模式 | 触发说法 | 取向 |
|---|---|---|
| **A 常规发现** | "最近有什么适合我的机会" | 按用户声明的 goals 均衡覆盖 |
| **B 非求职** | "我不想找工作 / 最近有点闲" | 压低 career 与 education，抬高竞赛 / 开源 / 项目 / 技能 / 活动 / 兴趣 |
| **C 未知机会** | "有什么我可能完全不知道的机会" | 抬高 open_source / project / networking，并把 adjacent + explore 提到 ~45% |
| **D 能力反推** | "我想以后做 X，现在做什么最好" | career 只作为"目标参照"，主力是 competition / project / open_source / skill |

用代码决定权重、用文字解释取向，可以避免"文档写一套、脚本跑另一套"。

## 6. Mode D：用真实机会反推当下行动

用户问"我想以后做 X，现在做什么最好"时，**禁止只给学习路线**。

```
1. 搜真实 X 类机会（career 为主：internship / new grad / 研究型实习）
   → 目标：20–40 条真实 posting，覆盖用户目标地区
2. 逐条抽取硬性/偏好要求 → 归一化词表
   （RTOS、C++、Git、Linux、英语成绩、发表经历、GPU/云、团队协作…）
3. 统计频次：在 N 条中，词 w 出现在 M 条
4. 找出用户当前缺失的高频项 → 这就是"能力缺口"
5. 反向搜索能补这些缺口的机会：
   competition（有交付物的）→ project（企业命题/开源）→
   open_source（有 mentorship 的）→ skill_development（认证/训练营）→
   research（实验室经历）
6. 输出：缺口 → 对应可参与的真实机会（不是课程清单）
```

**话术约束**（见 `state-and-feedback.md` §4）：
只能说"在本次扫描到的 N 条机会中，X 出现于 M 条"，
**禁止**说"学 X 能多 N 个机会""学 X 就能拿到 offer"。

---

## 7. 搜索预算与停止条件

### 7.1 预算（一次正常 Discovery）

| 项目 | 建议量 | 说明 |
|---|---|---|
| 类别数 | 开放性问题 ≥5；有明确目标 ≥3 | **覆盖度指导**：用来防止"全部退化成实习"，不是必须凑齐的数字。没有相关性的类别不要硬搜 |
| query 数 | 15–40 | 不是越多越好 |
| 深读页面（fetch/浏览器） | 8–20 个 | 只深读高潜力候选 |
| 最终结果 | 5–15 条 | 超过说明没筛 |

### 7.2 停止规则

对某个类别，出现下列任一情况就停：

1. 连续 **2** 个 query 变体只返回已见过或不相关的结果；
2. 已获得 **4–6** 条具官方来源的候选；
3. 继续检索只能拿到聚合站转载、无官方页可确认；
4. 时间已明显超出"下一个更有价值的类别"的收益（宁可换类别，不要刷同一类）。

### 7.3 结果太薄时（降级顺序）

```
① 换层：Exploit 太薄 → 搜 Adjacent
② 换语言：英文薄 → 用当地语言再搜一次
③ 换角色词：internship 薄 → RA / contributor / ambassador / volunteer / 志愿者
④ 换入口：官方页难找 → 先用聚合站/社区发现，再回官网确认
⑤ 放宽时间：当季无窗口 → 找"常年招募/滚动招募"的项目
⑥ 都不行 → 如实说明"该方向当前公开机会很少"，不要用凑数条目填充
```

---

## 8. 反模式

- ❌ 只把用户的字面词丢给搜索引擎。
- ❌ 一次搜索就交付（Step 4 只执行了一次）。
- ❌ 所有结果来自同一类（通常是 career）。
- ❌ 只搜英文，漏掉当地语言的官方机会。
- ❌ 为了"全面"刷几十页，最后给 40 条链接。
- ❌ 把 Explore 层写进计划却在结果里删掉。
- ❌ 用"应该存在"的项目凑数（未经验证的想象条目）。
