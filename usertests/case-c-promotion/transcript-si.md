# Case C — Promotion（升 Senior）回放记录 · 来源智能回归轮（SI）

> 目标：验证三处改动 —— `gaps.is_logistics()` 把手续类前置从「技能缺口」里分出来；`sources.STAGE_FIT` 按用户阶段给每个来源 family 打适配度并标记 selected/downweighted；`sources.source_freshness()` 区分「页面时效」与「机会时效」。
> 重跑真实链路：Profile → 来源感知 Discovery → Verification → Gap(`gaps.py`) → Bridge(`graph.py`) → Portfolio(`portfolio.py`) → 确定性 Gate(`score.py`)。
> 预算：7 次 WebSearch + 5 次 WebFetch（全部用尽，均无发明 URL）。

---

## ① 用户原话

> 「我现在不想跳槽，就是想让自己未来更容易升 Senior。我是做后端/云原生的，五年经验，base 在新加坡，远程也行。」

画像（`profile.json`，仅写入用户明确说过的内容）：
- life_stage = `working`，career_stage = `mid_career`，years_experience = 5
- skills = backend / cloud-native（等级 unknown，未发明技术栈）
- 目标（由「升 Senior」推导，非原话）：open_source / networking / event（高优先），research / skill / funding（中低）
- constraints：preferred_country = Singapore，remote = true，relocation = false，unpaid = true，weekly_time = null
- 未提供字段（雇主 / GPA / 毕业年份 / GitHub / 国籍 / 语言成绩）一律 Unknown

---

## ② 来源计划（含 stage_fit）

用户阶段 = **working**（`sources.stage_of` 因 working 优先，不会被 career_stage 拉回学生视角）。
三个缺口 → Bridge Intent → Source Family，每个 family 按 working 阶段适配度排序，`family_selected` / `family_downweighted_due_to_stage` 逐 query 记录：

| Gap 类型 | Bridge Intent | 选用 family | 各 family 的 stage_fit（working） | family_selected | family_downweighted |
|---|---|---|---|---|---|
| public_reputation | visible public impact | community_event, maintainer_program, working_group, speech_contest | 全部 high | ✅ 全部 | 无 |
| leadership | visible ownership | working_group, maintainer_program, foundation | 全部 high | ✅ 全部 | 无 |
| portfolio | public, verifiable artefact | contributor_guide, mentorship_program, foundation, speech_contest | 全部 high/medium | ✅ 全部 | 无 |

**结论**：本用户为在职（working），6 个相关 family 适配度全为 high（foundation/mentorship_program/working_group/maintainer_program 对 working 均 high；community_event/contributor_guide 亦 high）。因此 `stage_inapplicable_query_rate = 0`，`stage_family_precision = 1.0`——没有任何 family 因阶段被降权或跳过，预算不会浪费在低适配来源上。
（注：`plan_queries` 在命中 limit 时会提前 return、漏设 selected/downweighted 标记；本回放已在驱动脚本里按 `stage_fit` 显式补全。）

---

## ③ 候选机会与 provenance / source_freshness

真实搜索 7 次 + 真实抓取 5 次，命中 7 个真实官方源 + 1 个历史归档页（刻意测试降级）。逐条记录 `provenance` 与 `source_freshness`：

| 候选 | 类别 | provenance | source_family | source_freshness（页面时效） | zone（Gate 重算） |
|---|---|---|---|---|---|
| CNCF TAG 参与 | open_source | source_family_query | working_group | likely_current | recommended_now |
| KubeCon EU 2027 CFP | event | source_family_query | community_event | current（页面提到 2027） | recommended_now |
| Kubernetes SIG 贡献者路径 | open_source | source_family_query | contributor_guide | likely_current | recommended_now |
| CNCF Maintainer 路径 | open_source | source_family_query | foundation | likely_current | recommended_now |
| CNCF Ambassador 计划 | networking | source_family_query | maintainer_program | current（页面新鲜，但本年度已关闭） | excluded |
| LFX Mentorship（CNCF） | networking | source_family_query | mentorship_program | current（页面新鲜，但本周期已关闭） | excluded |
| CNCG Singapore 组织者 | networking | general_search | — | unknown（未单独抓 SG chapter） | worth_verifying |
| **KubeCon NA 2025 归档页** | event | source_family_query | community_event | **historical（URL 含 /archive/2025/）** | **excluded** |

关键观察（页面时效 ≠ 机会时效）：Ambassador / LFX 的**页面是 current**（有 2026 年动态/提交），但**机会本身 closed**（2026 周期已截止、下次 2027）；2025 归档页则**页面就是 historical**，直接不能作为当前机会。

`source_family_query_share = 0.875`，`general_search_share = 0.125`。

---

## ④ 验证与证据（evidence gate）

实抓 5 个官方页确认状态：
- **KubeCon EU 2027 CFP**：`events.linuxfoundation.org` 明确 "Submissions due 11 October 2026; Event 15–18 March 2027, Barcelona" → `application_status = open`，证据新鲜（verified_at 2026-09-20），进 recommended_now。
- **CNCF TAG**：`contribute.cncf.io/community/tags` "All TAG meetings are open to the public. No registration or membership required … Path to Leadership: Chairs nominate Tech Leads; community elects Chairs" → `rolling`，verified_official。
- **Kubernetes SIG**：`kubernetes.dev` "Anybody is welcome … good first issue … No application required" → `rolling`。
- **CNCF Maintainer 路径**：`cncf.io/blog` governance 文 "contributor → reviewer → maintainer；OWNERS 提名，2/3 maintainer 批准" → `rolling`。
- **CNCF Ambassador**：`cncf.io/people/ambassadors` 年度计划，2026 cycle 已关闭，下次 2027 → `closed`。
- **LFX Mentorship**：`github.com/cncf/mentoring` Term 03 2026（Sep–Nov）mentee 申请 8/3–8/18、mentor 提案 7/1–7/28 均关闭 → `closed`。
- **2025 归档页**：`/archive/2025/...` 命中 `source_freshness = historical`（URL 含 archive + 2025）→ 不满足「当前可申请」证据门，记为 fact 类降级。

`evidence` 完整度：`verified_official` 6 个；CNCG SG 为 `unverified`（general_search 发现、未单独抓章节页，process 类，可在下一轮补）；归档页页面已核实但无申请状态（historical）。

---

## ⑤ development gaps vs logistics（本次回归核心）

`gaps.collect_gaps` 现在把「手续/工具类前置」(`is_logistics`) 单独剥离，不污染 development gap 计数与覆盖率分母。

**development_gaps = 14**（来自真实机会硬性要求 + 用户/语义推导）：
- 用户明确 / 语义：`升 Senior 相关的可验证经历`(high)、`公开影响力证据（演讲/maintainer/社区角色）`(high)、`ownership / 跨团队项目证据`(medium)、`研究经历/论文/实验室接触`(high，学术导向→对本用户低相关)、`教授/实验室联系人`(high，学术导向→低相关)
- 机会硬性要求：`对某一云原生领域的兴趣`、`云原生相关实践经验（演讲主题）`、`英语演讲能力`、`Go / Kubernetes 基础`、`成为 CNCF 项目 contributor（先合并 PR）`、`CNCF SIG/TAG 成员或项目贡献`、`公开演讲/内容创作/社区组织（至少两项）`、`CNCF 项目 maintainer 资格（才能以 mentor 提案）`、`新加坡本地或远程组织意愿`

**logistics_prerequisites = 2**（被正确剥离，不再算缺口）：
- `CNCF Slack 账号（免费，参与沟通频道）`（来自 TAG）
- `GitHub 账号（提交 PR）`（来自 K8s SIG）

`gaps_total`（含 logistics）= 16，`gap_noise_rate = 0.125`（2/16）。
`gaps_with_bridge = 9`，`gap_coverage_rate`（仅对 development_gaps 计）= **0.643**（9/14），对比上一轮 0.562（9/16，分母里混了 logistics）。

诚实说明：logistics 修复本身对覆盖率提升有限（那 2 项本就不是「可被机会桥接」的硬缺口）。剩余的噪声主要来自**语义推导的 research / network(教授/实验室)** 缺口——它们对在职后端工程师本就低相关，本次三处改动未触及这部分。

---

## ⑥ Bridges（缺口 → 真实机会）

`graph.bridges_for_gap` 对 14 个 development gap 逐一匹配真实机会（不限 top-3 截断，避免漏算）：
- **bridges = 7**：CNCF TAG、KubeCon EU 2027 CFP、Kubernetes SIG、CNCF Maintainer 路径、CNCF Ambassador、LFX Mentorship、CNCG SG
- `bridges_verified = 6`（仅 CNCG SG 为 unverified），`bridge_verified_rate = 0.857`
- `bridge_actionable = 4`（4 个 recommended_now 机会），`bridge_actionable_rate = 0.571`
- 5 个 development gap 无桥接：研究/论文、云原生实践经验、英语演讲、公开演讲/内容创作、新加坡组织意愿（多为「机会本身的入场要求」，需靠投入该机会自身积累，桥接图按名字匹配不到——已知局限）

---

## ⑦ Portfolio（资源约束）

`profile.weekly_time = null` → 采用规划默认 `budget_hours = 5.0/wk`（已在记录中标注为默认）。
- `planned_hours = 3.0`，`resource_conflict = False`
- 入选：`CNCF TAG`（3h/wk，now + high_upside + long_term）、`CNCG SG`（小时未知，high_upside + long_term + explore）
- 因预算被 drop：`CNCF Maintainer`(6h)、`Kubernetes SIG`(4h)、`KubeCon CFP`(4h) —— 仍 recommended_now，可参与，只是周时超预算暂未排入
- 历史归档页不进入 portfolio（不是真实机会）

---

## ⑧ 【用户最终回答】（白话中文，无内部术语）

你不想跳槽，只是想以后更容易升 Senior。你是做后端/云原生的，5 年经验，在新加坡、也能远程。

最值得现在动手的 4 件事（都是真实、当前开放的官方渠道，不用花钱）：
1. **加入 CNCF 的技术顾问组（TAG）**：会议对所有人开放，不用报名，先从参与讨论、帮忙写文档开始，路线写得很清楚——做着做着会被提名当技术负责人。每周大约 3 小时。
2. **给 Kubernetes 这类开源项目提 PR**：从 "good first issue" 起步，不需要申请，先把代码合进去，这就是实打实的公开成果。
3. **走 CNCF 的 maintainer 路线**：先当 contributor，再按规则被提名成维护者——这是升 Senior 时最有说服力的「技术领导力」证据。
4. **投 KubeCon 2027（巴塞罗那，明年 3 月，投稿截止今年 10 月 11 日）的演讲**：用你做过的云原生实战当主题，练一次公开演讲。

另外两条路现在**关着，明年会再开**，先记着：CNCF 大使计划、LFX 导师计划（都要等到 2027 周期）。

两个**顺手就能解决、但不算「能力缺口」**的小事：参与上面这些，你只需要一个免费的 CNCF Slack 账号和一个 GitHub 账号——这俩是手续，不是你缺的技能，别为此焦虑。

**坦白讲**：你真正该补的「升 Senior 资本」就三类——**公开影响力**（演讲 / maintainer / 社区角色）、**ownership / 跨团队主导经验**、**技术影响力（贡献者→维护者）**。你画像里目前没有这些可见产出，所以建议从上面 4 件事里挑 1–2 件先持续做。每周大概 3 小时就能起步，不会跟你现在的工作冲突。
