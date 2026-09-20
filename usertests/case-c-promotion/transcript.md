# Case C — Round-3 Transcript（升 Senior 资本建设 / 后端·云原生 / 新加坡+远程）

## ① 原话（用户真实输入）

> "我现在不想跳槽，就是想让自己未来更容易升 Senior。我是做后端/云原生的，五年经验，base 在新加坡，远程也行。"

解析要点：
- **不想跳槽** → 排除所有 career 类招聘 / 求职入口；目标不是"找下一份工作"。
- **更容易升 Senior** → 目标 = 积累"升职资本"：技术领导力、跨团队影响力、团队外的可见度。
- **后端 / 云原生，5 年** → 接近 Senior 门槛，应侧重可见度与影响力而非基础技能。
- **base 新加坡，远程也行** → 地区 = 新加坡 + 全球远程；主语言英文（en-SG）。

## ② 画像（仅来自输入，未发明字段）

| 字段 | 值 | 来源 |
|---|---|---|
| 职业阶段 | working / mid_career | 推断自"5 年经验" |
| 年限 | 5 | 用户原话 |
| 领域 | backend / cloud-native（工作方向，非学位专业） | 用户原话 |
| 地区 | preferred_country=Singapore，remote=true，relocation=false | 用户原话 |
| 目标派生（由"升 Senior"推出，非原话） | open_source / networking / event / research / skill / funding | 升 Senior 资本的常见手段 |
| **未知字段（刻意留空）** | 学历学位、雇主、具体技术栈(K8s/Go/云平台)、GitHub/开源史、国籍/签证、语言成绩、每周可投入时间 | 用户未提供 |

> 画像纪律：未提供即 `Unknown`，不编造。据此 maintainer/mentor 类资格只能给 `Probably Eligible`。

## ③ locale / coverage

- **Mode A（profile discovery）**；但本轮为"升职资本建设"而非求职，故类别权重偏向 event / open_source / networking / research / skill，刻意压低 career 求职。
- **地区解析**（来自 `scripts/locales.py`）：regions = `singapore, remote`；primary locale = `en-SG`；optional = `zh-CN, ms-SG`（候选，未强搜）。
- **类别覆盖**：event、open_source、research、skill_development、networking 各 ≥1 条；全部为非求职类（开源/社区/会议/认证），未退化成招聘板。
- **预算**：6 WebSearch + 5 WebFetch 已用满。本轮 5 个官方页（KubeCon CFP、CNCF contribute、CKA 认证、TAG、LFX Mentorship 时间表）均成功取回并记录 explicit 证据；CNCG Singapore 群组页未以 WebFetch 打开，按 canonical-source gate 留作 worth_verifying。

## ④ queries（真实 WebSearch，6 条）

1. KubeCon CloudNativeCon 2027 CFP call for proposals deadline speaker submission — event
2. CNCF contributor ladder become a maintainer getting started contribute.cncf.io — open_source
3. CKA CKAD CKS Kubernetes certification Linux Foundation register online exam 2026 — skill_development
4. CNCF Technical Advisory Group TAG working group join participate contribute.cncf.io — research
5. LFX Mentorship become a mentor Linux Foundation terms application Spring Summer Fall — networking
6. CNCF Cloud Native Community Group Singapore chapter organizer community.cncf.io — networking (en-SG)

真实 WebFetch（5）：上述 1–5 的官方页全部命中并取回原文；CNCG 群组页未打开（见 ③）。

## ⑤ 候选与排除

**进入推荐区（recommended_now，4）：**
- `cncf-kubecon-eu-2027-cfp` — KubeCon+CloudNativeCon Europe 2027 CFP（演讲征集）
- `cncf-contributor-maintainer-path` — CNCF 开源贡献者路径（通往 Maintainer）
- `cncf-cka-ckad-cks` — CKA/CKAD/CKS Kubernetes 认证
- `cncf-tag-working-group` — CNCF TAG / Working Group 参与

**值得核实（worth_verifying，3）：**
- `lfx-mentorship-mentor` — LFX Mentorship（Mentor 身份）：recurring，官方文档确认按 Spring/Summer/Fall 循环，但**无法确认当前有开放的 Mentor 申请窗口** → 缺 dated open 观察。
- `cncg-singapore-organizer` — Cloud Native Community Group Singapore 组织者：evergreen，搜索显示 2026 仍有线下 meetup，但官方群组页未打开核实"成为组织者"入口 → 官方页未核实成功。
- `acm-singapore-committee` — ACM Singapore 委员：**未找到官方确认来源**（official_url 为空）→ 仅留作待核实。

**未搜/排除方向：** 一切 career 招聘类（用户明确不想跳槽）；学生专属项目（与"5 年职场"画像不符）。

## ⑥ verification / evidence / eligibility / readiness / utility

本轮严格执行新规则：`recommended_now` 必须同时满足 **canonical source + verified_official + dated application_status 证据（explicit+source_url+verified_at 在 30 天内）+ evidence 完整 + match≥55 或 utility=high**。

| 候选 | deadline_type（本轮新分类） | verification | application_status | 证据(dated) | 资格 | readiness | 落入区 |
|---|---|---|---|---|---|---|---|
| KubeCon CFP | fixed | verified_official | open | ✅ explicit 2026-09-20 | Eligible | minor | **recommended_now** |
| CNCF Maintainer | rolling | verified_official | open | ✅ explicit 2026-09-20 | Probably Eligible | minor | **recommended_now** |
| CKA/CKAD/CKS | **evergreen** | verified_official | open | ✅ explicit 2026-09-20 | Eligible | ready_now | **recommended_now** |
| CNCF TAG | rolling | verified_official | open | ✅ explicit 2026-09-20 | Eligible | ready_now | **recommended_now** |
| LFX Mentor | **recurring** | verified_official | recurring(非 open) | ⚠️ unknown：仅确认循环结构 | Probably Eligible | minor | worth_verifying |
| CNCG Singapore | **evergreen** | partially_verified | null | ⚠️ unknown：页未打开 | Eligible | minor | worth_verifying |
| ACM Singapore | evergreen | unverified | null | ❌ 无来源 | Unknown | unknown | worth_verifying |

**关键新规则体现：** evergreen/recurring 本身"长期存在"≠"今天能参与"。CKA 虽是 evergreen，但因记录了 dated `application_status=open` 证据，合法进入推荐区；LFX Mentor 虽是 recurring 且官方页已核实，但因**没有**"当前开放窗口"的 dated 观察，按证据前置检查被挡在 worth_verifying（降级性质 = fact：页面无法确认）。

## ⑦ graph（机会之间的桥接）

```
produces:
  KubeCon 演讲 → 公开演讲 / slides / 外部可见技术影响力
  CNCF Maintainer → 合并 PR / OWNERS / 技术决策权
  CKA 认证 → 行业认证凭证
  CNCF TAG → 标准文档 / 跨项目影响力
  LFX Mentor → mentee 产出 / 跨公司指导记录
  CNCG SG → 本地社区领导力 / 本地人脉

unlocks（彼此放大）:
  Maintainer → KubeCon 演讲 & CNCF Ambassador
  TAG → KubeCon 深度演讲
  CKA(Kubestronaut) → 更易被采纳为 maintainer
  LFX Mentor → maintainer 关系
  CNCG SG → 本地 meetup 演讲

bridge:
  主线：公开贡献(Maintainer) → 外部可见度(KubeCon/CNCG) → 升 Senior 的"影响超出团队"证据
  辅线：考证(CKA) 补可信度 → 进 TAG / 做导师 → 技术领导力与 mentorship 证据
  汇聚目标：promotion_to_senior（第三方可验证的技术领导力 / 行业影响力 / 培养他人）
```

## ⑧【用户最终回答】白话中文

你不想跳槽、想攒"升 Senior 的底气"，那重点就不在找下一份工作，而是把自己在本团队之外的影响力做出来。给你 4 个现在就能动手的（都已确认官方页、当前开放）：

1. **投 KubeCon Europe 2027 的演讲**（截止 2026-10-11，远程投稿）。一次旗舰会议演讲，是评审眼里最硬核的"技术影响力出圈"证据。
2. **去 CNCF 项目做贡献、往 Maintainer 走**（随时能开始，不用许可）。持续贡献约一年、被现 maintainer 提名，这是比"我会开源"强得多的第三方背书。
3. **考 CKA / CKAD / CKS**（全年可报名，在线考 $445）。Senior 答辩里，"有 CKA"比"熟悉 K8s"实在得多。
4. **加入 CNCF 的技术顾问组 TAG**（随时能参加公开会议）。参与定标准，是"影响超出本团队"的直接体现。

另外 3 个先别急着冲，值得你留意核实：
- **LFX Mentorship 做导师**：每年 Spring/Summer/Fall 招，但我没查到"现在正开放申请"的官方确认——等下届开放再看看。
- **新加坡本地 Cloud Native 社区组织者**：你 base 新加坡、零成本，但官方"成为组织者"入口这轮没打开核实，先去 meetup 混个脸熟。
- **ACM Singapore 委员**：没找到官方确认来源，先放一边。

一句话：**先把演讲、开源贡献、考证、进 TAG 这四件事做起来，你的"升 Senior 材料"就有了团队外可验证的证据。**
