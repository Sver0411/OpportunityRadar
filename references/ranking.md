# Ranking

Step 11–12。目标：把 20–40 条候选压成 5–15 条**值得看**的推荐，并且**能解释为什么**。

两条铁律：

1. **Match ≠ Priority。**
2. **分数不是结论，是排序辅助。** 任何分数都必须能拆成可读的理由。

---

## 1. Match 与 Priority 的区别

| | 定义 | 回答的问题 |
|---|---|---|
| **Match** | 与用户画像的契合度（不含时间） | "这个机会本身适合我吗？" |
| **Urgency** | 时间压力 | "我还来得及吗？" |
| **Priority** | `0.85 × Match + 0.15 × Urgency` | "我现在应该先看哪个？" |

**紧迫度以截止端点为基准**：`9月20日~10月5日` 这类报名窗口取 10-05
（`scripts/normalize_date.py` 的 `urgency_days` 已经这样实现），不要把开始日当截止日。

标准例子（必须能正确处理）：

```
Opportunity A  Match 95  Deadline 6 个月后   → Priority ≈ 95×0.85 + 25×0.15 ≈ 84.5
Opportunity B  Match 88  Deadline 2 天后     → Priority ≈ 88×0.85 + 100×0.15 ≈ 89.8
```

→ **B 排在 A 前面**，并且在输出里说明"因为 2 天后截止"。
把 Match 当唯一排序键是本 Skill 要修掉的典型错误。

无 deadline（滚动招募/常年开放）→ 不施加 urgency 项，`Priority = Match`，
并在输出注明"滚动招募，无截止压力"。

---

## 2. 组件与权重

**权重的唯一来源是 `scripts/common.py` 的 `WEIGHTS`**（本表必须与之一致，由
`tests/test_consistency.py` 自动校验），`scripts/score.py` 直接导入使用。

| 组件 | 权重 | 数据来源 | 缺失时 |
|---|---|---|---|
| `eligibility` | 0.26 | 第 10 步判定 | Ineligible → 直接排除，不进排序 |
| `goal_fit` | 0.19 | profile.goals ↔ 机会类别 | 无 goals → 中性 60 |
| `skill_fit` | 0.15 | skills_required/preferred ↔ profile.skills | 要求未知 → 中性 50（不是 0） |
| `interest_fit` | 0.11 | tags/summary ↔ profile.interests | 无兴趣字段 → 中性 55 |
| `location_fit` | 0.10 | country/city/remote ↔ constraints | 无地区约束 → 中性 60 |
| `value_fit` | 0.08 | opportunity.value ↔ goals 优先级 | 未评估 → 中性 55 |
| `trust` | 0.06 | trust_tier | 未知 → 50 |
| `novelty` | 0.05 | seen state | 无 state → 80 |

判定分映射：`Eligible` 100 / `Probably Eligible` 82 / `Unknown` 55 /
`Probably Ineligible` 25 / `Ineligible` 0（排除）。

**修正项（不进权重，单独呈现）**

- 过期（deadline 已过）→ 排除，或移到"已失效"小节的单行。
- `time_commitment` 超过 `constraints.weekly_time` → `heavy_load` 标记，
  Priority 扣 5 分，并在 △ 注明。
- 未找到官方来源（`unverified`）→ Priority 扣 8 分 + △ 注明。

`score.py` 输出分为 `High (≥80)` / `Medium (60–79)` / `Low (<60)` **三档**。
不要把原始分数当作精确评价展示给用户；用档次 + 理由。

---

## 3. 覆盖度指导（不是硬配额）

**主动搜索** Adjacent / Explore 方向；**当它们达到质量与验证门槛时纳入结果**。
绝不要为了满足份额而塞入弱机会。

以下数字是防止"所有机会都退化成实习"的**覆盖面参考值**，不是必须凑齐的指标：

| 项目 | 参考值 |
|---|---|
| 类别数 | 开放性问题 ≥3 类；目标明确时 ≥2 类 |
| 层数 | 尽量包含 Adjacent 与 Explore 各 ≥1 条 |
| 单类上限 | 任一类别不超过结果总数的 50% |
| 机构上限 | 同一机构不超过 2 条（同一企业的 3 个岗位 → 合并或只留最相关 1 条） |
| 已见过滤 | `seen` 且**无变化**的条目默认不进主列表，移入"已见过"小节 |

如果 Adjacent / Explore 一条都没有合格机会：**用一句话如实说明**（试过哪些层、为什么没通过
门槛），不要静默省略，也不要拿弱机会顶替。

如果某类别明显没货（例如只有 career 有结果）：如实说明覆盖不足，不要用凑数条目填满。
覆盖度自检结果由 `scripts/score.py` 的 `diversity` 字段输出，作为参考而非强制。

---

## 4. Value 评估（不需要精确数字）

对进入主列表的机会，按需评估以下维度，取值 `High / Medium / Low / Unknown`
（高价值项可再加一句理由）：

| 维度 | 判定要点 |
|---|---|
| `career` | 是否被该领域雇主认可、是否直通后续招聘（如選考直結型）、是否有 return offer 路径 |
| `research` | 是否有导师指导、是否能产出署名/成果、是否与后续升学挂钩 |
| `skill` | 是否强制上手用户想学的技术、是否有 mentor/评审反馈 |
| `portfolio` | 交付物能否公开/写进简历（开源 PR、作品、数据集、报告） |
| `networking` | 是否能接触到从业者/导师/同侪社群 |
| `financial` | 有薪/奖金/资助额度/免费资源（含云资源、硬件） |
| `interest` | 与用户兴趣领域的重合度（Mode B 尤为主要） |

**价值评分必须有依据。**
某个机会如果确实多个维度都是 High，就写全部 High——**不要为了"看起来真实"而人为降级**。
没有依据的维度用 `Unknown`，不要编一个 Medium 凑平衡。
判断依据可以是：有薪且直通后续招聘（career）、有导师与署名产出（research）、
交付物可公开进作品集（portfolio）、页面明确写了 mentor 或社群（networking）等。

---

## 5. 排序 tie-breaker（分数接近时按序使用）

1. 官方来源更完整（`verified_official` 优先）
2. 时间窗口更紧
3. 门槛更低（对用户更可达）
4. 层数更高（Explore > Adjacent > Exploit，用于保护多样性）
5. 类别覆盖面（补足当前结果里缺失的类别）

---

## 6. 写理由的规则

每条推荐的"为什么推荐给我"必须**引用具体字段**，不能写套话。

```
为什么适合你
✓ 接受本科生（official page：学部生・修士課程）
✓ 技能要求 C/C++ 与你的 C 技能匹配
✓ tags: embedded / tinyml 与你 Embedded + AI Agent 兴趣重合
✓ 地点符合你的 Japan 偏好

可能的问题
△ 页面未写明日语要求
△ 需要线下面试（页面写「対面面接あり」）
△ 每周 20 小时，与你 15 小时上限冲突
```

要求：
- 3–5 条 ✓，每条形如"页面/字段依据 + 与画像的连接"。
- 1–3 条 △，优先写**能改变用户决定**的不确定性，而不是鸡毛蒜皮。
- 不用"含金量高""非常有帮助""强烈推荐"这类无依据形容。

---

## 7. 反模式

- ❌ 直接采用搜索引擎排名当排序。
- ❌ 制造精确到小数点的"科学分数"并展示给用户。
- ❌ 全部结果来自同一类别（尤其全是实习）。
- ❌ 忽视 deadline：把两个月后截止的和两天后截止的混排。
- ❌ 名校/大厂偏见：只推知名度高的，漏掉门槛低但匹配度高的机会。
- ❌ 把 Explore 层当作"凑数的第 8 条"而不是真正的发现。
- ❌ 同一项目因来源不同重复占据多个名额（应先跑 dedupe）。
- ❌ 对 Unknown 的资格直接按 0 分处理（会把大量真实可申请的机会错杀）。
