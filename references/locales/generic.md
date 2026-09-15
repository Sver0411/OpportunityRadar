# Locale Selection Framework

**这是通用规则，永远加载。** 它决定"用哪些语言搜索、加载哪个地区的知识文件"。

核心原则：

> **Core 不知道用户来自哪里，也不知道用户想去哪。**
> 地区来自运行时（Profile + 当前请求），语言随地区推导。
> 英文是"提升国际召回"的手段，不是无条件默认。

```
Profile / 当前请求
      ↓
目标地区（target regions）
      ↓
语言计划（primary / optional locales）
      ↓
区域知识文件（按需加载，缺失也能工作）
      ↓
Query 矩阵（类别 × 层 × 语言）
```

`scripts/locales.py` 把上面这条链路做成了可执行逻辑：

```bash
python3 scripts/locales.py --profile <profile.json> --mode A
python3 scripts/locales.py --countries "Germany,Netherlands"
python3 scripts/locales.py --detect "https://example.fr/offres"
```

---

## 1. 确定目标地区（precedence，不是合并）

`target_regions()` 按下表取值，**高层来源出现时低层来源不再参与**：

| source | 触发 | 行为 |
|---|---|---|
| `explicit_override` | 请求明确限定地区（"只找德国" / "only Germany"） | 只用请求地区，**忽略**画像里的长期偏好 |
| `explicit_additive` | 请求提到地区但非限定（"德国和荷兰也可以" / "US or remote"） | 请求地区在前，画像地区保留在后（可按语义舍弃） |
| `profile_fallback` | 请求没有地区 | `preferred_country` → `school_country` |
| `default_remote` | 什么都没有 | Global / Remote（不是默认某个国家） |

输出的 `region_source` 字段标明走了哪条路径；`region_hints` 始终保留用户提到的地区 ——
**地区和语言不是一回事**：未收录的国家（如 Kenya）也要作为 hint 传给搜索，
不能因为语言未知就把地区丢掉。

**职责边界**：从复杂自然语言里提取地理意图是宿主 Agent 语义层的职责；
本脚本只做 canonicalization、已知别名解析、locale 规划与兜底。
Free-text 的地区识别是 **best-effort**（只认 `COUNTRY_ALIASES` 里的写法）——
解析不了就要求 Agent 结构化传入，不要宣称能自动识别所有国家。

**不要**从"用户说中文"推断用户在中国，也不要从"用户专业是 IoT"推断用户想去日本。
语言与专业都不是地区证据。

### 1.1 省/市级定位（place hints）

国家级只解决"用哪种语言"；用户说"在杭州读书""江浙沪优先"时，**地名必须进入搜索 query**，
否则城市意图会丢失（彩排 u1 的真实教训）。

- 画像字段：`constraints.preferred_city`（城市）/ `constraints.preferred_region`（省、大区，如 浙江 / 江浙沪）。
- `scripts/locales.py` 会把识别到的地名放进 `place_hints`，并解析出所属国家参与 precedence
  （杭州 → china；东京 → japan；未收录的地名原样保留为 hint，不丢弃）。
- 生成 query 时：`<intent> + <place_hints>`（如 "会计 实习 杭州"、"internship Hangzhou"），
  而不是只搜国家级。
- 种子表刻意保守（中国省市 + 少量国际城市）；未收录地名不影响运行，由 Agent 结构化传入。
- **表是加速器和归一化工具，不是边界**：Agent 语义层识别出的任何地名（哪怕表里没有）都优先于表；
  表里没有的地名原样透传成 hint，搜索照常进行。只有在"地名 → 国家 → 语言"的自动推断需要确定性时
  （对比、复现、测试）才查表。

## 2. 解析语言计划

| 情况 | primary | secondary |
|---|---|---|
| 单一目标地区 | 该地区当地语言 | 英文（有国际项目/跨国企业价值时） |
| 多个目标地区 | 每个地区的当地语言（去重、按顺序） | 英文 |
| Global / Remote | 英文 | 用户明确具备的语言（可选） |
| 地区未收录 | 英文 | —— 首轮之后按检测结果补充 |

规则：

- **当地语言负责召回本地机会**（政府/大学/企业官网常只有本地语言版本）。
- 英文负责跨国公司、国际组织与远程机会；它是**候选（optional）**而非基线，也不是第二轮必搜清单（输出字段名即 `optional_locales`）。
- 多语地区按该地区的实际情况处理（如加拿大 = en-CA + fr-CA，瑞士 = de-CH + fr-CH）。
- 用户画像里记录的语言只作为**补充召回**，不改变目标地区的主语言。

## 3. 构建本地语言 query

对每个 primary locale，把 Taxonomy 的 **intent template** 本地化，而不是背一张国家表：

```
intent: "<field> internship"
zh-CN  → "<方向> 实习"
ja-JP  → "<分野> インターン"
de-DE  → "<Fach> Praktikum"
fr-FR  → "stage <domaine>"
```

本地化用词优先参考对应区域的 locale 文件；**没有该地区文件时，用第一轮搜索结果里的
实际页面用词**（页面怎么写就怎么搜），这比凭空翻译可靠。

## 4. 什么时候才加英文

**加**：跨国企业、国际组织、远程/全球项目、英文授课项目、开源社区、
"该地区该领域几乎只有英文资料"（如前沿 AI 研究）。

**不加**：用户明确只看本国机会（"我要找国内大三暑期实习"）时，不必为流程完整硬塞一批英文结果。
中文场景下，英文只在"国际项目/跨国企业"这类确实有增益的地方补一轮。

## 5. 语言未知或页面语言不明时（动态检测）

第一轮用 primary locale（或英文）搜索后，**根据结果页面的语言决定下一轮**：

```bash
python3 scripts/locales.py --detect "https://www.univ-xyz.fr/offres"   # → fr-FR（域名后缀）
python3 scripts/locales.py --detect "研究室のインターン募集"              # → ja-JP（含假名）
python3 scripts/locales.py --detect "https://example.com/ja/recruit"    # → ja-JP（路径前缀）
```

动态检测只使用**强信号**：ccTLD、URL 语言路径前缀、以及独特的文字系统（假名/谚文/汉字等）。
没有强信号时返回「无法判断」，不会假装识别出了语言。检测到新的主要语言 →
追加该语言的 query 变体；检测不出 → 用结果质量决定是否补充本地语言。

## 6. 没有对应区域文件的国家

**功能不受影响**：走本文件 + English + 动态检测。区域文件只是增强层。

例如用户说"想去芬兰"：`fi-FI` 会作为 primary（若 `locales.py` 的表中已收录该地区），
没有 `references/locales/fi.md` 也照常工作 —— 用芬兰语/英语搜索，
页面上的具体规则（申请周期、资格术语）现场从官方页面读。

**不要**因为没有 locale 文件就告诉用户"不支持该地区"。

## 7. 加载纪律

- **本文件（`generic.md`）永远加载。**
- 区域文件（`jp.md` / `cn.md` / `us.md` / `uk.md` / `de.md`）**只在目标地区需要时加载**：
  一次正常的机会发现不需要同时读进五份区域知识。
- 多地区任务只加载对应地区的那几份。

## 8. 反模式

- ❌ 无论用户在哪里都搜 EN + CN + JA 三种语言。
- ❌ 用户说"只看国内机会"仍然硬塞一批英文结果。
- ❌ 因为用户用中文交流就假设他只看中国机会。
- ❌ 因为没有 locale 文件就放弃该地区。
- ❌ 把区域知识的用词当成通用用词（"应届生"不是通用概念，"new grad"也不是）。
