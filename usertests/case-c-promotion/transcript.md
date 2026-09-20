# Case C — Promotion（升 Senior 资本）回归测试记录

> P0 回归：修复缺陷 #1（V3 outcome facets 未进入 scoring，导致 CFP/开源/委员会角色卡在 ~48 < 55）
> 与缺陷 #2（run 未记录 tightened gate 要求的证据结构，导致 recommended_now 不可达）。
> 今天：2026-09-20。使用真实 WebSearch + WebFetch，仅收录有官方来源的实时机会。

---

## ① 用户原话

> "我现在不想跳槽，就是想让自己未来更容易升 Senior。我是做后端/云原生的，五年经验，base 在新加坡，远程也行。"

解读（不发明）：目标是**升 Senior 的资本建设**，不是找新工作。五年经验接近 Senior 门槛，应侧重**可见度、技术领导力、跨团队影响力**。地区=新加坡+全球远程，主语言英文。

---

## ② 画像（仅来自输入，未发明雇主/GPA/毕业年份/技术栈）

- life_stage: working；career_stage: mid_career；years_experience: 5
- education.degree: null；major: backend / cloud-native（行业方向，非学位专业）
- skills: backend(unknown), cloud-native(unknown)
- languages: English(unknown)
- goals（按优先级）: open_source(high)、networking(high)、event(high)、research(medium)、skill(medium)、funding(low)
- constraints: preferred_country=[Singapore], remote=true, relocation=false, unpaid=true
- 明确未提供：雇主、具体技术栈(K8s/Go/云平台)、GitHub/开源贡献史、国籍/签证、每周可投入时间

---

## ③ locale / coverage

- locales.py：`mode: A`，regions: singapore + remote，primary_locales: en-SG，optional: zh-CN/ms-SG
- 类别覆盖（≥3 类，避免退化成实习/招聘）：event、open_source、networking、research、skill_development 各≥1 条
- 预算：6 WebSearch + 5 WebFetch（已用满）。3 条官方页成功取回证据，2 条官方页取回失败（见⑥）

---

## ④ queries（6 次 WebSearch）

1. `KubeCon CloudNativeCon 2027 CFP call for proposals speaker deadline` — event
2. `CNCF become a project maintainer contributor ladder how to participate 2026` — open_source
3. `CNCF CKA CKAD CKS certification exam register schedule 2026 Linux Foundation` — skill
4. `CNCF Community Group Singapore chapter local meetup community.cncf.io` — networking
5. `LFX Mentorship Linux Foundation become a mentor 2026 application` — networking
6. `CNCF Technical Advisory Group TAG working group join participate contribute.cncf.io` — research

---

## ⑤ 候选与排除（7 个候选）

进入主推荐区（recommended_now，3 个，均 fetched + verified_official + 当日 evidence）：
- C1 KubeCon + CloudNativeCon Europe 2027 CFP（event）
- C2 CNCF 开源贡献者路径→Maintainer（open_source）
- C3 CKA/CKAD/CKS Kubernetes 认证（skill）

值得继续核实（worth_verifying，4 个）：
- C4 CNCF TAG / Working Group 参与（research）— 搜索到官方页显示开放，但本轮未 fetch 确认
- C5 LFX Mentorship 以 Mentor 身份（networking）— 官方 Mentor 文档显示按 Term 招募；fetch 跳登录墙
- C6 Cloud Native Community Group Singapore 组织者（networking）— 搜索显示群组活跃；群组页 fetch 返回 404
- C7 ACM Singapore 委员会（networking）— 未找到官方确认来源，留作待核实

排除：无（没有过期/明确不符合项）。C7 因无 canonical source 未进主区，但留在 worth_verifying 而非丢弃。

---

## ⑥ verification / evidence / eligibility / readiness / utility

**已 fetch 并记录的真实证据（verified_official + evidence，verified_at=2026-09-20）：**

| 候选 | 官方页（当日 fetch） | application_status | deadline |
|---|---|---|---|
| C1 KubeCon CFP | events.linuxfoundation.org/kubecon-cloudnativecon-europe/program/cfp | open（"Submissions are due by 11 October…"） | 2026-10-11 explicit |
| C2 CNCF 贡献者路径 | contribute.cncf.io/contributors/getting-started | open（"Contributing… doesn't require permission… start contributing"） | rolling（无固定截止）explicit |
| C3 CKA 认证 | www.cncf.io/certification/cka/ | open（"register for exam" 入口） | rolling（常年报名）explicit |

**fetch 失败、如实降级（未伪造 verified_official）：**
- C6 community.cncf.io/singapore → 404（SPA 路由），未取得'成为组织者'入口 → partially_verified
- C5 mentorship.lfx.linuxfoundation.org/participate/mentor → 跳 LF SSO 登录页，未取得正文 → partially_verified（evidence 取自官方 LFX gitbook 文档，标注来源）

**eligibility（按硬性条件，无 inferred 升级）：**
- C1 Eligible（CFP 对从业者开放，无硬性门槛）
- C2 Probably Eligible（maintainer 需 12 个月贡献+提名，画像缺开源史，只能给 Probably）
- C3 Eligible（认证无学历/身份门槛）
- C4 Eligible；C5 Probably Eligible；C6 Eligible；C7 Unknown

**readiness：** C3 ready_now；C1/C2/C5/C6 minor_preparation；C4 ready_now；C7 unknown
**utility：** 三者均为 medium-high（资格+准备度+产出/未来通道明确），但主区由 **match≥55** 命中（非仅靠 utility）。C1 match≈68、C2≈68、C3≈60，均≥55。

**关键修复验证：** 缺陷 #2 要求的结构（verification_status=verified_official + application_status/evidence.deadline explicit + source_url + verified_at 当日）已为 C1/C2/C3 记录；`actionable_evidence` 因此为真，freshness 对 rolling 项返回 likely_open → 三者全部进入 recommended_now。上一轮因缺该结构，recommended_now=0；本轮=3。

---

## ⑦ graph（机会图谱）

- produces：C2 合并 PR/OWNERS → C1 公开演讲 → C3 认证凭证 → C4 标准文档 → C5 指导记录 → C6 本地领导力
- unlocks：C2→C1/C6（maintainer 是 Ambassador/演讲跳板）；C4→C1；C3→C2（Kubestronaut 增信）；C5→C2；C6→C1
- bridges：公开贡献(C2) → 外部可见度(C1/C6) → 升 Senior 的'影响超出团队'证据；考证(C3) 补可信度 → 进 TAG(C4)/做导师(C5)

---

## ⑧ 【用户看到的最终回答】（白话中文，无内部术语）

你不想跳槽，只想**更容易升 Senior**——那重点就不是"再找一份工作"，而是攒够**升职评审看得见的资本**：行业外部影响力、技术领导力、带人/带项目的能力。基于你「后端/云原生、五年经验、base 新加坡、可远程」的情况，我筛了开源、社区、会议、认证这几类（不是招聘帖），以下 3 个现在就能动手：

1. **投 KubeCon + CloudNativeCon Europe 2027 的演讲（CFP）** — 截止 **2026-10-11**（还有 21 天），官网明确在收稿、鼓励首次演讲者。一次旗舰会议演讲，就是"技术影响力超出本团队"最硬、可验证的证据，直接能写进升职材料。
2. **走 CNCF 开源贡献者路径，目标做 Maintainer** — 官方贡献者页明确写"贡献不需要许可，直接开始"。持续给云原生项目发 PR、做 review，约一年后被现 maintainer 提名。这是"带动项目/他人"的第三方背书，比口头说"熟悉开源"分量重得多。
3. **考 CKA / CKAD / CKS（Kubernetes 认证）** — 官网常年开放报名（约 $445/门，远程在线考）。五年经验者的"硬通货"：简历和答辩里第三方可验证的 K8s 能力。

另外 3 个值得关注、但我**没能在这轮把官方申请入口核实清楚**，先放"待确认"：
- **进 CNCF 的 TAG / Working Group**（参与定标准，Senior 级"设定标准而非只执行"的强证据）
- **以 Mentor 身份参加 LFX Mentorship**（带新人 = 直接对应"培养他人"维度）
- **做 Cloud Native Community Group Singapore 的组织者**（就在新加坡本地，零成本建技术社区领导力）

> 坦白说：后两个的官方页我这轮抓取失败（一个 404、一个跳登录），所以没敢标"现在就能申请"，建议你点进去确认下入口。想让我深挖哪条、或你补充下具体技术栈/开源经历，我可以更精准地判断你能不能上。

---

## 真实 gate 输出（_apply_gate.py，2026-09-20）

```
[Case C] gate 重算: recommended=3 worth_verifying=4 excluded=0 | 手工标注与 gate 不一致: 0
    缺 evidence.application_status 的候选: 1/7
```

- recommended_now（3）：C1 KubeCon CFP、C2 CNCF Maintainer 路径、C3 CKA/CKAD/CKS
- worth_verifying（4）：C4 CNCF TAG、C5 LFX Mentor、C6 CNCG Singapore、C7 ACM Singapore
- excluded（0）：无
- 缺失 evidence.application_status 的候选：仅 C7（ACM Singapore，本就未进主区）

---

## 验收与剩余问题

- ✅ 未退化成招聘板（job-board degeneration）：全部为非求职类（开源/社区/会议/认证）。
- ✅ 缺陷 #1（V3 outcomes 进入 scoring）与 #2（evidence 前提）均已修复：recommended_now 由 0 → 3。
- ✅ 无过期/无来源项混入主区；主区官方验证率 3/3 = 100%。
- ⚠️ P1：C6 官方群组页 404、C5 官方 Mentor 页跳登录，导致这两条只能 worth_verifying（如实降级，未伪造 verified_official）。需额外 fetch 配额才能认证进主区。
- ⚠️ P1：画像未提供具体技术栈与开源贡献史，maintainer/mentor 类资格只能给 Probably Eligible，无法进一步收紧。
- P2：6+5 预算已用满，2 次失败 fetch 挤占了验证预算。
- 无 P0 残留（两个被回归的缺陷均已修复并通过真实 gate 验证）。
