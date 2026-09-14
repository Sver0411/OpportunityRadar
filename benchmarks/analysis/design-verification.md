# Design — Verification Regression Analysis

Persona: `benchmarks/personas/design.json`（设计大三，法国 + 远程/全球）
Round 1: bare 验证率 83%（5/6）vs **radar 29%（2/7）** —— 雷达侧验证率反而低，F09。
Round 2（修复后重跑，同预算）:

| | bare | radar |
|---|---|---|
| n | 6 | 7 |
| Recommended now | — | **2（2/2 = 100% verified_official）** |
| Worth verifying | — | 5（全部 fetch 失败或 404） |
| excluded | — | 15 |
| expired leakage | — | **0** |
| unverified actionable leakage | — | **0** |

## Round 1 为什么只有 29%

逐条复盘 round 1 的 7 条（对照 `benchmarks/runs/design/bare.json` 的 bare 侧）：

| 原因分类 | 条目 | 说明 |
|---|---|---|
| fetch 失败（反爬） | ArtStation Challenges | Cloudflare 拦截 |
| fetch 失败（重定向） | Ludum Dare | Akamai 重定向到无效 URL |
| 404 | Kenney Jam（kenney.nl/jam） | 页面不存在 |
| fetch 失败（反爬） | Awwwards | 403 Forbidden |
| future cycle | Global Game Jam 2027 | 2027 周期，未到申请窗口 |
| verified ✅ | Origin CG、DNA Paris | 官方页核实成功 |

分类结论：**5/7 是"官方站点难以抓取"类（反爬/404/重定向），2/7 是周期问题**。
不是"官方来源没搜"，也不是"query 太宽"——是**验证环节被反爬卡住**。

## Round 2 的变化

- 预算拆分生效：6 次 fetch **全部用于验证**（0 discovery），不再被发现挤占。
- Recommended now 收缩到 2 条，**2/2 = 100% verified_official**（Origin CG 2026、DNA Paris 2027）。
- 抓取失败的 4 条 + 1 条 future cycle + 1 条 GGJ(trust=2) 全部进 Worth verifying，并标注
  "未找到官方确认来源 / 反爬 / 404"。
- Freshness Gate 排除了 13 个已关闭的 2026 赛事 + 2 个资格不符。

## 诚实结论

- **F09 部分修复**：最终推荐验证率 29% → **100%**（round-2 目标达成），但代价是主推荐只有 2 条。
- **raw useful 数下降**（6/7 → 3/7）：round 2 的 judge 对"fetch 失败 = trust 1"执行得更严格，
  且 Radar 按 gate 把未验证项降级，导致 useful 集合缩小。这是**设计使然**：
  "宁可少推荐，也不要推无法确认的机会"（v0.2-beta 的核心质量标准）。
- **未解决**：ArtStation / Ludum Dare / Awwwards 这类对自动化抓取不友好的站点，当前工具链无法验证。
  这是基础设施限制，不是 Skill 规则问题 —— 记为已知限制，进 `benchmarks/failures/F11`。

## 已知限制（Beta 可接受）

- 反爬站点（Cloudflare/Akamai/403）无法用当前 WebFetch 验证 → 这些机会只能进 Worth verifying，
  并明确告知用户"未能验证，请自行确认"。
- 严格 judge 下 bare 与 radar 的 useful 差距主要来自 bare 敢于不验证就推荐 —— 这正是两个产品的
  语义差异：bare 给"看起来相关"的列表，Radar 给"确认过还能申请"的列表。
