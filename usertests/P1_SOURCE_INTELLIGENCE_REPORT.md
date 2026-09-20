# P1 报告：最小版 Source Intelligence

日期：2026-09-20 · 基线 `0815d5c` · 范围：**只**解决已确认的三个召回缺口
（Research Bridge / Language Bridge / Open-source Foundation Entry）
测试：**344 → 356 全绿** · 指标脚本：`usertests/_si_metrics.py`

---

## 1. Source Intelligence 数据模型

**定位**：不是网址收藏夹，也不是白名单搜索器。它只回答：

> 已经识别出某个 Gap 时，这类 Bridge 通常藏在**哪一类官方来源**里、应该先发什么 query。

```
Gap Type → Bridge Intent → Source Family → Targeted Query → general search fallback
```

- **代码（唯一事实来源）**：`scripts/sources.py` —— `SOURCE_FAMILIES`（18 个 family）、
  `GAP_TO_BRIDGE_INTENT`、`INTENT_TO_FAMILIES`、`STAGE_INTENT_OVERRIDES`、`plan_queries()`、
  `SOURCE_FAILURE_TYPES`、`record_yield()`。
- **参考文档**：`references/source-families/{README,research,language,oss}.md`
  （family 表、页面类型、query intent、canonical 判断方式、缺口细分）。
- **本地状态（可选、极轻）**：`.opportunity-radar/sources.json`
  只存 `source / category / region / runs / last_checked / last_success / historical_yield / failure_type`。
  **不缓存搜索结果、不存网页内容、不存隐私**（有测试断言 json 中不含 content）。

**硬纪律**：来源不提升可信度 —— 来自 known source 的候选仍要过 canonical source / freshness /
application-status evidence / eligibility / dedupe / readiness / utility / bridge gate。

## 2. Source Family 定义

| 组 | families |
|---|---|
| Research（8） | `university_lab`, `professor_page`, `research_seminar`, `summer_research`, `research_institute`, `academic_society`, `research_funding_body`, `graduate_school` |
| Language（6） | `official_exam_body`, `university_language_center`, `government_cultural_body`, `language_exchange_program`, `speech_contest`, `scholarship_language_program` |
| OSS Entry（8） | `foundation`, `mentorship_program`, `working_group`, `contributor_guide`, `community_event`, `maintainer_program`, `project_repository`, `bounty_program` |

每个 family 记录：适用 gap 类型、常见页面类型、query intent 模板、canonical-source 判断方式、
是否领域/地区敏感。**共 18 个 family，不是全球来源数据库。**

## 3. Gap → Bridge Intent → Source Family 映射

`GAP_TO_BRIDGE_INTENT`（12 类缺口）→ `INTENT_TO_FAMILIES`（每类 2–4 个 family）。
**不存在"Gap → query 字符串"的直连**（有测试断言必须经过 intent 层）。

| 缺口 | Bridge Intent | 优先 family |
|---|---|---|
| `network`（教授接触） | professor / community contact | `research_seminar` → `professor_page` → `academic_society` |
| `research`（研究经历） | hands-on research evidence | `summer_research` → `research_institute` → `university_lab` |
| `language` | certified language evidence | `official_exam_body` → `university_language_center` → `speech_contest` |
| `portfolio` | public verifiable artefact | `contributor_guide` → `mentorship_program` → `foundation` |
| `public_reputation` | visible public impact | `community_event` → `maintainer_program` → `working_group` |
| `leadership` | visible ownership | `working_group` → `maintainer_program` → `foundation` |

**阶段敏感**（`STAGE_INTENT_OVERRIDES`）：在职者的研究 Bridge 是
`part-time research programme` / `industry-academia collaboration` / `open seminar working professionals`；
本科生才是 `summer research programme undergraduate`。`stage_of()` **在职优先**，
不会被 `career_stage=graduate_student` 拉回学生视角（有测试）。

## 4. 三类实现要点

- **Research**：按缺口细分（缺教授接触 ≠ 缺研究经历 ≠ 缺研究产出），canonical 判断用学术域名
  （`.edu/.ac.jp/.ac.uk/.edu.cn/.uni-*.de`）+ 院系/实验室页面；聚合站只作 discovery。
- **Language**：目标不是"推荐语言课程"，而是找到**可认证的语言证据**；`speech_contest`
  这类能把语言转成公开证据（同时补 `portfolio`/`public_reputation`）。
- **OSS Entry**：覆盖基金会程序 / 社区页 / mentorship / 工作组 / SIG / contributor ladder /
  治理页 / 社区日历，而不是只搜 `good first issue`。ecosystem 由**用户领域**决定
  （有测试断言同一 family 在不同 topic 下生成不同 query，CNCF 只是种子示例）。

## 5. known-source 与 general fallback 策略

- 每个候选记录 provenance：`known_source` / `source_family_query` / `general_search` / `adjacent_discovery`
- registry 没有的来源**照常发现**（有测试：未知缺口会回落到 general search；`registry_coverage()` 明确声明"不会被排除"）
- `historical_yield` 只用于**同预算下先扫历史有效的来源**，不能因此停止搜索其他来源（Explore 预算保留）
- 失败类型沿用三分类：`process`（source_not_found）/ `fact`（source_found_no_opportunity、
  source_found_not_current）/ `infrastructure`（page_not_verifiable、js_rendered、blocked）

## 6. Before / After 指标

**规划层**（`_si_metrics.py`，5 场景）

| 指标 | before | after |
|---|---|---|
| `source_plan_coverage`（有来源计划的缺口占比） | n/a（无该层） | **1.00** |
| `source_family_hit_rate`（计划中命中 family 的 query 占比） | 0（全部 general） | **1.00** |
| `general_search_fallback_rate` | 1.00 | **0.00** |
| `bridge_verified_rate` | 1.00 | **1.00**（未下降） |
| `bridge_actionable_rate` | 1.00 | **1.00**（未下降） |
| `portfolio_resource_conflict_rate` | 0.00 | **0.00** |

**Case 层（真实联网）**

| Case | gaps | 有桥缺口 | gap_coverage | bridges | verified | actionable | family 占比 | general 占比 | Portfolio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| C 升 Senior | 16 | 9 | 0.562 | 7 | 0.857 | 0.571 | **0.857** | 0.143 | 3.0h / 5h，无冲突 |
| D 在职申硕 | 8 | 6 | **0.75**（上轮 0.50） | 8 | 0.875 | 0.625 | 0.75 | 0.125 | 预算未知 → 见第 9 节 |
| E 无目标 | 0 | 0 | —（无缺口，正确） | 0 | — | — | 0.222 | 0.667 | 预算未知 |

> `gap_coverage_rate` 的目标值**没有调整**（上一轮记录的是 0.64；本轮真实提升体现在 Case D 的
> 研究类缺口，因为那是本轮唯一改动的来源族）。

## 7. T3 / Case D research coverage 是否改善

**是：0.50 → 0.75。** 具体：

- 8 个 family 中 **6 个产出可用（非 undergrad-only）项**：`university_lab`、`research_seminar`、
  `graduate_school`、`research_funding_body`、`official_exam_body`、`academic_society`
- `professor_page` 经由"研究生（research student）内諾"路径覆盖
- research / network / language 三个研究相关缺口**全部**由在职友好的已验证官方源桥接
- 唯一未桥接的是 `experience`（"不脱产也能获得的真实研究经历"确实稀缺 —— 这是事实，不是搜索问题）
- 官方 lab / professor 页面**没有被 JS 渲染或反爬**（ois / cst / weblab / studyinjapan 均正常抓取）

## 8. 新发现的召回失败

1. **family 与阶段错配**：`summer_research` 对在职者只产出学部生项目（UTRIP 等）→
   该 family 对 working 阶段实际不可用。需要在规划层对"阶段 × family"做可用性标注。
2. **`research_institute` 命中陈旧页面**：只找到旧 PDF（stale，未能验证）→
   研究所类来源需要"当前期次"判据（与 freshness 联动）。
3. **Gap 噪声压低覆盖率**：Case C 报了 16 个 gap，其中包含 `slack`/`github profile` 这类
   **手续类前置**，把覆盖率分母灌大（0.562 被低估）。**本轮已修**：`gaps.is_logistics()`
   过滤手续类前置并单独记录在 `logistics_prerequisites`（不静默丢弃）。
4. **Case E 的 4 个候选沿用上轮未重抓**（LFX/GSoC/Outreachy/Recurse）→ provenance 上仍记为 process。

## 9. Infrastructure failures

| 来源 | 现象 | 分类 |
|---|---|---|
| JLPT 官方 PDF | WebFetch 取不到文本（只能靠搜索摘要） | infrastructure |
| OpenSSF `/mentorship/` | 404，2027 日期只能推断 | infrastructure |
| LFX 平台页 | JS 渲染（上轮已记录，本轮仍存在） | infrastructure |
| play.picoctf.org | Cloudflare 拦截（上轮已记录） | infrastructure |

**没有**出现"官方页打不开就拿第三方当官方证据"的情况。

## 10. 是否产生 source bias

**没有，且有机制保证**：

- Case E 的 family 占比只有 **0.222**（general_search 0.667 + adjacent 0.111）——没有收敛成白名单搜索
- 未知缺口会回落到 general search（测试覆盖）
- ecosystem 由 topic 决定，不写死 CNCF（测试覆盖）
- 规划层 `general_search_fallback_rate` 在合成场景为 0 是因为那些场景都有对应 family；
  **真实 E 场景仍是 general 主导** —— 说明 SI 只在该起作用的地方起作用

## 11. C / D / E 端到端回归（链：Profile→Discovery→SI→Verification→Gap→Bridge→Graph→Utility→Portfolio→Answer）

三组全部跑通整链，SI 记录同样过真实 gate（`_apply_gate.py --record record-si.json`）：

| Case | gate 计算 | 说明 |
|---|---|---|
| D | recommended=4 / worth_verifying=3 / excluded=1 | 1 处手工标注被 gate 修正（IPSJ 学会 rolling 无固定窗口），已按 gate 改正并保留原标注 |
| C | recommended=4（与上轮持平，构成更贴升 Senior：SIG contributor 替代 CKA） | 6/7 候选来自 source family |
| E | recommended=1 / worth_verifying=6 | 缺口为空（未制造目标） |

## 12. 用户最终答案前后差异

- **C**：数量不变（4 条），但构成从"3/4 属社区/会议"变为 **4/4 属工作组/维护者/CFP/贡献者**，
  更贴合"不跳槽、升 Senior"；两个维护者/导师项因缺 evidence 被诚实降级。
- **D**：研究型 Bridge 从"仅 1 条"变为**多个真实在职友好路径**（研究生制度、实验室公开讲义、
  JASSO/MEXT 资助、JLPT），回答从"只有在线硕士"变成
  "缺口 → 桥接 → 产出证据 → 打开什么"的完整链。
- **E**：候选 7 → 10，纳入 9 → 9，**1 条被明确拒绝为弱项**（过期 CFP）；答案仍以
  开源贡献/带薪导师制/漏洞赏金为主，没有退化成"实习+竞赛+课程"。

## 13. 是否值得继续扩大 Source Intelligence

**暂时不值得大扩**，理由：

- 真实收益集中在**研究类**（0.50 → 0.75）；语言类与 OSS 类的增益主要体现为**构成更准**而非数量更多
- Case C 的 recommended 数量与上轮持平 → 说明该场景的瓶颈是**候选质量/证据**，不是来源覆盖
- 已暴露的两个新问题（family×阶段错配、陈旧页面判据）属于**规划层规则**，不是"来源不够"

**判断瓶颈**：三项确定（现有数据即可判断）——
① **Query Budget**：D/E 的 portfolio 因预算未知/候选多而膨胀，说明是预算与收敛问题；
② **证据完整性**：C/D/E 仍有大量候选缺 application-status 证据（process 类失败）；
③ **Opportunity 本身稀缺**：如"在职者不脱产的真实研究经历"确实稀少，扩大来源库也解决不了。

## 14. 下一步建议

1. **阶段 × family 可用性标注**（新发现，优先）：`summer_research` 对 working 不可用 →
   规划层按 `life_stage` 过滤 family 并输出 `family_stage_fit`。
2. **陈旧页面判据**：`research_institute` 类来源需要"当前期次"证据，否则记为
   `source_found_not_current`（fact）。
3. **重跑 C（修完 gap 噪声后）**：验证 `gap_coverage` 在过滤手续类前置后的真实值。
4. **预算收敛**：预算未知时不应给出 36h/107h 级计划（本轮已改为 `budget_unknown=True` +
   `resource_conflict=None`，指标只统计预算已知的组合；建议再加"预算未知时最多给 3 条并提示确认"）。
5. 仍待处理：IoT 最终验证 67% < 80%（`benchmarks/known_failures.json`，声明的 FAIL）。
6. **不建议**现在扩大 registry：先做 1–3，再决定是否需要更多 family。

---

### 诚实结论

Source Intelligence 在**研究类缺口**上带来了真实可测的召回提升（0.50 → 0.75），
没有降低真实性门槛，也没有产生 source bias；但它在**数量**上的增益有限，
主要价值是**构成更准 + provenance 可追踪**。瓶颈已从"来源不够"转移到
**预算收敛、证据完整性、以及部分机会本身稀缺**。
