# Locale Knowledge

区域知识层。**按需加载** —— 这是增强层，不是 Core 的硬依赖。

```
references/locales/
├── generic.md   # 通用规则（Locale Selection Framework）—— 永远加载
├── cn.md        # 中国大陆：应届生 / 保研 / 夏令营 / 选词
├── jp.md        # 日本：卒業年度 / インターン / 在留資格 / JLPT
├── us.md        # 美国：work authorization / CPT / OPT / new grad / REU
├── uk.md        # 英国与爱尔兰：placement year / graduate scheme / right to work
└── de.md        # 德国：Praktikum / Werkstudent / HiWi / CEFR
```

## 加载规则

| 文件 | 何时加载 |
|---|---|
| `generic.md` | **总是**（决定用哪些语言、怎么处理未知地区） |
| `cn.md` / `jp.md` / `us.md` / `uk.md` / `de.md` | 仅当**目标地区**包含对应国家时 |

一次正常的机会发现**不应该**同时读进所有区域文件。多地区任务只加载对应那几份。

## 目标地区从哪来

运行时决定，不由示例或开发者偏好决定：

```
当前请求里可识别的地区  >  constraints.preferred_country  >  education.school_country  >  Global/Remote
```

`scripts/locales.py` 实现了这条链路：

```bash
python3 scripts/locales.py --profile examples/profiles/cs-student.example.json
python3 scripts/locales.py --countries "Germany,Netherlands"
python3 scripts/locales.py --list-locales
python3 scripts/locales.py --detect "https://www.example.fr/offres"
```

## 没有对应文件的国家怎么办

**照常工作**：走 `generic.md` + English + 页面语言动态检测。
`locale.py` 的表里收录的地区远多于上面这五个文件（如法国、荷兰、北欧、巴西、印度等），
它们有语言计划但没有专门知识文件 —— 这是设计意图，不是缺口。

**不要**因为没有区域文件就告诉用户"不支持该地区"。

## 为什么只有这几个文件

区域文件只在"当地规则复杂到容易判错"时才值得写（资格术语、时间线口径、特有形态）。
为了目录完整而给几十个国家各建一个空文件，只会增加维护成本、稀释加载纪律。

新增区域文件的门槛：**有真实的判错风险**（时间线口径、资格术语、特有项目形态），
而不是"这个国家还没有文件"。
