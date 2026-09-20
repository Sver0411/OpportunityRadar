# Case E — Round SI（Source Intelligence）全链路记录

## ① 原话
> 「最近没什么目标，就是想看看有没有我完全不知道但是值得做的事情。」

画像：美国大三 CS 学生，远程友好，兴趣 security + open_source，无目标、无 weekly_time。

## ② 来源计划（Source Intelligence 作为 unknown-unknown 入口）
用户无目标 → gaps 为空 → 不制造 bridge，改用 source family 作为**替代发现入口**：
- `contributor_guide`（安全开源 good first issue）→ 命中 **OWASP**
- `mentorship_program` / `foundation`（安全专项带薪导师制）→ 命中 **OpenSSF Mentorship**
- `community_event`（安全社区 CFP）→ 2026 各 CFP 已过期，记为 2027 常驻入口
- `general_search` 兜底（完全未知的进项）→ 命中 **漏洞赏金 / VDP**

## ③ 候选与 provenance
| 候选 | provenance | source_family |
|---|---|---|
| CyLab Security Academy / picoGym | general_search | — |
| picoCTF 年度赛 / LFX / GSOC / Recurse / Outreachy | general_search（沿用上轮 discovery） | — |
| OpenSSF Mentorship（安全专项带薪） | source_family_query | mentorship_program |
| OWASP 贡献入口（Juice Shop/BLT/PyGoat） | source_family_query | contributor_guide |
| 漏洞赏金 / VDP（HackerOne、DoD） | adjacent_discovery | — |

## ④ verification / evidence
- **picoGym**：fetch picoctf.org 确认已更名 CyLab Security Academy、免费、登录/练习区开放 → `verified_official` + `open`（recommended_now）。
- **OWASP**：fetch owasp.org 确认免费、多个项目持续接受贡献、入口常驻 → `verified_official` + `open_ongoing`。
- **OpenSSF Mentorship**：openssf.org 官方播客确认 2026 周期 3/24–4/12、带薪；2027 日期未公布 → `verified_official`（partial），`closed_2026_next_2027_unconfirmed`。
- 4 个 carry-forward 候选（LFX/GSOC/Outreachy/Recurse）本轮未重新 fetch，证据沿用上轮。

## ⑤ gaps（可能为空）
**为空**。用户输入无目标，且未发现可推导硬要求的"目标机会" → `gaps.py` 输出 0 条。这正是本 round 的预期：Source Intelligence 未用来制造目标或塞机会。

## ⑥ bridges（可能为空）
**为空**。`bridge_graph` 仅含 user 节点，`connected=false`。原因同上：无缺口 → 无 bridge；Source Intelligence 在此只做发现入口。

## ⑦ portfolio（small bets）
weekly_time 未知 → budget=None，无资源冲突。组合（按角色）：
- **now**：picoGym（随时可做，2–5h/周）
- **high_upside**：OpenSSF Mentorship、LFX、GSOC、Outreachy、漏洞赏金、picoCTF 年度赛、Recurse
- 无纯 **low_cost** 轻量项（picoGym 2–5h 超过 2h 阈值）；OWASP / 漏洞赏金属 **public_output / interest_asset** 类自驱小注。

对照建议：若优先"练手+公开作品"→ picoGym + OWASP 贡献 + 漏洞赏金 write-up；若优先"带薪履历"→ OpenSSF/LFX/GSOC/Outreachy。

## ⑧【用户最终回答】（白话中文，无内部术语）
你目前没有特定目标，所以我没帮你硬编目标，只是按你"安全 + 开源"的兴趣，找了几个**你可能完全不知道、但很值得做**的事：

1. **picoCTF / CyLab 安全学院**（CMU 免费）：它的练习题区是常年开放的，不用等比赛，现在就能登录做题练手。
2. **给 OWASP 项目做贡献**（比如 Juice Shop、BLT）：应用安全领域的开源项目，专门欢迎新手，改文档、修小 bug 都行，成果直接挂在 GitHub 上给人看。
3. **OpenSSF 带薪导师计划**：专做"软件安全"的开源导师制，上一期三分之二学员后来成了项目维护者；今年这期已截止，明年大概三四月再开。
4. **挖漏洞赚赏金**（HackerOne、美国国防部漏洞计划）：边练真实攻防边可能有收入，写份分析报告还能当作品集。
5. 顺带也提几个老牌但容易错过的：**LFX / Google 编程之夏 / Outreachy** 这类远程带薪开源实习，一年一两次，要提前半年关注。

这些都不需要你先有目标，挑一个最低门槛的（picoGym 或 OWASP 小贡献）先动起来就行。
