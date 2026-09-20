# Source Families（最小版 Source Intelligence）

**定位**：不是静态网址收藏夹，也不是白名单搜索器。它只回答一件事：

> 已经识别出某个 Gap 时，这类 Bridge 通常藏在**哪一类官方来源**里、应该先发什么 query。

```
Gap Type → Bridge Intent → Source Family → Targeted Query → general search fallback
```

## 加载规则

| 文件 | 何时加载 |
|---|---|
| 本文件 | 需要规划来源时 |
| `research.md` | 缺口类型含 `research` / `network`（研究型 Bridge） |
| `language.md` | 缺口类型含 `language` |
| `oss.md` | 缺口类型含 `portfolio` / `public_reputation` / `leadership`（开源生态入口） |

**registry 没有某大学/某基金会/某国家 ≠ 不搜索它**：未收录来源照常走 general discovery，
新发现的高质量来源可在本轮使用，并可选记录到 `.opportunity-radar/sources.json`。

## 硬纪律

1. **来源不提升可信度**：来自 known source 的候选仍要过 canonical source / freshness /
   application-status evidence / eligibility / dedupe / readiness / utility / bridge gate。
2. **阶段敏感**：同一个研究缺口，本科生与在职者的 Bridge 不同（见各文件的 stage 变体）。
3. **`historical_yield` 只用于排序偏好**：相同预算下先扫历史上出过成果的来源；
   不能因此停止搜索其他来源，Explore 预算必须保留。
4. **失败类型沿用三分类**：`process` / `fact` / `infrastructure`
   （`source_not_found` / `source_found_no_opportunity` / `source_found_not_current` /
   `page_not_verifiable` / `js_rendered` / `blocked`）。
5. **第三方只能做 discovery / cross-check**，不能因为官方页打不开就当成官方证据。

## 候选来源要记录 provenance

每个候选标记来源：
`known_source` / `source_family_query` / `general_search` / `adjacent_discovery` ——
否则无法判断 Source Intelligence 到底有没有提升召回。

## 代码

`scripts/sources.py` 是这一层的唯一事实来源（families、intent 映射、阶段变体、query 规划、
轻量 yield 状态）。
