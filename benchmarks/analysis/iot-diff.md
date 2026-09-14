# IoT / Embedded — Round 2 Diff Analysis

Persona: `benchmarks/personas/iot-embedded.json`（IoT 大三，C/Python/ESP32，目标 日本+中国+远程）
Round 1: bare 4/10 useful vs **radar 3/8**（Radar 在自己的"主场"输给 bare —— F08）
Round 2（修复后重跑，同预算 6 搜索 + 6 抓取，today=2026-09-15）:

| | bare | radar |
|---|---|---|
| useful | 3/10 | 2/5 |
| radar-only useful | — | 2 |
| Recommended now | — | 3（2 条 verified_official，1 条官方未确认） |
| expired leakage | — | **0** |
| unverified actionable leakage | — | **0** |
| excluded | — | 15 |

> 注意：round 1 与 round 2 的 judge 不是同一次评审，打分口径不同（v2 judge 对过期项一律 elig=0、
> 对纯聚合站一律 trust≤1），所以 v1↔v2 的 useful 绝对值**不可直接比较**；本文件只比较同一轮内的
> bare vs radar，以及硬门槛（judge 无关，直接从 run 工件计算）。

## Radar 逐条复盘（5 条）

| 条目 | zone | trust | 判定 | 原因 |
|---|---|---|---|---|
| Okinawa Innovation Contest 2026 | recommended_now | 3 | ✅ useful | 官方页核实，开放中 |
| 全国大学生智能汽车竞赛（室外赛道） | recommended_now | **1** | ✗ | smartcarrace.com 返回无关内容（JS/反爬），截止日只有第三方来源 |
| openUBMC 开源实习 | recommended_now | 3 | ✅ useful | 官方页核实，rolling |
| ETロボコン 2026 | worth_verifying | 1 | ✗ | 官方页未抓到，deadline/资格未确认 |
| Tokyo 技术コミュニティ列表 | worth_verifying | 1 | ✗ | 第三方博客列表，无统一官方入口 |

## Bare-only useful（Radar 漏掉，3 条）

1. **Sharp 2026 Internship Program**（AIoT/嵌入式，trust=3）—— Radar 的 ja 查询没有覆盖到Sharp 校招页
2. **Espressif LEADER 嵌入式软件开发实习生**（ESP-IDF/Matter/Zigbee，trust=2）—— v1 时 Radar 抓 Espressif
   官网遇到 captcha；本轮 Radar 的 6 次 query 预算被 ja+zh+en 三语言摊薄，没再回到该页
3. **全国大学生物联网设计竞赛 2026**（ESP32 track，trust=3）—— v1 时 Radar 找到过；本轮该 query 的预算
   让给了日本侧

## Root cause（按证据，不按猜测）

1. **不是 query expansion 不足**：Radar 的 ja/zh 查询实际命中了 Okinawa、openUBMC、ETロボコン 等目标
   类型 —— expansion 方向正确。
2. **是验证预算 × 反爬的乘积问题**：6 次 fetch 中 1 次反爬、1 次无关内容、4 次成功；失败的那两次恰好
   是两个本可 useful 的条目（智能汽车竞赛、ETロボコン）。trust=1 直接使它们退出 useful 集合。
3. **是 6-query 预算在三语言间的摊薄**：ja+zh+en 每语言只有 2 次 query，Sharp/Espressif/物联网竞赛
   三个高价值目标没有轮到。

## 结论

- **F02 已修**（过期竞赛不再出现；expired leakage = 0）。
- **F08 部分改善**：不再"因为过期/聚合站污染而输"——本轮 Radar 的 precision（2/5 = 40%）高于
  bare（3/10 = 30%），但**绝对 useful 数仍低于 bare**（2 vs 3），缺口来自召回（漏 Sharp/Espressif/
  物联网竞赛），不是排序或污染。
- **不给 ESP32/Embedded 加权**（失败证据不支持）：问题在预算分配与验证预算，不在权重。

## 对应修复建议（进入下一轮 backlog）

1. 三语言场景下把 discovery query 预算提到 8–9 次，或要求 Agent 显式做"每语言至少 2 次"的分配。
2. 对反爬站点（smartcarrace 类）允许"跨来源交叉确认截止日"并把 verification_status 记为
   `partially_verified` 而不是直接 trust=1。
3. 为 v1 已验证命中过的官方域（espressif、sharp）建立"上一轮已核实来源"的复访优先级
   （state 层已有 seen.json，可加 `verified_domains` 复用）。
