# Output Format

Step 13 的执行规范。默认**简洁**：用户要的是"哪几个值得看、为什么"，不是研究报告。

---

## 1. 整体结构

```
[1 行标题]        说明本轮怎么搜的（模式 / 覆盖类别 / 数量）
[3–6 条完整块]    最值得看的
[另一个方向]      Adjacent & Explore 组（单行列表 + 一句理由）
[已见过 / 有变化]  仅在有本地 state 且存在变化时出现
[能力缺口快照]    仅 Mode D 或用户问"我缺什么"时出现
[下一步]         1–3 条可执行动作（用户自己做，不是我代做）
```

标题行示例：

> 按「物联网大三 + C/Python/ESP32 + 关注 Embedded/AI Agent」这一轮覆盖了
> 竞赛 / 实习 / 科研 / 开源 / 学生资源 5 类，筛出 7 条值得看的（含 2 条你可能没想到的方向）。

需要让用户理解"这轮为什么这样搜"时，**描述行为而不是内部模式名**：

```
✅ 这轮降低了求职类权重，更侧重竞赛、开源和项目。
✅ 这次多找了一些非传统方向（你可能不会主动搜的岗位名与项目类型）。
❌ 模式：B（非求职向）
❌ Mode C
```

A/B/C/D 只是内部执行模型，用户不关心协议名称；只有调试输出才暴露它们。

---


## 1.1 三个输出区（必须分开，不能合成一个列表）

```
Recommended now     ← 现在值得申请（Freshness Gate + Canonical Gate 都通过）
Worth verifying     ← 有价值，但状态/来源/资格未确认，需要继续核实
Closed / Excluded   ← 已过期/已结束，或明确不符合资格（附原因）
```

进入 **Recommended now** 的最低条件（`scripts/score.py` 的 `recommendation_zone()` 已实现）：

1. `freshness ∈ {open, likely_open}`
2. 有 canonical source（`official_url` 非空）
3. `eligibility_verdict != Ineligible`
4. `match_score >= 55`（最低质量门槛）

其余进入 **Worth verifying**（`freshness = unknown`、无官方来源、match 偏低）。
`closed` / `expired` / `Ineligible` 进 **Closed / Excluded** 并写明原因。

**Unknown 不是负面**：`Eligibility = Unknown` 只表示信息不足，它可以出现在 Worth verifying，
并列出"补上什么信息就能确认"。

## 2. 完整块模板

```
1. <官方名称>（<中文/英文简注，可选>）
   类型：<primary_category> / <关键技术或子类>      ← 可加 secondary
   为什么适合你：
   - <依据 + 与画像的连接>
   - ...
   资格：<判定>（<决定性依据>）
   截止：<YYYY-MM-DD 或 "滚动招募">
   注意：<真正会改变决定的不确定性>
   价值：Career High / Portfolio Medium / Research Unknown
   官方来源：<url>          ← 找不到就写 "未找到官方确认来源（仅第三方）"
```

**长度纪律**：单块 ≤ 10 行；不写背景介绍、不写行业分析、不写"建议尽快准备材料"这类空话。

**多行变体**（信息很多时，仍然只保留会改变决定的行）：

```
3. <名称>
   类型：Competition / Edge AI
   为什么适合你：- 接受本科生 - 要求 C++/Python - 与 TinyML 兴趣重合
   资格：Probably Eligible △ 未写明是否允许跨校组队
   截止：2026-11-30 ｜ 需 3 人组队 ｜ 奖金 $10k
   官方来源：<url>
```

---

## 3. Adjacent & Explore 组

这一组的写法是**单行 + 一句理由**，明确标出"你可能不会想到搜这个"：

```
另一个方向
· <机会名> — <一句理由>（Open Source / 远程）
· <机会名> — <一句理由>（Project / 企业命题）
· <机会名> — <一句理由>（Networking / 门槛低，适合先建立联系）
```

如果这一组确实为空（试过 Adjacent / Explore 但没有达到质量与验证门槛的条目）：

> 这一轮没找到合适的非传统方向条目（试过 <哪些类/哪些层>，但没有通过质量/来源门槛的）。

**如实说明即可，不要用弱机会凑数**。这一组是 OpportunityRadar 与普通搜索的核心差异之一，
所以即使为空也要交代一句，不要静默省略。

---

## 4. 已见过 / 有变化

```
已见过（3 条）
· <名称> — 上次推荐，截止未变
有变化（1 条）
· <名称> — deadline 由 10-03 改为 10-17（官方页面更新）
```

规则：`seen` 且无变化 → 只列名，不重复写理由；
有变化 → 完整块 + 写明**变化了什么**。

---

## 5. 能力缺口快照（Mode D / "我缺什么"）

```
能力缺口（基于本次扫描到的 23 条嵌入式方向机会）
· RTOS 出现在 9 条要求中（其中 4 条为硬性要求）
· 英语成绩出现在 7 条
· 公开项目/作品集出现在 6 条（多为"优先"）
· 日语 N2 以上出现在 5 条

对应可参与的机会
· <竞赛/项目/开源/认证机会> — 直接产出 <RTOS 使用经验 / 公开仓库 / 成绩>
```

**话术铁律**：
- ✅ "在本次扫描到的 23 条机会中，RTOS 出现于 9 条"
- ❌ "学 RTOS 能多 9 个机会" / "学 RTOS 就能拿到 offer"
- ❌ "你必须考 N2"

必须注明这是**当前发现结果**的统计，不是全市场结论。

---

## 6. JSON 产物（可选但推荐）

把本轮结构化结果写入 `.opportunity-radar/last-run.json`：

```json
{
  "run_at": "2026-09-14",
  "mode": "A",
  "profile_snapshot": { "...": "本次实际使用的画像（含 null）" },
  "categories_searched": ["career", "competition", "research", "open_source", "skill_development"],
  "queries_used": ["...", "..."],
  "opportunities": [ { "...": "符合 schemas/opportunity.schema.json" } ],
  "excluded": [ { "id": "...", "reason": "ineligible: 要求 2027 年 3 月毕业" } ],
  "unverified": [ { "id": "...", "reason": "未找到官方确认来源" } ]
}
```

用途：下一轮可对比、可做 Seen State、可做缺口统计。写入前告知用户写到了哪里。
如果用户的工作目录不可写 → 跳过，不影响主输出。

---

## 7. 语言与格式

- 用**用户的语言**回答；项目/机构/URL 保留原文，必要时加短注。
- Markdown 层级不超过两层；不用大表格堆信息（列表更易读）。
- 日期统一 `YYYY-MM-DD`；跨年不确定的写"9月20日（年份未标明）"。
- 金额保留原币种与原文（`$10,000`、`10万円`、`￥5,000`），需要时加约等换算并标明是换算值。
- 资格判定名与 Trust/Verify 状态用规范词（`Probably Eligible`、`partially_verified`）。

---

## 8. 输出反模式

- ❌ 100 条链接清单。
- ❌ 每条 300 字的长篇分析。
- ❌ 把第三方的日期当成官方日期，不标注。
- ❌ 结果里没有一条 Adjacent / Explore。
- ❌ 把分数（87.3）当结论展示；应给档次 + 理由。
- ❌ 结尾自动"帮你投递/发邮件"。应当只给用户可自己执行的动作。
- ❌ 用"含金量高""强烈推荐"代替依据。
