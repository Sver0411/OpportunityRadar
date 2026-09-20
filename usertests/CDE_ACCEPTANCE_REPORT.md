# C/D/E 综合验收报告（V3 P0，真实联网）

日期：2026-09-20 · 顺序：D → C → E · 每组都用真实公开机会 + 官方来源核实 + **真实 gate 重算**
产物：`usertests/case-d-japan-masters/`、`usertests/case-c-promotion/`、`usertests/case-e-unknown/`
工具：`usertests/_audit_cases.py`（审计）、`usertests/_apply_gate.py`（用 `score.py` 重算分区）

> 本报告里的所有分区数字都来自 **`score.py` 的真实 gate**，不是运行者的手工标注。

---

## 一、通过的能力

| 能力 | 证据 |
|---|---|
| 混合人生状态（D） | `working + return_to_school` 并存，未塌缩成 "worker OR student"；搜索覆盖 education/funding/language/research 四类 |
| 非求职路径（C） | 招聘类机会占比 **0/6**；产出全部是 CFP / 开源 maintainer 阶梯 / 技术委员会 / 社区 lead / 认证 / 导师制 |
| Unknown-Unknown（E） | 相邻维度覆盖 **7/7**（field/role/opportunity_type/community/institution/career_path/geography）；"实习+比赛+课程"仅 1/6 |
| 不编造画像 | 三组分别保留 9 / 7 / 16 个字段为 Unknown，未出现"用户没说却当成已知" |
| 时效门 | D 组 2 条过期项被真实 gate 判为 excluded（YLP 2026-09-18、JASSO 2025-11-27） |
| 官方来源门 | D/C/E 的**主推荐区**无一条缺 official_url（D 的 3 条手工主推荐被 gate 降级，见下） |
| 新增 V3 字段确实改变输出 | C 组 outcome facets 把 CFP 的 match 从 48 抬到 73 → 从"永远进不了主推荐"变成可推荐；E 组 7/7 相邻维度由 `unlocks/goal_contribution/optionality` 驱动 |
| Utility ≠ Match（C） | 高 match 的长期资本型机会 Utility=medium（"值得做但不是本周最急"），信息与 Match 不同 |
| 覆盖说明诚实（E） | 明确写出深扫/浅扫方向，未声称全量扫描 |

**C 组回归重跑（修复后）**：真实 gate 计算出 **recommended_now = 3**（KubeCon CFP、CNCF 贡献者路径、CKA/CKAD/CKS），worth_verifying = 4，excluded = 0；5 次 fetch 中 3 次成功并记录了 explicit evidence，2 次失败（404 / 登录墙）**如实降级、未伪造**。

---

## 二、失败 / 退化

| # | 现象 | 组 | 性质 |
|---|---|---|---|
| 1 | 运行者手工标注了 9 条 `recommended_now`（D 3 / C 6 / E 6），**真实 gate 一条都不认**（D 3→0、C 6→0、E 6→0） | D/C/E | **P0（协议 + 验证工具缺失）** |
| 2 | 全部候选缺少 `evidence.application_status`（D 11/11、C 7/7、E 10/10）→ 主推荐区**不可达** | D/C/E | **P0（同上根因）** |
| 3 | 2 条已过期机会被放进 "值得核实" 且未标"已截止" | D | **P0（输出信任）** |
| 4 | 单元级：CFP/开源/社区类机会 match 恒定 48 < 55 → 永远进不了主推荐 | C/E | **P0（V3 字段没参与打分）** |
| 5 | `open_source` / `networking` / `public_speaking` 三个职场兴趣词**完全缺失** → CFP/社区类兴趣命中率 0 | C/E | **P0（同上根因）** |
| 6 | `effort` / `cost` 写成字符串时 `readiness`/`utility` 直接抛异常 | D | P0（健壮性，已修） |

**没有**出现：student-only 退化、job-board-only 退化、编造画像字段、过期项进入**主推荐**、未验证项进入**主推荐**。

---

## 三、搜索召回问题

- **D**：语言准备、研究桥接、企业资助三个方向只做了浅扫（7 次搜索被"在职硕士/专业奖学金"吃满）；career continuity / networking 方向 0 条专门 query。
- **C**：社区类（CNCG Singapore）与导师制（LFX）各只有 1 次 query；专业协会（ACM Singapore）未能找到官方页。
- **E**：讲者/CFP、REU（研究型）、技术写作、专业学会 4 个方向仅浅扫；geography 维度只以用户自身 US+remote 为镜头，没有扩展到新地区。
- 共性：**一次运行只能深扫 3–5 个方向**，其余必须如实标注浅扫（已做到，但用户可能高估覆盖面）。

## 四、验证问题

- **反爬/404 是当前最大验证瓶颈**：CNCG Singapore（JS 重定向）、LFX Mentor（登录墙）、OpenSSF 专页（404）→ 4 条候选因此只能停在 worthy-verifying。
- 预算约束下"验证 vs 发现"仍会互相挤压：D 组 5 次 fetch 用在 4 条候选上，日语页面可读性差导致语言类候选未验证。
- 好消息：**没有任何一次伪造 verified_official**；失败一律如实降级。

## 五、决策逻辑问题

1. ~~V3 字段不参与打分~~ → 已修（outcomes 参与 goal_fit/interest_fit；`networking`↔`network` 的 facet 别名）。
2. ~~Utility 不影响推荐~~ → 已修（`recommended_now` 现在允许 `Utility=high` 作为 match 门槛的替代路径，否则渐进式画像下主推荐区不可达）。
3. **rolling/evergreen 的 freshness 仍易判 unknown**（CFP 周期、maintainer 路径、常设导师制）：这类机会"随时可参与"，但缺 deadline 结构时会被降级 → 需要"页面明确写 rolling/常设 → likely_open"的证据规则（P1）。
4. **专业资本维度使用不均**：D 未使用 `career_capital` / `future_optionality`（对在职申硕本应有用）；E 未使用 `career_capital`。

## 六、输出体验问题

1. D 组把过期项放进"值得核实"却没有"已截止"标签 —— 分区正确性依赖运行者，不依赖 gate。
2. E 组"小赌注"覆盖不均：low_cost / network 两类为空（3 条 public_output、2 条 high_upside、1 条 interest_asset）。
3. 追问质量好（D 问本科专业与日语水平、C 问技术栈与开源史、E 问愿意投入的时间），但**没有在回答里先给"补上 X 就能确定资格"的清单**（E 的 SFS/Outreachy 美籍/身份门槛因此停在 Unknown）。

---

## 七、P0 必须修复项（本轮已修 + 回归）

| # | 修复 | 证据 |
|---|---|---|
| P0-1 | **V3 outcome facets 参与打分**：`goal_component` 支持跨类别命中（`outcomes.network=high` → 命中 networking 目标），并加 `networking↔network` facet 别名 | CFP match 48 → **73**，zone 由 worth_verifying → **recommended_now** |
| P0-2 | **补职场/社区兴趣别名**：`open_source` / `networking` / `public_speaking` | interest_fit 由 20 → **100**（C 组同一条机会） |
| P0-3 | **Utility 进入推荐判定**：`recommended_now` = … 且（match ≥ 55 **或** Utility=high） | 新增单测 `test_utility_can_qualify_recommendation` |
| P0-4 | **证据前提写进协议**：SKILL.md 新增 "Evidence precondition"；`extraction-policy §6.2` 给出结构示例与"必须在页面上当场记录"的纪律 | C 组回归：带 evidence 后真实 gate 给出 **recommended_now = 3** |
| P0-5 | **禁止手工标注分区**：`usertests/_apply_gate.py` 用真实 `score.py` 重算每个候选的 zone；`tests/test_usertest_records.py` 守卫"标注必须等于 gate 计算值 + 主推荐必须带 evidence" | 守卫曾正确报出 D 组 3 条虚假主推荐，修正后 313 测试全绿 |
| P0-6 | **过期项不得进入任何可申请区**（D 的 2 条已按 gate 改为 excluded，并保留 `zone_declared_by_agent` 审计痕迹） | `_apply_gate.py` 输出 0 处不一致 |
| P0-7 | **健壮性**：`effort` / `cost` 允许字符串或对象（真实验收数据两种都有） | `test_effort_and_cost_accept_both_shapes` |

测试：**306 → 313 全绿**（新增 P0 回归 5 例 + case 记录守卫 2 例）。

## 八、P1 候选项（按证据排序，尚未实施）

1. **rolling/evergreen freshness 规则**（C/E 受影响最重）：页面明确写 rolling/常设/随时 → `likely_open`，并保留证据要求。
2. **反爬友好的验证路径**（F11）：Worth verifying 区固定话术 + 允许"跨来源交叉确认"记为 `partially_verified`。
3. **证据字段的记录成本**：把 `evidence.application_status` 抽成模板/检查清单，降低漏记概率（P0-4 只解决了"知道要记"，没解决"容易忘"）。
4. **预算分配建议**：三语言/多方向场景下强制"每方向 ≥2 query"，并预留 ≥50% fetch 给最终候选。
5. **专业资本维度覆盖**：D/E 应输出 `career_capital` 与 `future_optionality`（已具备字段，未使用）。
6. **小赌注组合均衡**：E 的 low_cost / network 两类为空，需要显式提示"至少各一条"。
7. **回答内"补信息解锁清单"**：把 Unknown 资格项转成"补上 X 就能确定"，减少 Unknown 的挫败感。
8. **IoT 最终验证 67% < 80%**（`benchmarks/known_failures.json`，上轮遗留）：仍为声明的 FAIL，不降门槛。

---

## 结论

- **能力层面通过**：三种人生阶段（在职申硕 / 不跳槽求晋升 / 无目标探索）都能得到非退化的、官方可核实的、有决策信息的答案；V3 的 outcome / readiness / utility / graph 字段**确实改变了推荐**（不只是 JSON）。
- **过程层面曾严重失守**：手工分区 + 缺 evidence 让"主推荐区"名义存在、实际不可达。P0-1…P0-7 修复后，真实 gate 已在 C 组回归中给出 3 条可推荐机会。
- **不建议现在进入 P1**：先按 P1-1（evergreen freshness）与 P1-3（证据记录成本）各做一次小回归，确认"带证据的主推荐"在 D/E 也能稳定出现，再排 P1 优先级。
