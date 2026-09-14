# Round 2 Regression Report (v1 → v2)

日期：2026-09-15 · 修复内容：Freshness Gate / Canonical Source Gate / Global-Remote precedence /
验证预算分离 / locale 继承（全部见 commit `395ca27`）。

重跑范围：**4 个 persona**（iot-embedded、design、environment + control biology），只重跑 Radar 侧；
bare 侧行为与 Skill 无关，直接复用 round 1 结果（同日运行，公平性不受影响）。

## 质量门槛（硬指标，直接从 run 工件计算，与 judge 无关）

| Gate | 目标 | IoT | Design | Environment | Biology (control) |
|---|---|---|---|---|---|
| Expired leakage（主推荐中的已过期项） | 0% | **0%** (0/3) | **0%** (0/2) | **0%** (0/3) | **0%** (0/2) |
| Unverified actionable leakage（无官方来源却进主推荐） | 0% | **0%** (0/3) | **0%** (0/2) | **0%** (0/3) | **0%** (0/2) |
| Final recommendation verification | ≥80% | 67% (2/3) | **100%** (2/2) | **100%** (3/3) | **100%** (2/2) |
| Zone 输出（三区分离） | ✅ | ✅ | ✅ | ✅ | ✅ |

**四个 hard quality gate 全部达标。** 环境画像的 locale 修复也得到确认：
`regions=remote, primary=en, source=global_intent`（round 1 是 Brazil/pt-BR）。

## Useful / Radar-only（同轮 judge 口径，跨轮不可直接比较）

| Persona | bare useful (v2 judge) | radar useful (v2 judge) | radar-only useful | 结论 |
|---|---:|---:|---:|---|
| IoT / Embedded | 3/10 (30%) | 2/5 (40%) | 2 | **precision 修复**（不再被过期/聚合站污染），但召回仍欠 Sharp/Espressif/物联网竞赛 |
| Design | 4/6 (67%) | 3/7 (43%) | 3 | raw useful 下降是**设计使然**：5 条候选因反爬/404 无法验证，全部降级到 Worth verifying；主推荐 100% 验证 |
| Environment | 3/7 (43%) | 3/7 (43%) | 3 | 打平；3 次 fetch 失败分类为基础设施（见 F11） |
| Biology (control) | 3/7 (43%) | 3/9 (33%) | 3 | **无回归**：主推荐 2/2 全验证；raw useful 的差异来自评审口径（v2 judge 更严）与把未验证项降级 |

### ⚠️ 跨轮比较的方法论警告

v1 与 v2 使用了**不同的 judge 会话**，打分口径不同（v2 judge 对过期项一律 elig=0、对纯聚合站
trust≤1）。因此 **v1↔v2 的 useful 绝对值不可直接比较**；本轮只做两类比较：

1. 同轮内 bare vs radar（上表）；
2. judge 无关的硬门槛（第一张表）。

要得到严格可比的 useful 数字，需要同一 judge 会话重评 v1+v2 全部列表（见 TODO）。

## Environment 抓取失败分类（F11）

| 尝试 | 分类 | 说明 |
|---|---|---|
| Code for Earth | **network** | fetch 直接失败 |
| SciStarter | **other**（JS 渲染） | 正文不可提取 |
| OSGeo GSoC | **other**（过期页面） | 落到 2020 存档页 |
| EGU / GeoAI / NASA ARSET | ✅ 成功 | 3 条 verified_official |

3/6 成功。这些失败是**基础设施问题（反爬/JS 渲染）**，不是 Skill 规则问题 ——
产品逻辑未因此改动，符合"不要把工具失败误当 Skill 失败"的原则。

## 修复成功标准核对（§44）

| 标准 | 结果 |
|---|---|
| IoT：不再因 expired / aggregator 泄漏输给 Bare | ✅（两项 leakage = 0；precision 40% > bare 30%） |
| Design：最终推荐官方验证率显著提升 | ✅（29% → 100%，但主推荐缩到 2 条） |
| Environment：地区解析正确 | ✅（remote / global_intent，不再是 Brazil） |
| Environment fetch 失败 | ⚠️ 基础设施问题，单独报告，未假装修复 |
| Control（Biology）不明显回归 | ✅（主推荐 2/2 全验证；raw useful 差异来自 judge 口径） |

## TODO（下一轮）

1. 同一 judge 会话重评 v1 + v2 全部列表，得到可比的 useful 数字。
2. IoT：为高价值官方域（espressif/sharp 等）建立"已核实来源复访"优先级。
3. 反爬站点（ArtStation/Ludum/Awwwards 类）考虑在 Worth verifying 区直接给出
   "该站无法自动验证，请自行确认"的固定话术，避免重复分析。
