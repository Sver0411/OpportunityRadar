# Case B — 职场人士转向 Edge AI（V3 专业场景回归验证）

## ① 用户原话

> 我是做了三年嵌入式的工程师，最近感觉有点卡住，想往 Edge AI 转，每周大概只能拿出 6 个小时，有什么值得做？

（画像来自 `benchmarks/personas/early-career-engineer.json`：三年嵌入式固件工程师、全日制在职、目标日本 Edge AI 工程师、每周 6 小时、不接受无薪长期实习与每周超 15 小时。）

---

## ② 实际做的事

**定位与语言计划（运行 `scripts/locales.py --profile … --mode D`）**
- 目标地区：日本 + 远程（来自画像 `preferred_country: Japan`、`remote: true`）
- 主搜索语言：日语（`ja-JP`）；补充：英文、中文（画像已具备中文）
- 模式：能力反推（D）——围绕"为转 Edge AI 现在该补什么"展开，同时压低纯求职、抬高开源/项目/技能/大会
- 加载区域知识：`references/locales/generic.md`、`references/locales/jp.md`
- 覆盖类别：开源、开发者计划、行业大会与人脉、专业认证与兼职学习、竞赛、职业岗位

**执行的 6 条检索（每条对应专业适用类别，刻意避开"仅学生"入口）**
1. `Edge AI TinyML open source contribution good first issue 2026 GitHub` → 开源贡献
2. `エッジAI 開発者プログラム Edge AI developer program Coral Jetson STM32Cube.AI 無料` → 开发者计划/技能
3. `Edge AI conference Japan 2026 call for speakers エッジAI 勉強会 コミュニティ` → 大会/人脉
4. `TinyML Edge AI challenge contest 2026 hardware competition professional` → 竞赛（筛选专业/已过期项）
5. `Edge AI engineer remote jobs Japan エッジAIエンジニア 求人 リモート 経験者` → 职业岗位（作为 6–12 个月目标参照）
6. `Edge AI professional certificate course part-time TinyML training online 2026` → 专业认证/兼职学习

**验证（4 次页面深读，均回到官方一手来源）**
- ST 官方 STM32 AI 资源页（`stm32ai.st.com`）
- edX 上 HarvardX TinyML 证书页
- Linux Foundation 的 ONE Summit Japan 2026 页面
- TinyMLDelta 仓库的 CONTRIBUTING 文档（GitHub 官方）

**覆盖说明**：本轮没有把任何"学生实习 / 仅学生竞赛"作为主推。检索中出现的「IEEE COINS 的 ST TinyML 赛（6 月已截止）」「某 Kaggle 比赛（页面标注面向学生）」「2021 年的 tinyML Vision Challenge（已结束）」均被排除，因为它们要么过期、要么仅面向学生，对一位在职工程师不是合适入口。

---

## ③ 给用户的最终回复

### 本轮结论
你是在职工程师、每周只有 6 小时，所以这一轮我专门找"能直接上手、能形成公开作品、不绑定你太久"的专业机会，而不是学生实习或比赛。下面 4 条现在就能开始，另有 1 条「半年后的目标岗位」帮你反推还差什么。

### 最值得现在处理（现在就能开始）
这 3 条投入都在 6 小时/周以内、能产出可展示的成果，且和你已有的 C/嵌入式/RTOS 经验直接接得上：

**1. STM32 Edge AI 开发套件（ST 官方免费工具）**
- 是什么：意法半导体官方的 Edge AI 工具集——STM32Cube.AI（把训练好的神经网络自动转成 STM32 能跑的 C 代码）、NanoEdge AI Studio（自动生成异常检测/预测性维护模型）、ST Edge AI Developer Cloud（在线基准测试+模型库），外加 50+ 实战案例和一门 MOOC。
- 为什么与你有关：你三年嵌入式固件（C/RTOS），目标 Edge AI；这套工具正好把你的 MCU 经验接到"把 AI 部署到芯片上"，而且是日本/全球嵌入式主流平台。
- 资格：面向所有开发者，免费、无学历/年级限制 → 符合。
- 当前状态：官网常驻、随时可用。
- 准备度：可直接开始（已具备 Embedded C、RTOS）。
- 投入：自定进度，约 3–5 小时/周，不超你的上限；免费。
- 主要产出：一个能在 STM32 上跑的 Edge AI demo（异常检测/视觉），可进 GitHub 和简历。
- 长期价值：直接补齐"ML 部署到 MCU"这条最短缺口，对应目标岗位的高频要求（量化、部署、Jetson 类）。
- 可能问题：最好有一块低成本 STM32 开发板（或先用 Developer Cloud 在线跑）；进阶功能会用到一点 Python。
- 官方来源：https://stm32ai.st.com/resources/ （日文版 https://stm32ai.st.com/ja/products/）

**2. HarvardX TinyML 专业证书（edX，哈佛 + Google TensorFlow）**
- 是什么：TinyML 专业证书，3 门课、16 周、自学节奏，含一个 Arduino 实物套件的动手项目。
- 为什么与你有关：体系化补"无 ML 基础"这个瓶颈——量化、部署、TensorFlow Lite Micro 全讲到；是面向工程师的职业证书，不是学生课。
- 资格：官方写明"入门级、无需先验经验、自学节奏" → 符合。
- 当前状态：常年开放报名，随时开始。
- 准备度：少量准备（需补一点 Python，几小时到一两天）。
- 投入：2–4 小时/周（在 6 小时以内）；费用约 $807.30（≈人民币 5,800）。
- 主要产出：结课证书 + 一个可在 Arduino 上跑的 TinyML 应用（可展示）。
- 长期价值：名企背书的系统 ML 基础，是跳槽 Edge AI 的"硬通货"之一。
- 可能问题：需付费；部分实验依赖开发板套件；英语授课（你 IELTS 6.0 能读）。
- 官方来源：https://www.edx.org/certificates/professional-certificate/harvardx-tiny-machine-learning

**3. TinyMLDelta 开源贡献**
- 是什么：一个给微控制器上的 ML 模型做"增量更新/差分"的开源项目（Edge AI 模型基础设施层）。
- 为什么与你有关：项目明确欢迎嵌入式 AI 开发者，需要 C 运行时代码和 STM32/ESP32/NRF52 等 MCU 移植——和你的 C/嵌入式/Git 完全对口，且远程、时间灵活。
- 资格：欢迎代码/文档/示例/测试各类贡献，无门槛 → 符合（早期项目，倾向"可能符合"）。
- 当前状态：仓库活跃、持续招募贡献者。
- 准备度：可直接开始（已具备 C、Git）。
- 投入：灵活，约 2–4 小时/周，不超上限。
- 主要产出：合并的 PR、公开的 GitHub 贡献记录——正是你想要的"公开作品"。
- 长期价值：真实开源履历 + 进入 Edge AI 开发者圈子，比"自己学"更有说服力。
- 可能问题：项目较早期、维护者少，任务需自己认领；不是大厂背书。
- 官方来源：https://github.com/felixgalindo/TinyMLDelta/blob/main/CONTRIBUTING.md

### 机会组合（为半年后铺路 / 认识人和资源）
**4. ONE Summit Japan 2026（东京，边缘计算与开源峰会）**
- 是什么：Linux 基金会旗下、东京举办的开放网络与边缘计算峰会，含「Edge AI & Data at the Edge」主题，与 Open Source Summit Japan 同期。
- 为什么与你有关：就在日本、直接讲边缘 AI 与开源部署，是认识日本 Edge AI 从业者/雇主的最低成本入口，契合你的日本目标。
- 资格：面向工程师/架构师/研究者/开源贡献者开放参会 → 符合。
- 当前状态：2026-12-10~12-11 东京，报名已开放；今年演讲征集已截止（讲者路线留到下一届）。
- 准备度：可直接报名参会（无需前置，仅差旅/报名费）。
- 投入：2 天参会，或先只注册关注；远低于 6 小时/周。
- 主要产出：人脉、行业认知、可写进"关注方向"的笔记。
- 长期价值：为半年后日本求职铺路——现场可对接 ST、Idein 这类边缘 AI 公司。
- 可能问题：需赴东京差旅；今年讲者通道已关。
- 官方来源：https://events.linuxfoundation.org/open-networking-edge-summit-japan/

**5. 日本 Edge AI 工程师岗位（作为 6–12 个月目标，不是现在"顺手做"）**
- 是什么：日本企业招聘的 Edge AI / ML Engineer 岗（如某 AI 算法公司的全远程岗、Idein 的 Actcast 边缘 AI 平台、RobotJobJapan 的 Edge AI ML Engineer）。
- 为什么与你有关：这正是你 12 个月后的目标角色；现在看能反推"还差什么"。
- 资格：多数要求"ML 部署经验（量化/蒸馏/剪枝、TensorRT/ONNX/TVM、Jetson 等）+ 商务日语 N2"——你目前缺 ML 经验、日语仅 N4 → 现在"可能不符合"，属未来目标。
- 当前状态：常年招募，随时可看。
- 准备度：需先补 ML 部署经验 + 日语，是主要准备项。
- 投入：全职岗位，不在 6 小时/周范围（是未来主线）。
- 主要产出：未来投递目标清单 + 反向明确能力缺口。
- 长期价值：方向锚点。
- 可能问题：硬性要求日语 N2 与 ML 经验，现阶段不匹配；远程岗也多要求日语商务级。
- 官方来源：https://www.daijob.com/en/jobs/detail/1546523 ；https://helloworldjapan.com/cn/jobs/idein

### 你可能没想到的方向
- **开源贡献（TinyMLDelta）**：比"再报一门课"更被雇主认可，且直接吃你的 C/嵌入式老本行——多数人在职转行会忽略这条。
- **去日本行业大会当观众**：不用演讲也能低成本建立人脉、搞清日本公司在招什么，是"非求职"却最实用的入口。

### 能力 / 准备缺口（基于本轮扫描到的岗位与机会）
- 在本轮扫描到的日本 Edge AI 岗位中，**ML 部署/量化经验**与**日语 N2**各出现在多条要求里；**Python**是证书与岗位的通用前置。
- 你的「公开作品 / 开源贡献」诉求，正好由上面第 1、3 条直接满足。
- 说明：这是本轮发现结果的统计，不是全市场结论；不保证"补了 X 就多 N 个机会"。

### 搜索覆盖说明
按"日本 + 远程"、日语为主 + 英文补充，覆盖了开源 / 开发者计划 / 行业大会与人脉 / 专业认证与兼职学习 / 竞赛 / 职业岗位 6 类；刻意排除了仅面向学生的实习与竞赛（某 Kaggle 赛标注"面向学生"、IEEE COINS 的 TinyML 赛已于 6 月截止），未作为主推。

### 下一步
1. 这周先装 STM32Cube.AI、跑通一个官方示例（异常检测），把第一个 demo 推到 GitHub。
2. 报名 HarvardX TinyML 证书，先补 Python 基础再开课；同时认领 TinyMLDelta 的一个 `good first issue`。
3. 注册 ONE Summit Japan 2026 的观众票（或先关注），并收藏 2–3 个日本 Edge AI 岗位作为能力对照表。
