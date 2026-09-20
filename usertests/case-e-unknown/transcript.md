# Case E — Unknown-Unknown Discovery（Mode C）

## ① 用户原话
> 「最近没什么目标，就是想看看有没有我完全不知道但是值得做的事情。」

## ② 画像（Unknown 字段保留）
- 已知（用户明确说过 / 可推导）：大三 CS 学生、美国在读、远程友好；技能 Python / Linux / Git；兴趣 cybersecurity + open source；无明确 goal。
- **Unknown（保持 null，未编造）**：学校名、学校城市/层次、入学年、毕业时间、GPA、国籍、签证、每周可用时间、可实习时间段、是否接受无薪、GitHub/科研/开源经历、公司。
- 模式判定：**Mode C（未知机会）**——降低求职权重，抬升 open_source / project / networking，adjacent+explore 提到 ~45%（55/25/20）。

## ③ locale / coverage
- `scripts/locales.py --profile` → mode C；regions: **us, remote**；primary locale: **en-US**；optional: 无。
- 加载：`references/locales/generic.md` + `references/locales/us.md`。
- 覆盖（9 搜索 / 6 核实）：open_source×2、funding、research、event、skill_development、competition、networking 各 1 query。
- 官方来源核实 6 个：Recurse、picoCTF、MLH、SFS、Outreachy、OpenSSF（播客）。
- 覆盖声明（来自 `coverage.py`）：**「本轮重点扫描了 us（competition、entrepreneurship、event、funding、networking、research、skill_development仅浅扫）；这是有限预算下的覆盖，不是全互联网完整扫描。」**
- 相邻维度深/浅：深核＝开源导师制/带薪 Fellowship（OpenSSF/MLH/Outreachy）、政府奖学金（SFS）、编程静修（Recurse）、CTF（picoCTF）；浅扫＝讲者/CFP、研究型 REU、技术写作(GSoD)、专业学会(OWASP)。

## ④ queries（layer + 探索的相邻维度）
1. `open source security mentorship program undergraduate 2026 remote` — adjacent / **role**
2. `tech conference student call for proposals security 2026 undergraduate` — explore / **role**(speaker)
3. `cybersecurity undergraduate scholarship government 2026 US citizen program` — adjacent / **institution**(government)
4. `free programming residency retreat 2026 remote programmers no tuition` — explore / **career_path**(residency)
5. `NSF REU cybersecurity summer 2026 undergraduate research experience remote` — adjacent / **opportunity_type**(research fellowship)
6. `open source technical writing program 2026 google season of docs docs` — explore / **role**(technical writer)
7. `free cybersecurity CTF 2026 undergraduate picoCTF DrivenData challenge` — exploit / **field**
8. `cybersecurity student society free membership ACM SIGSAC OWASP USENIX chapter 2026` — explore / **community**
9. `student open source fellowship 2026 remote paid MLH major league hacking` — adjacent / **role**(fellow)

> 相邻维度覆盖：field / role / opportunity_type / community / institution / career_path / geography = **7 维**（geography 以用户自身 US+remote 为镜头主动使用，未扩展到新国家）。

## ⑤ 候选与排除
- **纳入 Recommended now / 计划型**：Recurse Center、picoCTF、MLH Fellowship、CyberCorps SFS、Outreachy、OpenSSF Mentorship。
- **排除（含原因）**：
  - DoD Cyber Service Academy — 与 SFS 同为政府全额奖学金+服务义务，重叠，保留 SFS 作代表。
  - NSF REU（cybersecurity sites）— 2026 批已截止，需美籍/PR，本轮未核实具体学校页。
  - Google Season of Docs — 2026 是否运行未确认（最近公开轮次 2024）。
  - 学生 CFP（IUSCI/Twente/UBC/ITCODERA）— 多为非美国/已过期/学校限制，与 US+remote 不匹配，且无已核实的美国学生 CFP 页。

## ⑥ verification / eligibility / readiness / utility
- 全部 6 个纳入项均有官方来源；Recurse/picoCTF/MLH/SFS = `verified_official`，Outreachy = `verified_official`，OpenSSF = `partially_verified`（专页 404，以 openssf.org 官方播客确认）。
- 资格：Recurse `Eligible`；picoCTF `Eligible`；MLH `Probably Eligible`；OpenSSF `Probably Eligible`；**SFS `Unknown`（要求美籍+学校 NCAE-C，画像未提供国籍）→ 非 Ineligible，可进推荐但需确认**；Outreachy `Unknown`（弱势群体身份未提供）。
- 新鲜度：Recurse/picoCTF = open（滚动/常年）；MLH/SFS = likely_open（下一轮数月内开）；Outreachy/OpenSSF = future（下一轮 2027）。
- 无过期项混入推荐（`expired_in_recommended = false`）；推荐区无未核实项（`unverified_in_recommended = false`）。
- Personal Utility（`scripts/utility.py`）：Recurse = **high**；其余 5 = **medium**。说明 utility 与 match 分离——同为高匹配的 6 项，因窗口远近/资格未知而 utility 分层。

## ⑦ graph
- `scripts/graph.py`：6 节点、3 实边。produces→unlocks 链：
  - Recurse → 公开项目/更强简历 → RC 校友网络、SWE 简历。
  - MLH → 合进公开仓库的 PR → SWE 实习、开源 maintainer。
  - SFS → 资助学位+联邦许可 → 联邦网络安全岗。
  - OpenSSF → 安全工具贡献 → 开源 maintainer。
- gap→bridge（缺口「open source contribution / public portfolio」）：桥接机会 = MLH Fellowship（公开产出）、OpenSSF Mentorship（低投入）、Outreachy、Recurse、picoCTF。证明图在「补缺口该去哪」上有用。

## ⑧【用户看到的最终回答】（白话中文）

**本轮结论**：你这轮没有目标，所以我没按"实习 / 比赛 / 课程"去凑，而是专门找了一批你大概率不会主动搜的方向：编程静修、政府全额奖学金、开源导师制、远程带薪 Fellowship、免费 CTF、以及自己拉安全社区分会的入口。下面 4 条现在就能看/能准备，后面几条是"过几个月才开"但值得盯着的。

### 现在就值得看 / 能准备
1. **Recurse Center**（编程静修）
   类型：自我提升 / 可远程 ｜ 为什么适合你：Python/Linux/Git 够用，免费、滚动录取、现在就能申；产出公开项目、认识同行。
   资格：基本开放（会写小程序即可）。截止：滚动，无压力。
   价值：上限高、零成本。官方：recurse.com
2. **picoCTF（现已并入 CMU CyLab Security Academy）**（CTF / 安全练习）
   类型：竞赛 / 兴趣 ｜ 为什么适合你：直接练 cybersecurity 手感，完全免费、全年可练，比一次性比赛更能长期积累。
   资格：开放给大学生。截止：平台常年开放（年度赛 2027 待定）。官方：cylabacademy.org
3. **MLH Fellowship**（远程开源 Fellowship）
   类型：开源 / 带薪 ｜ 为什么适合你：远程友好，12 周合公开 PR、进全球开发者网络。
   资格：大概率符合（18+、中级编程；你大三应满 18）。时间：Spring 2027 批次约 10–12 月开申，滚动。官方：fellowship.mlh.io
4. **CyberCorps: Scholarship for Service（SFS）**（政府全额奖学金）
   类型：资助 / 职业 ｜ 为什么适合你：上限极高——学费+生活费全包，毕业直接进联邦政府网络安全岗。
   ⚠ 需确认：要求美籍 + 学校为 NCAE-C + 相关方向；你没填国籍，所以资格待确认。下一轮约 2026 年 12 月开申。官方：sfs.opm.gov

### 你想不到、但值得留意的方向
- **Outreachy** — 面向科技弱势群体、完全远程、3 个月付费 $7000 的开源实习（文档/代码都行）。下一轮 2027 年 2 月开申。
- **OpenSSF Mentorship** — 开源安全基金会的付费导师制，把新手培养成项目 maintainer；下一轮 2027。
- **OWASP 学生分会 / $20 会员** — 自己在学校拉起一个应用安全社区，低成本拓展人脉。
- **安全会议 CFP / 学生演讲** — BSides、DEF CON、PyCon 都收学生提案；这轮我只浅扫到不少海外/已过期的，没核实到具体的美国学生 CFP 页，建议你直接去 BSides 官网看近期 CFP。

### 需要你确认（才能给确定结论）
- SFS 的**国籍**与**学校是否 NCAE-C**；Outreachy 的**"弱势群体"身份**；OpenSSF 的**下一轮公布日期**（尚未出）。

### 覆盖说明（诚实版）
这轮在 US / 远程、en-US 下浅扫了 open_source / funding / research / event / skill / competition / networking 等类，并对 6 个官方来源做了核实；**讲者/CFP、研究型 REU、技术写作(GSoD)、专业学会**这几个方向只浅扫、未深核。这是有限预算下的覆盖，**不是全互联网完整扫描**。

### 下一步 & 追问
1. 现在就去 recurse.com 看最近一批次、在 picoctf 注册练一题。
2. 想冲 SFS：先确认自己是否美籍、学校是否 NCAE-C（这决定它对你是否成立）。
3. 想做开源：把 GitHub 活跃起来，为 MLH / Outreachy / OpenSSF 的下一轮做准备。
4. 对"建社区 / 做演讲"感兴趣吗？告诉我，我下轮深挖 OWASP 分会流程 + 美国安全会议的学生 CFP 页面。
