# Runtime terminal SDK formal README review diff checklist v1

## 1. 文档定位

本文档是 `runtime_terminal_sdk_formal_readme_v1.md` 的**专项审阅清单**。

它服务于一个比通用 review matrix 更窄的问题：

> 当 formal README 候选稿已经生成后，reviewer 应如何快速判断：这份 README 是否严格继承 runtime terminal v1 冻结边界、是否没有把最小 SDK 写大、以及是否已经达到“可评审 / 可交接 / 可作为后续 README 替换候选”的最小标准。

本文档只审 README 候选稿本身，不重定义 API contract，不重开 complete / fail / snapshot 语义，也不把 README review 变成新的架构讨论。

目标审阅对象：
- `docs/contracts/runtime_terminal_sdk_formal_readme_v1.md`

配套参考文档：
- `runtime_terminal_sdk_readme_handoff_note_v1.md`
- `runtime_terminal_sdk_review_matrix_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_sdk_docs_index_v1.md`

---

## 2. 使用方式

建议 reviewer 按以下顺序使用本清单：

1. 先确认 review 对象仅为 formal README 候选稿，而不是整个 SDK 代码实现。
2. 再按本清单逐项标记：`Pass / Conditional Pass / Fail / N/A`。
3. 每个 `Fail` 或 `Conditional Pass` 都必须写明：
   - 问题位置
   - 偏离的固定口径
   - 建议回看的依据文档
4. 若发现问题已触碰冻结边界，应停止 README 润色式修订，升级到独立设计讨论。

建议判定口径：
- `Pass`：与冻结边界一致，表达明确，无明显误导
- `Conditional Pass`：边界没错，但表达不充分、导航不清或示例不够稳
- `Fail`：已出现范围越界、语义误导、错误口径错误或 handoff 风险

---

## 3. 默认冻结前提

本清单默认以下结论已冻结，不在 README review 中重开：

- terminal = terminal write + snapshot read
- SDK 只围绕 `complete_job(...)` / `fail_job(...)` / `get_job_snapshot(...)`
- 不重定义 API contract
- 不重开 complete / fail / snapshot 语义
- 不扩展到 claim / heartbeat / retry orchestration
- SDK 不做业务仲裁
- SDK 不自动 retry `409`
- SDK 不自动修补 payload
- SDK 不自动替换 `claim_token`
- `job_id / attempt_id / worker_id / claim_token` 必须来自同一次真实 attempt
- `completion_status` 不等于 `job_status`
- complete / fail 成功后建议做 snapshot 核验
- `422` 保持 FastAPI / Pydantic 默认行为
- facade 写侧不绕过 service 直写 repository

如果某条意见试图重开上述结论，默认记为：**超出 formal README review 范围**。

---

## 4. 一票否决项

出现以下任一情况，建议直接判定 README review 为 `Fail`：

1. 把最小 terminal SDK 写成 unified runtime platform SDK。
2. 把 README 写成 claim client、heartbeat manager、retry orchestration framework、scheduler entrypoint 或 business-state arbiter。
3. 暗示 SDK 会自动 retry `409`。
4. 暗示 SDK 会自动修补 payload、自动替换 `claim_token`、自动猜 attempt identity。
5. 混淆 `completion_status` 与 `job_status`。
6. Quick start 没有体现 snapshot 核验，且误导“写成功 = 业务状态已正确消费”。
7. 将 `422` 改写成新的业务语义 contract，而不是保持默认校验定位。
8. README 文案鼓励从多处拼装 `job_id / attempt_id / worker_id / claim_token`。

---

## 5. 核心 review checklist

> 建议 reviewer 直接复制下表逐项打标。

### 5.1 首页定位与一句话简介

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| 一句话简介是否准确 | 必须为：`A minimal SDK for runtime terminal v1 terminal writes and snapshot reads.` |  |  |
| 首页是否足够早说明这是最小 SDK | 前两屏内明确出现 minimal SDK / minimal client 定位 |  |  |
| 是否说明当前是 formal README candidate | 明确说明不替换仓库根 `README.md` |  |  |
| 是否说明 repository note / packaging note | 明确根项目仍是 `ai-videos-replication`，`[project].readme` 仍指向根 `README.md` |  |  |

### 5.2 What this package is

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| 是否明确只做 terminal v1 最小 SDK | 只覆盖 terminal write + snapshot read |  |  |
| 是否明确 public methods 主线 | 只围绕 `complete_job(...)` / `fail_job(...)` / `get_job_snapshot(...)` |  |  |
| 是否说明适用对象 | 可面向 worker reporters / lightweight adapters / caller-side integrations |  |  |
| 是否强调最小、稳定、可复用、可交接 | 至少有等价表达 |  |  |

### 5.3 What this package is not

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| 是否明确不是 unified runtime platform SDK | 必须明确 |  |  |
| 是否明确不是 claim client | 必须明确 |  |  |
| 是否明确不是 heartbeat manager | 必须明确 |  |  |
| 是否明确不是 retry orchestration framework | 必须明确 |  |  |
| 是否明确不是 business-state arbiter | 必须明确 |  |  |
| 是否明确不是 scheduler entrypoint | 必须明确 |  |  |

### 5.4 Public surface 与最小包结构

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| 是否只暴露三类稳定公共概念 | `RuntimeTerminalClient` / `RuntimeAttemptContext` / minimal exception tree |  |  |
| 是否给出最小 package layout | `client.py` / `models.py` / `errors.py` / `__init__.py` |  |  |
| 是否避免暴露内部 helper / framework 化对象 | README 不应鼓励扩展 internal-only objects |  |  |
| 是否明确 `RuntimeAttemptContext` 的四元身份收束作用 | 必须出现 `job_id / attempt_id / worker_id / claim_token` 同源提醒 |  |  |

### 5.5 Quick start 默认闭环

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| 是否使用固定默认闭环 | `build context -> write terminal -> handle explicit errors -> verify by snapshot` |  |  |
| 示例是否包含 `RuntimeAttemptContext` | 必须出现 |  |  |
| 示例是否包含 `RuntimeTerminalClient` | 必须出现 |  |  |
| 示例是否包含 `complete_job(...)` | 必须出现 |  |  |
| 示例是否包含 `get_job_snapshot(...)` | 必须出现 |  |  |
| 示例是否保留最小 `fail_job(...)` 示例 | 必须出现或等价补充 |  |  |
| 是否提醒 `completion_status` 不等于 `job_status` | 必须出现 |  |  |
| 是否提醒 SDK 不自动 retry `409` | 必须出现 |  |  |
| 是否提醒 SDK 不自动修补 payload | 必须出现 |  |  |
| 是否提醒 SDK 不自动替换 `claim_token` | 必须出现 |  |  |

### 5.6 Error handling 口径

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| `409` 是否解释为 state / lease / attempt-context conflict | 默认不自动重试 |  |  |
| `422` 是否解释为 caller or payload construction issue | 先修请求构造 |  |  |
| `404` 是否解释为 object missing or wrong identifier | 先核标识与对象存在性 |  |  |
| `5xx` 是否解释为 server or infrastructure issue | 可有限重试 |  |  |
| transport error 是否与 HTTP semantic conflict 分开 | 必须分离表达 |  |  |
| 是否明确 `422` 保持 FastAPI / Pydantic 默认行为 | 必须出现 |  |  |

### 5.7 Boundary / non-goals

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| 是否再次固定 terminal 边界 | terminal = terminal write + snapshot read |  |  |
| 是否明确 SDK 不做业务决策 | 不替 caller 决定业务语义 |  |  |
| 是否明确 SDK 不自动 retry `409` | 必须出现 |  |  |
| 是否明确 SDK 不自动 repair payload | 必须出现 |  |  |
| 是否明确 SDK 不自动 replace `claim_token` | 必须出现 |  |  |
| 是否明确不推导 / 合成 attempt identity | 必须出现 |  |  |
| 是否明确不包装新的 `422` 业务 schema | 必须出现 |  |  |
| 是否明确 facade 写侧不直写 repository | 必须出现 |  |  |
| 是否列出 v1 non-goals | 至少包含 claim / heartbeat / retry orchestration / scheduler entrypoints / business arbitration |  |  |

### 5.8 Related docs 与 handoff notes

| 检查项 | 期望口径 | 结果 | 备注 |
|---|---|---|---|
| 是否给出 related docs 列表 | 必须指向 docs index、exception、packaging、usage snippet 等材料 |  |  |
| 是否具备新维护者阅读顺序建议 | 推荐 reading order 清楚 |  |  |
| 是否包含 handoff note | 必须出现 |  |  |
| handoff note 是否明确“不要重开的问题” | 必须列出不应在 README 中重新发散的问题 |  |  |
| 是否提醒未来改动优先走增量文档或独立设计轨 | 必须出现或等价表达 |  |  |

---

## 6. 差异审阅重点（Diff Focus）

当 reviewer 比对 formal README 候选稿与既有 README / handoff note / review matrix 时，建议重点看以下“差异是否合理”：

| Diff focus | 应接受的差异 | 不应接受的差异 |
|---|---|---|
| README 语气 | 从草案风格收敛为正式 README 风格 | 为了“更像产品 README”而放大能力边界 |
| 结构组织 | 更适合 README 首页阅读 | 删除关键 non-goals、错误口径、snapshot 核验提醒 |
| Quick start | 适度简化示例长度 | 省略 `RuntimeAttemptContext` 或 snapshot 核验 |
| packaging note | 增加仓内 package candidate 说明 | 假装当前仓库已完成独立发布包切换 |
| related docs | 调整顺序、强化导航 | 移除关键依据文档，导致接手人无法追溯 |
| handoff note | 收敛成面向 README 的交接提醒 | 借 handoff note 偷偷重开 freeze boundary |

---

## 7. 常见 Conditional Pass 情况

下列情况通常可判为 `Conditional Pass`，而不是直接 `Fail`：

1. 首页边界没错，但 repository note 不够清楚。
2. Quick start 有主流程，但 snapshot 核验提醒不够醒目。
3. error handling 表格正确，但对 transport error 的区分还不够直白。
4. related docs 已列出，但阅读顺序或适用场景说明偏弱。
5. handoff note 已存在，但“不要重开的问题”列得不够完整。

建议修复方式：
- 只补表达与导航
- 不改冻结结论
- 不借 README review 扩 scope

---

## 8. 最小 review 记录模板

```text
Review target:
- docs/contracts/runtime_terminal_sdk_formal_readme_v1.md

Review date:
Reviewer:

Overall verdict:
- Pass / Conditional Pass / Fail

Checklist summary:
- Passed items:
- Conditional items:
- Failed items:

Blocking issues:
1.
2.

Recommended edits:
1.
2.

Need freeze-boundary escalation?:
- No / Yes

If yes, stop README review and escalate separately.
```

---

## 9. 建议的通过标准

若该 formal README 候选稿想被判定为“review-ready”，建议至少同时满足：

1. 首页一句话简介准确。
2. “是什么 / 不是什么”边界清楚。
3. public surface 与 package layout 克制且稳定。
4. Quick start 体现默认闭环与 snapshot 核验。
5. error handling 维持 `409 / 422 / 404 / 5xx / transport` 的固定解释。
6. boundary / non-goals 没有松动。
7. related docs 与 handoff note 足以支撑下游继续维护。
8. repository note 没有误导 reviewer 以为已替换根 `README.md` 或已完成独立发布。

只要第 1、2、4、5、6、8 任一项明显做反，通常不建议通过。

---

## 10. 本文档不做什么

本文档不负责：
- 改写 formal README 正文
- 重新设计 SDK public API
- 决定是否把候选稿替换到仓库根 `README.md`
- 扩展 claim / heartbeat / orchestration 能力
- 审核 runtime terminal 服务端 contract

它只负责一件事：

> 让 reviewer 用统一口径快速判断 formal README 候选稿是否仍然忠实于 runtime terminal v1 最小 SDK 冻结边界。
