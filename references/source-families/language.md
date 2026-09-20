# Language Bridge 来源

**适用缺口**：`language`（缺语言成绩/等级）。目标不是"推荐语言课程"，而是找到**可认证的语言证据**。

## Source families

| family | 常见页面 | 典型 query intent |
|---|---|---|
| `official_exam_body` | 考试日程 / 官方模考 / 报名 | `<exam> official test dates registration`、`公式 模擬試験` |
| `university_language_center` | 大学语言中心课程 | `university language centre <lang> short programme` |
| `government_cultural_body` | 文化机构课程 / 交流 | `<country> cultural institute <lang> course programme` |
| `language_exchange_program` | 语伴 / 交换项目 | `<lang> language exchange programme university` |
| `speech_contest` | 演讲/翻译比赛 | `<lang> speech contest students apply` |
| `official_training_program` / `scholarship_language_program` | 官方培训 / 语言奖学金 | `<lang> scholarship language programme` |

**canonical source 判断**：考试主办方、大学、政府文化机构官网；语言学校与中介只作 discovery。

## 缺口 → family

| 缺口 | 优先 family |
|---|---|
| 缺 `JLPT N2` 这类等级 | `official_exam_body`（考试规划）→ `university_language_center` → `speech_contest`（把语言变成公开证据） |
| 缺英语成绩（IELTS/TOEFL） | `official_exam_body` → `university_language_center` |
| 目标国语言但无成绩记录 | `government_cultural_body` → `language_exchange_program` |

**注意**：`speech_contest` 这类属于"语言能力 → 公开证据"的 Bridge，
比单纯再考一次更能补 `portfolio` / `public_reputation` 缺口；但是否真的有助于目标仍走 Bridge scoring。
