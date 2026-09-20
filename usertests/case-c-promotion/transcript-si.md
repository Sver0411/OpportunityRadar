# Case C — Source Intelligence 全链路记录（transcript-si）

> 用户目标：不跳槽，只为将来更容易升 Senior。后端/云原生，5 年经验，base 新加坡，远程可接受。
> 轮次：Round-4 Source Intelligence 回归。日期：2026-09-20。真实联网 + 真实官方来源，无发明 URL。

## ① 原话（user_input）
"我现在不想跳槽，就是想让自己未来更容易升 Senior。我是做后端/云原生的，五年经验，base 在新加坡，远程也行。"

推导出的目标（非用户原话，标注为推导）：open_source(maintainer/committer、mentorship)、networking(专业协会/社区组织者)、event(CFP/演讲/program committee)、research(技术委员会/标准组织)、skill(云原生认证)。约束：不推荐跳槽岗位；地区=新加坡+全球远程；未提供学历/雇主/技术栈/GitHub/国籍。

## ② 来源计划（Source Intelligence plan，scripts/sources.py）
生态选择（由用户领域决定，非硬编码）：**CNCF**（后端/云原生 → cloud native foundation）。
对三个缺口分别跑了 `scripts/sources.py --gap <缺口> --gap-type <类型> --topic CNCF --profile profile.json`：

- **public_reputation**（bridge intent: visible public impact）→ families: community_event, maintainer_program, working_group, speech_contest
  查询：`CNCF community event CFP open` / `CNCF maintainer pathway governance` / `CNCF working group SIG join` / `CNCF technical committee participate`
- **leadership**（bridge intent: visible ownership）→ families: working_group, maintainer_program, foundation
  查询：`CNCF working group SIG join` / `CNCF technical committee participate` / `CNCF maintainer pathway governance` / `CNCF foundation contributor programme students`
- **portfolio**（bridge intent: public, verifiable artefact）→ families: contributor_guide, mentorship_program, foundation, speech_contest
  查询：`CNCF contributor guide good first issue` / `CNCF mentorship programme apply` / `CNCF foundation contributor programme students`

纪律：registry 不是白名单——未知来源照常走 general_search / adjacent_discovery；候选不因"来自 known source"而变可信。

**实际执行（预算内 7 WebSearch + 5 WebFetch）：**
1. `CNCF Technical Advisory Group TAG join how to participate` → contribute.cncf.io/community/tags
2. `CNCF Ambassador program apply 2026` → cncf.io/people/ambassadors/FAQ
3. `LFX Mentorship CNCF apply mentor 2026` → github.com/cncf/mentoring
4. `KubeCon CloudNativeCon 2027 CFP call for proposals` → events.linuxfoundation.org/.../cfp
5. `Kubernetes SIG contributor guide good first issue` → kubernetes.dev/docs/guide/first-contribution
6. `CNCF contributor ladder become maintainer governance` → cncf.io/blog/2026/08/26/...governance
7. `cloud native community groups Singapore chapter lead organizer apply`（**general_search 兜底**）→ 发现社区组角度，但未单独核实 SG chapter

## ③ 候选与来源 provenance（7 个，覆盖全部 6 个要求 family）
| # | 候选 | family | provenance | zone（gate 重算） |
|---|------|--------|-----------|-------------------|
| 1 | CNCF Technical Advisory Group (TAG) 参与 | working_group | source_family_query | recommended_now |
| 2 | KubeCon + CloudNativeCon Europe 2027 CFP | community_event | source_family_query | recommended_now |
| 3 | Kubernetes SIG 贡献者路径（good first issue） | contributor_guide | source_family_query | recommended_now |
| 4 | CNCF 项目 Maintainer 路径（contributor ladder） | foundation | source_family_query | recommended_now |
| 5 | CNCF Ambassador 计划（年度申请） | maintainer_program | source_family_query | excluded（2026 cycle closed）|
| 6 | LFX Mentorship（以 Mentor 身份，需 maintainer 资格） | mentorship_program | source_family_query | excluded（Term3 2026 窗口关闭）|
| 7 | Cloud Native Community Group (CNCG) Singapore | — | general_search | worth_verifying（未单独核实）|

provenance 分布：source_family_query = 6/7（0.857），general_search = 1/7（0.143）。**没有 known_source 白名单**；所有项都走同一套 gate。

## ④ verification / evidence（每个候选都有 dated 官方证据，verified_at=2026-09-20）
统一 gate 要求：`verified_official` + `evidence.application_status`（explicit + source_url + verified_at 在 30 天内）+ freshness 非 closed。
- TAG：`verified_official`，evidence "All TAG meetings are open to the public. No registration or membership required"，application_status=rolling → likely_open。
- KubeCon EU 2027 CFP：`verified_official`，evidence "Submissions due by 11 October CEST"，application_status=open，deadline 2026-10-11（剩 ~21 天）→ open。
- K8s SIG：`verified_official`，evidence "Anybody is welcome to jump into a SIG... good first issue"，application_status=rolling。
- CNCF Maintainer：`verified_official`，evidence "Maintainer nominated via PR to OWNERS file, 2/3 approve"，application_status=rolling。
- CNCF Ambassador：`verified_official`，但 evidence "applications once a year; notifications September; 2026 cycle closed" → application_status=closed → 诚实 excluded（2027 重开）。
- LFX Mentorship：`verified_official`，evidence "Term3 mentee/mentor windows closed; next Term1 2027" → closed → 诚实 excluded。
- CNCG Singapore：仅 community.cncf.io 平台 URL，**未 fetch 具体 SG chapter**，无 application_status 证据 → 未进 recommended_now（process 失败，见 ⑨）。

## ⑤ gaps（scripts/gaps.py，collect_gaps）
共 16 个 gap；9 个有桥接覆盖（gap_coverage_rate=0.562）。来源分布：requirements 11、semantic 4、user_stated 1。
- 语义缺口（与"升 Senior"直接相关）：public_reputation（高）、leadership（中）、experience（高，user_stated）、network（高）、research（高）。
  - 被覆盖：public_reputation（TAG/Maintainer/KubeCon 桥接）、leadership（Maintainer/TAG）、experience（Maintainer 路径）。
  - 未覆盖：network（学术教授接触）、research（论文/实验室）——对在职后端工程师本就低相关。
- 注意：11 个 requirements 类 gap 含 prerequisite 噪声（Slack 账号、GitHub 账号、Go/K8s 基础等被 collect_gaps 归入 skill），拉低了覆盖率数字。

## ⑥ bridges（scripts/graph.py bridge_graph）
User → Gap → Bridge → Produced Evidence → Goal 全链路连通。7 个机会均为桥接：
- 4 个 recommended_now（可立即行动）：TAG、KubeCon CFP、K8s SIG、CNCF Maintainer。
- 2 个 excluded（当前周期关闭，作为 2027 通道保留）：Ambassador、LFX。
- 1 个 worth_verifying：CNCG Singapore。
bridges_verified=6/7（0.857），bridge_actionable_rate（recommended_now）=4/7（0.571）。

## ⑦ portfolio（scripts/portfolio.py，budget = weekly_time）
profile.weekly_time 为 null（用户未填），采用规划默认 **5 小时/周**。
- resource_conflict = **False**（资源冲突率 0，符合 P1 指标）。
- 入选：CNCF TAG（now，~3h/周）+ CNCG Singapore（high_upside，时数未明）。
- 因周时预算被 drop（非排除，仍可参与）：CNCF Maintainer、K8s SIG、KubeCon CFP。
- 角色覆盖：now / high_upside / long_term / explore。

## ⑧【用户最终回答】（白话中文，无内部术语）
你想的是"先不跳槽，但让自己以后更好升 Senior"——说白了，就是要在团队之外，攒下**别人看得见、查得到**的资历。我帮你从云原生开源社区里找了几个现在就能动手的路子（都是真的、官方可查的，不是招聘广告）：

**你缺什么（用大白话说）**
- 缺"公开名气"：公司外没人知道你牛。
- 缺"当家做主"的证据：升 Senior 要看你能不能带队/主导，而不只是写代码。
- 缺"拿得出手的作品"：公开合并过的代码、讲过的分享。

**可以马上做的（现在就开）**
1. **加入 CNCF 的技术顾问组（TAG）**：完全免费、不用报名，进 Slack、开会、帮着审文档/写白皮书，混脸熟后能被提名进领导层。这最对口"公开领导力"。
2. **给 Kubernetes 提第一个 PR**：认领 "good first issue"，进对应的 SIG，沿贡献者阶梯往上走——这是最硬的公开作品。
3. **投 KubeCon 欧洲 2027 的演讲征集（CFP）**：截止 2026-10-11，会议在 2027 年 3 月巴塞罗那。第一次演讲他们也鼓励，这是团队外曝光最快的一条。
4. **走 CNCF 项目 Maintainer 路径**：先合 PR 成为 contributor，再被现有 maintainer 提名进 OWNERS 文件——这才是升 Senior 最硬核的"ownership 证据"。

**现在没开、但明年能用的（别急）**
- **CNCF Ambassador（大使）** 和 **LFX Mentorship（以导师身份）**：今年的申请窗口已经关了，明年会重开；而且当 LFX 导师得先成为项目 maintainer，所以建议先把上面 1/4 做起来。

**打开什么**
- 从"写代码的人"变成"社区里被认得出的人"：TAG 领导层提名、KubeCon 演讲、maintainer 身份，都是升 Senior 评审时实打实能亮出来的东西。
- 新加坡本地还有 Cloud Native 社区组（CNCG），可以当组织者——这条我还没单独核实新加坡具体页面，你上去 community.cncf.io 查一下"Singapore"就能开。

**每周投入建议**：先按 5 小时/周来排，首选 TAG（约 3h）+ 顺手认领一个 K8s issue；CFP、maintainer 路径可以并行但别一次铺太开。

## ⑨ failures / 回归检查
- **Failure（process）**：CNCG Singapore 具体 chapter 页面未单独核实，只用了 CNCG 平台 URL，无法进入 recommended_now；已如实标为 worth_verifying，未发明深链。
- **job-board 回归**：本案例目标是非招聘，全程未从任何招聘/求职板取候选，仅用官方社区源，符合"不推荐跳槽岗位"约束。
- **与上轮（baseline 4 recommended_now）对比**：recommended_now 数量**未超过**上轮（仍为 4）；但构成更贴目标——上轮含 1 个技能认证(CKA)，本轮回合为 K8s SIG contributor（公开产出），4 个推荐项现全部是 工作组/维护者/CFP/贡献者 类型（上轮 3/4）。SI 的增量价值在于：跑通 family→query 规划、补齐 provenance 来源追踪、并把两个"当前关闭"的维护者/导师项诚实降级而非凑数。
