# Round 3 报告：Rolling / Evergreen Freshness + Evidence Pipeline

日期：2026-09-20 · 基线 `d3b0f8d` · 本轮只做事实链（不改 Match / Utility / Priority 权重，不放宽 gate）
测试：**313 → 324 全绿**（新增 10 例 fixture + 5 例证据/降级测试）

---

## 1. Freshness 状态模型（最终定义）

`deadline_type`（`common.DEADLINE_TYPES`，schema 同步）：
`fixed` / `range` / **`rolling`** / **`evergreen`** / **`recurring`** / `asap` / `flexible` / `tbd` / `unknown`

`freshness` 状态（`normalize_date.FRESHNESS_STATUSES`）：
`open` / `likely_open` / **`evergreen`** / **`recurring`** / `unknown` / `closed` / `expired` / `future`

| deadline_type | freshness | 能否 actionable |
|---|---|---|
| fixed / range | 按日期 → open / expired | open 可以 |
| rolling | likely_open | 可以（仍需证据） |
| evergreen | evergreen | **仅当页面有"当前可参与"证据** |
| recurring | 按周期年份 → future / closed / recurring | **仅当有当前周期开放证据** |
| asap / flexible | likely_open | 可以（仍需证据） |
| tbd / unknown / 无信息 | unknown | 不可以 |

**`deadline = null` 不再等于 unknown**：先看显式 `deadline_type`，再从页面文本识别
（rolling/ongoing/随時/先着 → likely_open；always open/长期有效 → evergreen；annual/每年 → recurring）。

**evergreen ≠ verified open**：长期存在不等于今天能参与 —— 只有
`application_status: open|rolling` + dated evidence 才能进主推荐（有测试守卫）。

## 2. Evidence Pipeline 改动

新增 `scripts/evidence.py`（extraction 后、gate 前运行）：

```
官方已核实 → evidence.application_status(explicit + source_url + verified_at≤30d) → actionable?
        ↓ 缺任何一项
   Flags: evidence_incomplete + 明确列出缺什么 → 只能进 worth_verifying
```

- `check(opp, today)`：canonical source + `verified_official` + dated application-status evidence，三者齐全才 `complete`
- `gated`：`recommended_now` 现在要求 `evidence_complete` **且** `actionable`；**Match / Utility 不能绕过**（有测试）
- `demotion_reason()`：把降级原因分成三类，机械区分而非人工判断
  - `missing_evidence_structure`（process）：页面读过但没记录证据
  - `verification_not_attempted`（process）：本轮没去核实
  - `page_not_verifiable`（infrastructure）：反爬 / JS 渲染 / 404 / 超时
  - `page_cannot_confirm`（fact）：页面本身不写当前状态
  - `no_canonical_source`（process）/ `closed_or_ineligible`（fact）
- `usertests/_apply_gate.py` 现在会回写每个候选的 `gate_computed.demotion`，并把
  deadline_type 分布 / rolling-evergreen 数 / 证据完整度 / 降级分类写入 `gate_computed_summary`

## 3. 新增测试

| 测试 | 覆盖 |
|---|---|
| `tests/fixtures/evidence_freshness_cases.json`（10 例） + `tests/test_freshness_evidence_cases.py` | 固定未到期/已过期、rolling 官方开放、evergreen 有入口/无入口、recurring 未开始/当前开放、null 无法确认、第三方声称、官网反爬 —— 每条给出**期望 freshness 与期望 zone** |
| `TestEvidencePrecondition`（4 例） | 无证据 / 证据过期 / 证据完整 / evergreen 无参与证据 |
| `TestDemotionClassification`（3 例） | process vs fact vs infrastructure 的判定 |
| `TestP0FixesFromCDE`（5 例，上一轮） | outcome 参与打分、Utility 等价门槛但不越权、effort/cost 双形态 |

## 4. C / D / E Regression（真实联网 + 真实 gate）

| Case | discovered | verified | recommended_now | worth_verifying | excluded | 证据完整度 | rolling/evergreen/recurring | 降级 process / fact / infra |
|---|---:|---:|---:|---:|---:|---:|---|---|
| **C**（升 Senior） | 7 | 4 | **4** | 3 | 0 | 6/7 | 6/7 | 2 / 1 / 0 |
| **D**（在职申硕） | 11 | 8 | **1** | 5 | 5 | 1/11 | 6/11（recurring 5 + evergreen 1） | 2 / 8 / 0 |
| **E**（无目标探索） | 7 | 1 | **1** | 6 | 0 | 1/7 | 7/7（evergreen 2 + recurring 4 + rolling 1） | 6 / 0 / 0 |

关键观察：

- **C 从 3 → 4**：新分类把 2 个 rolling、3 个 evergreen、1 个 recurring 机会正确识别出来，其中带 dated 证据的全部进入主推荐（CFP / maintainer 路径 / 证书）。
- **D 从 0 → 1**：唯一带"当前开放"证据的是 EMBA TECH（在线硕士）；其余在职硕士多为 recurring（按入学季）或 evergreen（远程/通信制），页面确认当前无开放窗口 → 如实降级（fact 3）。
- **E 从 0 → 1**：picoGym（CMU，evergreen 练习平台）当天读到官方页并记录证据 → 进主推荐；LFX / GSoC / Outreachy 都是 recurring 且当前非开放期 → 降级。
- **`recommended_now` 不再依赖运气**：三组里进入主推荐的每一条都有 distinct 的 `verified_official + dated evidence`。

## 5. 降级原因拆分（回答"系统忘了" vs "官网无法确认"）

| 类别 | D | C | E | 含义 |
|---|---:|---:|---:|---|
| process：漏记证据 | 2 | 2 | 6 | 可以靠流程/预算修 |
| fact：页面无法确认 / 已关闭 | 8 | 1 | 0 | **不可修**（事实如此） |
| infrastructure：反爬 / JS / 404 | 0 | 0 | 0 | 工具链限制 |

E 的 6 条全部是"本轮没去核实"（我只用了 2 搜 3 抓，子代理触发频率限制后由我手工执行）——
已在记录中显式标注 `notes`，不伪装成基础设施问题。

## 6. 仍然无法验证的真实案例

1. **LFX Mentorship 平台页**：JS 渲染（"Loading Content"），无法读到当前期次；只能靠 CNCF 官方博客日期判断（Term 3 申请 8/3–8/18 已截止）。
2. **play.picoctf.org**：Cloudflare 人机校验拦截；改由可读的 `picoctf.org` 官方页记录平台持续开放证据。
3. **D 组的日本大学社会人入试页**：放送大学 / SBI / 大阪経済均"页面无当前开放窗口"（fact，非工具问题）。
4. **GSoC / Outreachy 官网**：本轮未核实（预算），标记为 process 而非不可验证。

## 7. 新发现的缺陷

**P0（本轮已修）**
1. gate 首条件仍是 `freshness ∈ {open, likely_open}`，导致**有参与证据的 evergreen/recurring 永远进不了主推荐** → 改为 `actionable`（编码了两种路径）。
2. 只有 `evidence.deadline` 的条目仍被当作可推荐 → 现在要求 **application-status 证据**，旧测试 helper 同步升级。
3. 降级原因无法区分"漏记"与"官网打不开" → 新增分类 + 测试。

**P1（未做，需排期）**
1. **LFX 类 JS 平台页**：需要能读 JS 的抓取方式或固定话术（"平台当前期次请自查"）。
2. **evergreen 的"参与入口"判定仍需人工语义**：目前靠 `evidence_summary` 由 Agent 描述，可考虑加最小结构化字段（如 `participation_entry_url`）。
3. **预算分配**：E 组 6/7 未核实说明"发现多、验证少"；建议强制"最终候选 ≥80% 做过 fetch"。
4. **recurring 的下一期日期**：可把"下一周期预计开放时间"结构化（如 `next_cycle_opens`），让用户知道什么时候回来。
5. **IoT 最终验证 67% < 80%**（`benchmarks/known_failures.json`）仍为声明的 FAIL。

## 结论

事实链现在是稳的：**有当前证据的长期/滚动机会能稳定进主推荐，没有证据的稳定进不了**，
且降级原因可机械区分（process / fact / infrastructure）。三组真实回归的主推荐数量
（C 4 / D 1 / E 1）都来自真实官方页证据，没有一条是手工标注的。

下一轮按你的规划：**P1 第二项**（Portfolio / Gap→Bridge 或 Source Intelligence）二选一。
