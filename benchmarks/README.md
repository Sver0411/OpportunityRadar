# OpportunityRadar Benchmark

目的：验证 OpportunityRadar 在**真实互联网**上是否比"普通 Agent + 帮我找机会"更有价值。
不是功能演示，不是单元测试。

## 公平性规则（A/B 唯一变量 = Skill）

两边必须完全相同：同一个 Agent、同一模型、同一时间窗口、同样的 web 能力（WebSearch + WebFetch）、
同一份 Persona 画像、同一提问意图、**同样的搜索预算（每模式最多 6 次 web 搜索 + 必要的页面抓取）**。
不允许给任何一方更多搜索次数、更好的提示词、或事后人工删除某一方的垃圾结果。

- **A — Bare Agent**：不加载 Skill。只给画像 + "Find current opportunities worth their attention."
- **B — OpportunityRadar**：加载 Skill（协议 + references + scripts）。问："最近有什么真正值得我关注的机会？"

## 目录

```
benchmarks/
├── README.md          # 本协议
├── RUBRIC.md          # 评分标准
├── personas/          # 8 个 FICTIONAL TEST PERSONA
├── runs/<persona>/    # bare.json 与 opportunity-radar.json（原始记录）
├── failures/          # 真实失败案例
└── REPORT.md          # 结论
```

## 指标

每条机会按 RUBRIC 评 5 项（0–3）：Relevance / Eligibility / Trust / Novelty / Actionability。
`useful = Relevance>=2 且 Trust>=2 且 Actionability>=2`。
**Radar-only useful opportunity**：useful 且只出现在 OpportunityRadar 一侧 —— 本项目最关键指标。

## 已知局限（必须诚实）

- 评审（Judge）是同一个模型家族，虽然做了匿名化处理，但不是真正独立的人类评审。
- 搜索预算被人为限制（6 次）以保证可比性，真实使用可以更充分。
- 抓取的是 2026-09-14 前后的互联网快照；机会具有时效性，结果不可长期复现。
- 未收录地区/语言的 Persona 更依赖页面语言检测，效果可能偏低。
