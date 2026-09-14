# Opportunity Taxonomy

13 个一级分类。每条 Opportunity 必须有 1 个 `primary_category`，可以有多个
`secondary_categories`，以及任意个自由 `tags`。

分类不是标签墙，而是**搜索空间的枚举清单**：Step 2 用它决定"这次要找哪几类"，
Step 4 用它决定"每类要发哪些 query"。因此本文件同时给出每一类的**典型来源**与
**query 模式**（英/中/日），直接可复制使用。

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
企业学生计划专页、大学就业中心官网、企业日本採用ページ。

**Query 模式：**

```
EN: <field> internship 2026 · <field> intern summer 2027 · new grad <field> program
    student program <company> · <field> placement year
CN: <方向> 实习 招聘 · <企业> 校园招聘 · <方向> 暑期实习 · 应届生 <方向> 提前批
JA: <分野> インターン 大学生 · <分野> 長期インターン · 新卒 <分野> 採用 ·
    学生向け プログラム · サマーインターン 選考
```

**注意：**
- 聚合站（招聘平台、LinkedIn）只用于**发现**；投递入口与截止日必须回官网确认。
- "研究型实习"同时属于 `research`，默认 primary 取 `career`、`research` 进 secondary。
- 校招时间线强绑定毕业年份（日本按「卒業年度」、中国按「应届生」），
  没有毕业年份时不要把往届信息当成有效机会。

---

## 2. `research` — 科研机会

**子类：** Research Assistant / 本科科研 / 科研实习 / Summer Research / 实验室项目 /
企业研究院 / 教授招募 / 大学生科研计划 / 开放课题 / 研究训练计划 / 论文合作 /
Poster / Workshop / 学术项目 / Visiting Student / Research Internship

**典型 Tier A 来源：** 大学实验室官网、教授个人主页（`*.edu`、`*.ac.jp`、
`*.ac.uk` 教員紹介）、院系"研究プロジェクト/招募"页面、企业研究院（R&D）页面、
学术组织官方公告（ACM/IEEE/SIG 等）。

**Query 模式：**

```
EN: undergraduate research program <field> · research assistant professor <field>
    summer research internship <field> · visiting student <field> · funded RA position
CN: <方向> 本科生科研 · 实验室 招募 本科生 · 科研助理 招聘 导师 · 大学生科研训练计划
JA: 学部生 研究 募集 <分野> · 研究室 配属 募集 · 研究インターン 学生 ·
    サマースクール 研究 <分野>
```

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

**Query 模式：**

```
EN: <topic> competition students 2026 · <topic> challenge open call ·
    <topic> hackathon worldwide · embedded design contest
CN: <方向> 大赛 报名 · 大学生 <方向> 竞赛 · <方向> 挑战赛 2026 · 创客大赛
JA: <分野> コンテスト 学生 · 学生 ハッカソン 2026 · アイデアコンテスト 学生 ·
    ロボコン 大会 募集
```

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

**Query 模式：**

```
EN: summer school <field> 2026 · master program <field> application ·
    exchange program university <field> · visiting student program
CN: <方向> 暑期学校 报名 · 夏令营 招生 简章 · 保研 夏令营 2026 ·
    联合培养 项目 申请
JA: サマースクール 募集 <分野> · 大学院 入試 募集要項 · 交換留学 募集 ·
    研究生 募集 大学
```

**注意：**
- 中国升学类信息受年份与政策影响大，把"哪一届"写清楚，避免把去年简章当本年机会。
- 海外项目必须单独核对语言成绩与财政证明要求，二者常是硬性条件。

---

## 5. `language` — 语言

**子类：** JLPT / TOEIC / IELTS / TOEFL / GRE / GMAT / CET / TOPIK / 其他语言考试 /
考试报名 / 模考 / 语言比赛 / 翻译比赛 / 演讲比赛 / 语言奖学金 / 语言交换 /
短期语言项目

**典型 Tier A 来源：** 考试主办方官网（JLPT 官方、ETS、IELTS 官方、CET 教务）、
使馆/文化机构（JASSO、Goethe、Alliance Française）、语言学校官方页。

**Query 模式：**

```
EN: <exam> test dates 2026 <country> · <exam> registration deadline
CN: <考试> 报名时间 2026 · <考试> 考点 报名 · 语言 比赛 报名 · 翻译大赛 报名
JA: <試験> 申込期間 · <試験> 日程 2026 · 語学 スピーチコンテスト 募集
```

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

**Query 模式：**

```
EN: student developer pack · free certification students <vendor> ·
    cloud credits students · startup credits program · university program <vendor>
CN: 学生 免费 认证 · 学生 云资源 申请 · 开发者计划 学生 · 教育优惠 开发板
JA: 学生 無料 資格 · 学生 開発者 プログラム · クラウド クーポン 学生
```

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

**Query 模式：**

```
EN: GSoC <topic> · open source mentorship program · good first issue <topic> ·
    <project> contributors wanted · paid open source internship
CN: 开源 之夏 项目 · 开源 实习 招募 · 开源社区 贡献 新人 · 悬赏 任务 开源
JA: OSS コントリビュート 初心者 募集 · オープンソース インターン ·
    メンタリング プログラム 募集
```

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

**Query 模式：**

```
EN: <brand> student program · <hobby> competition students ·
    <hobby> community event 2026 · <hobby> ambassador program
CN: <兴趣> 大赛 报名 · <兴趣> 校园 活动 · <品牌> 用户 计划 招募 ·
    创客 活动 报名
JA: <趣味> コンテスト 募集 · <趣味> 学生 プログラム ·
    <趣味> イベント 2026 参加者募集
```

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

**Query 模式：**

```
EN: <field> travel grant conference · student research grant <field> ·
    scholarship <field> international students · conference grant application
CN: 奖学金 申请 <方向> · 学生 科研基金 申请 · 会议 差旅 资助 ·
    交流 资助 项目 申请
JA: 奨学金 応募 <分野> · 学会 参加 助成 学生 · 研究 助成 申請 学生
```

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

**Query 模式：**

```
EN: <topic> conference students registration · developer conference 2026 free ·
    university open day <field> · career fair <field>
CN: <方向> 大会 学生 报名 · 技术大会 2026 · 校园宣讲会 <企业> ·
    开放日 实验室 报名
JA: <分野> カンファレンス 学生 参加 · 説明会 学生 予約 ·
    オープンキャンパス 研究室 公開
```

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

**Query 模式：**

```
EN: open innovation challenge students · company capstone project <field> ·
    build challenge hardware · civic tech project volunteers
CN: 命题 挑战 学生 · 企业 课题 招募 学生 · 开源 数据集 项目 参与 ·
    公益 技术 项目 招募
JA: 企業 課題 学生 募集 · オープンイノベーション 公募 ·
    プロジェクト メンバー 募集 学生
```

**注意：**
- 项目类最适合"想积累作品但不想被长期绑定"的用户（Mode B）。
- 交付物是否可公开（能否进作品集）是重要判断点，能查到就写进 `value.portfolio`。

---

## 12. `entrepreneurship` — 创业

**子类：** Startup Competition / Accelerator / Incubator / 校园创业 / 创业基金 /
创业训练营 / Demo Day / 创业团队招募 / 联合创始人招募 / 企业创新挑战

**典型 Tier A 来源：** 孵化器/加速器官网、创业赛官网、大学创业中心、
政府/园区创业扶持页。

**Query 模式：**

```
EN: student startup competition 2026 · university accelerator application ·
    incubator student founders · co-founder wanted student
CN: 大学生 创业 大赛 报名 · 校园 孵化器 申请 · 创业 训练营 招募 ·
    创业 基金 学生 申请
JA: 学生 起業 コンテスト 募集 · インキュベーション 学生 ·
    アクセラレータ 応募 学生
```

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

**Query 模式：**

```
EN: <company> mentorship program students · student chapter <society> ·
    campus ambassador program · alumni mentoring program
CN: 导师 计划 学生 申请 · 学生 分会 招募 · 校园 大使 招募 ·
    技术 社区 志愿者 招募
JA: メンター プログラム 学生 · 学生 支部 募集 · キャンパス アンバサダー 募集
```

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
