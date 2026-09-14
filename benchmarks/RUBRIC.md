# Opportunity Quality Rubric

每条 Opportunity 按 5 个维度评 0–3：

## Relevance（相关性）
- 0 基本无关
- 1 勉强相关
- 2 有一定相关性（与专业、技能或目标之一相关）
- 3 高度匹配（同时匹配专业、兴趣与目标）

## Eligibility（资格）
- 0 明显不符合（页面硬条件与画像冲突）
- 1 很可能不符合
- 2 Unknown / 部分符合（页面未写明或画像缺信息）
- 3 明显可申请

## Trust（可信度）
- 0 无可靠来源 / 疑似编造
- 1 只有第三方来源
- 2 找到官方来源但信息不完整
- 3 官方来源充分验证（截止日与资格可核对）

## Novelty（意外性）
- 0 用户显然会自己搜
- 1 普通搜索比较容易发现
- 2 用户可能不知道
- 3 很可能完全想不到

## Actionability（可行动性）
- 0 基本无法行动
- 1 信息不足
- 2 可以继续研究
- 3 截止日期 / 要求 / 官方入口明确，可直接采取行动

## 派生
- `useful = Relevance>=2 且 Trust>=2 且 Actionability>=2`
- `radar_only_useful`：useful 且仅出现在 OpportunityRadar 一侧
- 噪音指标：duplicate / expired / unverified / irrelevant / false eligibility
