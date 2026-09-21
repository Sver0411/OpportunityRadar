# RC2 Last Mile Report（2026-09-21）

本轮只做四件事：① D 的主线选择 ② D 的已有职业资本可见 ③ E 的 Explore 查询与核实多样化
④ 两处文档修正。然后**只真实重跑 D 与 E**。测试 **510 → 525**，preflight 与 CI 全绿。

---

## 1. D 是否 5/5

**是。** D2 是一次全新的独立会话（fresh profile / state / 候选池，不读任何其它目录），
逐条引用它自己的产物：

| # | 标准 | 判定与证据 |
|---|---|---|
| 1 | 体现已有 5 年后端资本 | ✅ `starting_point.capital = ["5 年后端开发经验", "目前在职（可以边工作边投入）"]`；即使 `skill_fit = 0` 也先写资本 |
| 2 | 拒绝实习降级路线 | ✅ 主推荐只有 vLLM（notes 明写"不是雇佣岗位、也不是实习"）+ MLOps Community；无实习/无薪条目 |
| 3 | 识别 AI production / platform bridge | ✅ 主线 vLLM 的 `public_evidence = ["合并进 vLLM 的公开 PR…"]`（serve / inference-infra），全场无课程 |
| 4 | 6h 约束正确 | ✅ `resource_conflict = false`；主推条目的周小时数未写明时，分配写明"不做时间加总"而**不给总计**；`%` 与"每天 X 小时"出现 0 次 |
| 5 | 单一 external mainline 由目标相关性决定 | ✅ 见下一节 |

## 2. D 主线最终是谁、为什么

**`vllm-open-source-contribution`**，`why = "与目标相关度最高（goal_fit 80）；后续通道 high；Utility medium"`。

更急的条目（剩余 5 天 / 13 天）**没有抢主线**，落在 `worth_verifying`。
**诚实说明**：正因为紧急项不在主推集合里（`main`）里，"近期窗口"这个新标签这次**没有被真实触发** ——
行为是对的（urgent 不再等于主线），但该标签只在单元测试里验证过，真实运行未覆盖。

## 3. Career Capital 是否可见

可见，且回答里只写一次（在顶部，不是每张卡重复）：

```text
**你的起点**：5 年后端开发经验、目前在职（可以边工作边投入）。
而这套工程经验可以往上叠：本轮优先找能补 **AI 工程（AI 工程方向） 相关的可验证经历**、
指向 **AI 工程师（AI 工程方向）** 的机会。
```

后半句（"可以往上叠"）只在**有 gap / produces 支持**时才写 —— 无支持时只写前半句（有测试固定）。
读的字段只有用户**明确提供**的那些：`employment.role / years_of_experience / seniority / industry / status`。

## 4. E query lens 分布

`plan_explore_queries()` 在 E 上给出 **4 条**（`lens_limit = 4`，≥3 达标），E2 会话实际共发 5 条查询：

| lens | 条数 |
|---|---|
| build | 1 |
| volunteer | 1 |
| creative | 1 |
| community | 1 |
| research | 1（`plan_explore_queries` 被 limit 截断的下一条镜头） |

门控是严格的：`explore_lens_enabled()` 只在 **Mode C + 无 goals + career_direction == explore** 时为真，
A/B/C/D 全部返回 `enabled: false`（有测试固定）。

## 5. E verification lens 分布

`select_verification_targets(..., mode="C")` 选中 4 个目标，覆盖 4 个不同镜头：
`contribute / build / community / cross_domain` 各 1（`verification_selected_because = top_in_axis`）。

**lens-top finalist 的 `verification_attempt_rate = 4/4 = 100%`，0 次基础设施失败。**
验证门槛一个没降（`canonical source` / `freshness` / `application_status` / `verified_official` 全不变），
候选数据也未被修改（有测试断言）。

## 6. E 最终 presented axes

用工具对**呈现集合**重新计算：**6 条轴** —— `build, community, contribute, creative, research, volunteer`。

对比口径（不只看一个数字）：

```text
available_high_quality_axes    = 6   （真正合格候选覆盖到的轴）
presented_axes                 = 6
差额                            = 0   → 没有为过 benchmark 塞弱条目
十字轴 cross_domain            = 两侧都没有（唯一候选已过期被排除）
```

（E2 会话自己报的是 7 = 7，差异来自它把一条被排除的条目也算进了 available；以工具重算的 6/6 为准。）

## 7. E 若 0 recommended，原因是 fact/infra 还是 process

**本轮不适用：E2 有 3 条主推荐**（We Are Human Film&AI，9/30 止；NASA 公民科学，官方页核实无国籍限制；
OIN Solicitation 6.0，10/22 止）。

7 条 excluded 的降级原因**全部是"时间已过"（fact）**，例如 SDGs Challenge 的官方页自证 2026 届 7/31 已闭。
没有 `verification_not_attempted` 或 `missing_evidence_structure` 这类 **process** 原因。

## 8. 零容忍指标

用当前代码对 D2 / E2 复核（`expired / unverified actionable / source stale / violations / leakage /
self-directed mixed`）：

```text
D2: expired=0  unverified=0  stale=0  violations=0  leakage=0  self_directed=0
E2: expired=0  unverified=0  stale=0  violations=0  leakage=0  self_directed=0
合计 = 全部 0
```

A/B/C **没有重新联网跑**（按你的要求）；改为把它们独立会话的结构化产物固化成回归基线
`usertests/rc2-validation/inputs/{A..E}/`，由 `tests/test_rc2_regression.py` 保证
新的主线选择器 / 起点段 / Explore 镜头规划**不让它们变形**（含"不得断言用户没说过的偏好"
"主线必须是目标相关性最高的那条""呈现轴数等于真实可达轴数"等不变量）。

## 9. preflight / CI

`python3 scripts/preflight.py` → **PASSED**（compile → 525 单测 → skill 包校验）。
CI：见本报告所在提交的 3.8 / 3.12 两个 job，均为 success。

顺带修掉本轮重跑暴露的两处展示缺陷（都属"不得伪精确/不得误导"这一类）：
① 定性分配里"这些机会都没写明小时数"那条分支漏了 `mainline` 字段；
② 卡片把 `Build time 24 hours（未标注周投入量）` 渲染成"每周约 24 小时" —— 现在只有
"这句话就是在说每周几小时"时才写成"每周约 X"，并且 `_parse_hours` 会拒绝文本自己声明"不是每周投入"的情况。

## 10. 是否已打 `v3.0.0-rc2`

**已打。** 条件逐条核对：

```text
D Golden 5/5                                  ✅
E query lenses >= 3（实际 5）                  ✅
E lens-top finalist verification attempt 100%  ✅
E 无 diversity stuffing（presented == available）✅
E 未放松 evidence gate                          ✅
六个零容忍指标全 0                              ✅
python3 scripts/preflight.py 全绿               ✅
```

→ `git tag -a v3.0.0-rc2`，已推送。

**下一阶段（不再开 synthetic feature development）**：5 个真人 →
原始输入 → 真实点击 / 收藏 / 行动 → 3–7 天 Follow-up → `usertests/real/SUMMARY_ROUND1.md`。
