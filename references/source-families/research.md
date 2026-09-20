# Research Bridge 来源

**适用缺口**：`research`（研究经历/产出）、`network`（教授接触）、`experience`、`education`。

## Source families

| family | 常见页面 | 典型 query intent |
|---|---|---|
| `university_lab` | 实验室主页 / 招生页 / 教員紹介 | `<topic> laboratory open positions students`、`研究室 学生 募集` |
| `professor_page` | 教授个人主页 / 招生说明 | `professor <topic> recruiting students` |
| `research_seminar` | 开放讲座 / 见学会 / workshop | `<topic> open seminar registration students` |
| `summer_research` | 暑研 / research internship / visiting student | `summer research programme <topic> international students` |
| `research_institute` | 研究所项目 / 实习 | `<topic> research institute internship programme` |
| `academic_society` | 学会学生会员 / 委员会 | `<topic> professional society student member programme` |
| `research_funding_body` | 资助 / fellowship / travel grant | `<topic> research grant students apply` |
| `graduate_school` | 招生页 / 在职项目 / 研究生制度 | `graduate school part-time programme admissions` |

**canonical source 判断**：大学/机构域名（`.edu` / `.ac.jp` / `.ac.uk` / `.edu.cn` / `.uni-*.de`）
+ 院系或实验室页面；聚合站只作 discovery。

## 按缺口细分（不要一个 query 打天下）

| 缺口 | 优先 family |
|---|---|
| 缺教授接触 | `research_seminar` → `professor_page` → `academic_society` |
| 缺研究经历 | `summer_research` → `research_institute` → `university_lab` |
| 缺研究产出（论文/海报） | `research_funding_body` → `university_lab` → `academic_society` |
| 在职申请硕士的准备 | `graduate_school` → `research_seminar`（见学/开放讲座）→ `professor_page` |

## 阶段变体（必须使用 life_stage / career_stage）

- **undergraduate**：`summer research programme undergraduate`、`undergraduate lab`,
  `lab tour undergraduate students`
- **working**：`part-time research programme working professionals`、
  `industry-academia collaborative project`、`open seminar working professionals`、
  `研究生 見学会 社会人`

不要补完职场支持后又在来源层退回学生视角。
