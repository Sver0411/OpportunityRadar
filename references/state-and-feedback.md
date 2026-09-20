# State & Feedback

本地轻量状态的语义。目标：**不重复推荐同一件事**、**注意到变化**、**让反馈影响下一轮**。
不引入数据库、服务端或复杂模型。

---

## 1. 目录与文件

```
.opportunity-radar/          # 相对宿主 Agent 的工作目录；可用 --dir 覆盖
├── profile.json             # 可选画像（见 profile-building.md）
├── seen.json                # 发现记录
├── saved.json               # Interested / Saved / Applied
├── ignored.json             # Ignored / Not Relevant
└── last-run.json            # 上次 Discovery 的结构化产物（见 output-format.md）
```

`.gitignore` 中应忽略整个目录（个人数据不进版本库）。

### seen.json

```json
{
  "version": 1,
  "updated_at": "2026-09-14T18:02:11",
  "entries": {
    "sony-embedded-internship-2027": {
      "opportunity_id": "sony-embedded-internship-2027",
      "title": "Sony Embedded Systems Internship",
      "organization": "Sony",
      "official_url": "https://example.com/careers/x",
      "first_seen": "2026-09-01T10:00:00",
      "last_seen": "2026-09-14T18:02:11",
      "tracked_hash": "b3f1c9…",
      "tracked": { "deadline": "2026-10-03", "application_open": null, "cost": null,
                   "compensation": "paid", "education_level": ["undergraduate"],
                   "student_year": null, "language_requirement": null, "official_url": "https://example.com/careers/x" },
      "change_log": [
        { "at": "2026-09-14T18:02:11", "field": "deadline", "from": "2026-10-03", "to": "2026-10-17" }
      ]
    }
  }
}
```

### saved.json / ignored.json

```json
{
  "version": 1,
  "updated_at": "2026-09-14T18:05:00",
  "entries": {
    "sony-embedded-internship-2027": {
      "opportunity_id": "sony-embedded-internship-2027",
      "title": "Sony Embedded Systems Internship",
      "organization": "Sony",
      "official_url": "https://example.com/careers/x",
      "status": "saved",
      "first_seen": "2026-09-01T10:00:00",
      "last_seen": "2026-09-14T18:05:00",
      "note": "need to check Japanese requirement"
    }
  }
}
```

---

## 2. 变化检测（Seen State 的核心）

**tracked 字段**（以 `scripts/common.py` 的 `TRACKED_FIELDS` 为准）：

```
deadline · application_open · application_status · cost · compensation ·
graduation_window · education_level · student_year · major_requirement ·
language_requirement · official_url · verification_status · country · region · city · organization_size
```

`tracked_hash` = 上述字段值的规范化 JSON 的 SHA-256 前 16 位。

### 规范化规则（与 dedupe 完全共用，避免"同一个 URL 两套规则"）

- URL 走 `scripts/common.py` 的 `canonical_url()`：host 转小写、**path 保留大小写**、
  只删除 `utm_*` 与明确点击追踪参数（`gclid`/`fbclid` 等），参数排序、去 fragment。
- 因此"只是追加了 `utm_source`"**不会**被误报为 `changed`（有测试覆盖）。
- `ref` / `source` / `from` 这类可能承载路由语义的参数**刻意保留**：
  它们变化时报 `changed` 是预期行为（宁可多提醒一次，也不要把真实变化漏掉）。
- Opportunity ID 走 `scripts/common.py` 的 `derive_id()`：
  **同一机会 + 同一周期 → 同一 ID；同一项目 + 不同年份/周期 → 不同 ID**。
  ID 规则变更会导致历史 Seen State 失配，所以改动必须同步更新 `seen.json` 或接受一次重扫。

最终答复确定后，只对**实际展示给用户**的机会执行；内部发现的候选不算 `seen`：

```bash
python3 scripts/state.py mark-seen --input .opportunity-radar/last-run.json --ids id-1,id-2
```

输出分三类：

| 分类 | 含义 | 输出处理 |
|---|---|---|
| `new` | 从未见过 | 正常推荐 |
| `changed` | 见过但 tracked 字段变了 | 完整推荐 + 写出**变了什么** |
| `repeat` | 见过且无变化 | 只进"已见过"小节列名 |

**变化样例**：deadline 延后 → 值得重新提醒；cost 由免费变收费 → 必须提醒；
language_requirement 新增 → 可能影响资格判定，需重跑 eligibility。

---

## 3. Feedback 状态

| 状态 | 存放 | 语义 |
|---|---|---|
| `interested` | saved | 用户表示想看更多同类（弱信号） |
| `saved` | saved | 用户明确收藏（强信号） |
| `applied` | saved | 用户已投递/已报名（后续应更新状态而非重推） |
| `ignored` | ignored | 用户当前不想看这类 |
| `not_relevant` | ignored | 用户认为"不适合我"（比 ignored 更强的负信号） |

用法：

```bash
python3 scripts/state.py feedback saved --id sony-embedded-internship-2027
python3 scripts/state.py feedback not_relevant --id some-hackathon --note "不想做比赛"
```

**对搜索的影响（必须有界且可解释）**：

- `saved` / `interested` → 下一轮提高对应 `tags` 与类别的权重；
- `not_relevant` → 下一轮降低对应**类别或标签**权重（**不是**降低整个大类，
  除非用户连续 3 次以上对同一类给出负反馈）；
- 影响只作用于**本次会话的排序与分类配额**，并要在输出里说明：
  > "按你之前的反馈，这轮降低了竞赛类权重。"

**禁止**：根据反馈偷偷永久改写 `profile.json`。
只允许建议：

```bash
python3 scripts/state.py suggest
# → 你似乎更关注 Embedded AI，是否提高该方向权重？
```

---

## 4. 能力缺口分析（Gap Analysis）

用户问"我现在缺什么""为什么很多机会我都申请不了"时：

```
输入：本次（或最近几轮）发现的机会集合
1. 汇总所有 skills_required / skills_preferred / language_requirement / GPA_requirement
2. 归一化词表（RTOS / C++ / Linux / 英语成绩 / 公开项目 / 论文 …）
3. 统计每个词的出现条数 M，与总数 N
4. 与 profile 已有能力对差 → 缺口清单，按 M 降序
5. 为每个高频缺口找"能补它的真实机会"（竞赛/项目/开源/认证/科研）
```

**话术约束（硬）**：

| ✅ 可以说 | ❌ 不能说 |
|---|---|
| 在本次扫描到的 23 条机会中，RTOS 出现在 9 条要求里 | 学 RTOS 能多 9 个机会 |
| 英语成绩是这 23 条里第 2 高频的要求 | 不考英语基本没戏 |
| 这是当前发现结果，不是全市场统计 | 嵌入式实习普遍要求 RTOS |
| 缺口 → 可参与的机会（附来源） | 缺口 → 一串课程/学习路线 |

必须显式声明样本范围与局限。

---

## 5. 读取与写入时机

| 时机 | 动作 |
|---|---|
| Discovery 开始 | 若目录存在 → 读 `seen.json`（用于 novelty 与重复过滤）；读 `saved/ignored`（用于权重） |
| 抽取完成后 | 写 `last-run.json` |
| 确定最终展示条目后 | `mark-seen --ids` 只更新展示过的 ID |
| 用户表达态度 | `feedback` 写入 saved/ignored |
| 用户问"我之前收藏的" | `list --status saved` |

**没有状态目录也能完整工作**（Skill 必须可选降级）。只在用户允许或工作目录可写时创建。

---

## 6. 隐私与失败处理

- 状态全部留在本地，**不发起任何网络请求**，不上传。
- 不写入：手机号、邮箱、身份证/学号、账号密码、简历原文。
- 目录不可写 → 跳过状态功能，在输出里一句带过，不阻塞主流程。
- `seen.json` 损坏/非法 JSON → 用 `state.py init --force` 前先备份为 `seen.json.bak`
  （由脚本自动完成），不要静默清空用户数据。

---

## 7. 命令速查

```bash
python3 scripts/state.py init                     # 创建目录与空状态文件（幂等）
python3 scripts/state.py mark-seen --input last-run.json --ids id-1,id-2
python3 scripts/state.py check --input last-run.json      # 只分类，不写入
python3 scripts/state.py feedback saved --id <id> --note "..."
python3 scripts/state.py list --status saved
python3 scripts/state.py show --id <id>
python3 scripts/state.py suggest                  # 只读，输出权重建议
```
