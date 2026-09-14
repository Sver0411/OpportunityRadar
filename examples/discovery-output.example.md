# 输出格式示例（格式示意，数据为虚构）

> ⚠️ 本文件中的所有机会、机构、日期均为**虚构**，仅用于演示 `references/output-format.md` 的排版与信息密度。真实运行时必须使用联网搜索并回官方来源验证的结果。

对应输入：

```text
我是物联网工程大三学生，会 C、Python 和 ESP32，最近有什么值得参加的？
```

对应的 Mode A 输出：

---

按「物联网大三 + C / Python / ESP32 + 关注 Embedded / AI Agent」搜了一轮，
覆盖 竞赛 / 实习 / 科研 / 开源 / 学生资源 5 类，从 30+ 条候选里筛出 7 条值得看的
（含 2 条你可能不会想到去搜的方向）。画像里没写毕业年份和日语成绩，
这两项会影响校招类机会的资格判断，补上我能再筛一轮。

**1. Nagi Robotics Summer Internship 2027**
类型：Career / Embedded · 8 周全职，名古屋，有薪
为什么适合你：
- 接受本科生（官方页面：学部生・修士課程）
- 硬性技能 C / Git 与你现有技能匹配
- tags: embedded / robotics 与你的 Embedded、Robotics 兴趣重合
资格：Probably Eligible
截止：2026-10-03
注意：页面未写明语言要求（△）；需线下面试
价值：Career High / Portfolio High / Research Medium
官方来源：https://careers.nagi-robotics.example/students/summer

**2. Tokyo Embedded Challenge 2026**
类型：Competition / Embedded · 学生组，2–4 人
为什么适合你：
- 主题为嵌入式系统设计，直接对上 ESP32 经验
- 允许跨校组队，作品可公开 → 可进作品集
资格：Probably Eligible（△ 未写明是否接受国际学生）
截止：2026-10-20 ｜ 需组队
价值：Portfolio High / Skill High / Career Medium
官方来源：https://tokyo-embedded.example/challenge-2026

**3. Kagura University Undergraduate Research Program**
类型：Research / 实验室 · 6 个月兼职，有 stipend
为什么适合你：
- 明确面向本科生、2–3 年级
- Python 为偏好技能（非硬性）
资格：Unknown——页面要求 JLPT N2 以上，你尚未提供日语成绩（这是唯一卡点）
截止：2026-11-30
价值：Research High / Networking High / Financial Low
官方来源：https://www.kagura-university.example/research/undergrad-program

**4. Zephyr Project — good first issue（嵌入式开源）**
类型：Open Source / Embedded
为什么适合你：
- 项目维护者标注了面向新贡献者的 issue，语言 C
- 产出公开 PR → 是"公开项目经历"最直接的补法
资格：Eligible（无学历/年级限制）
截止：滚动（无截止）
注意：△ 需要能英文沟通（issue 讨论用英文）
价值：Skill High / Portfolio High / Career Medium
官方来源：https://github.com/example/zephyr-project

**5. TinyML Challenge（学生赛道）**
类型：Competition / Edge AI
为什么适合你：
- 主题 TinyML（ESP32 可用的边缘推理）与你 ESP32 + AI 兴趣的交叉点
- 提供免费开发板资源
资格：Probably Eligible（△ 页面未写是否限本国学生）
截止：2026-11-30
价值：Skill High / Portfolio Medium / Research Medium
官方来源：https://tinyml-challenge.example/2026

**6. GitHub Student Developer Pack（学生开发资源）**
类型：Skill Development / 学生资源
为什么适合你：云资源与开发工具免费额度，申请门槛仅需学生身份
资格：Eligible
截止：滚动
价值：Financial Medium / Skill Low
官方来源：https://education.github.com/pack

---

**另一个方向（你可能不会想到去搜这些）**
- Solutions Engineer / FAE 实习 — 需要嵌入式背景 + 会沟通，与你技能栈重叠，但岗位名与"嵌入式工程师"不同（Explore / Career）
- 农业 IoT 开放创新命题 — 企业出题、学生组队交付，比纯竞赛更接近真实项目（Adjacent / Project）
- Maker Faire 学生展位 — 把手上的 ESP32 项目变成公开作品与社群入口，门槛低（Explore / Event）
- 学生分会 / mentor 计划 — 低风险建立行业联系，适合现在还没有明确方向时先做（Explore / Networking）

**已见过（1 条）**
- Nagi Robotics Robot Hackathon — 上次推荐，截止未变

**有变化（1 条）**
- Kagura University Undergraduate Research Program — 截止由 11-30 改为 12-15（官方页面更新）；同时报酬字段由 stipend 变为 unpaid，建议重新确认

**下一步（你自己执行）**
1. 补上毕业年份与日语成绩，我可以对第 1、3 条给出确定性资格判断
2. 第 4 条可以这周挑一个 issue 留言；第 5 条报名先看团队限制
3. 需要的话我把这 7 条写成 JSON 存到 `.opportunity-radar/last-run.json`，下次自动过滤已推荐的

---

**未找到官方确认来源的条目**：无
**信息可能已过期**：Tokyo Embedded Challenge 2026（last_verified 2026-09-14，竞赛类阈值 14 天）
