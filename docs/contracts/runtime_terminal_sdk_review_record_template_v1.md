# Runtime terminal SDK review record template v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK review record template**。

它不是新的 review 规则文档，而是把已经在以下材料中冻结的 review 口径，压缩成一份可直接复用的 **review 记录模板 / handoff 审查记录模板**：

- `runtime_terminal_sdk_review_matrix_v1.md`
- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_readme_handoff_note_v1.md`
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`

本文档服务于一个更实际的交接动作：

> 当 reviewer、receiver、handoff owner 已经按照 review matrix 完成检查后，应该如何留下结构化记录，确保结论可追踪、可回看、可交接，而不是把 review 结论散落在聊天、口头确认或临时注释里。

本文档不新增 API contract，不重开 complete / fail / snapshot 语义，不扩展 runtime terminal v1 freeze，也不替代 review matrix 本身。

---

## 2. 这份模板要解决什么问题

在 runtime terminal v1 的 SDK 交接阶段，真正容易丢失的通常不是“有没有 review”，而是：

- review 结论没有统一格式，后续无法快速回看
- reviewer 写了一堆点评，但 receiver 不知道哪些是阻塞项、哪些只是补充项
- 有人说“原则上可过”，但没有明确写清是 `Pass`、`Conditional Pass` 还是 `Fail`
- 发现问题后，没有写清应回看哪份既有文档修正，导致现场重新发散设计
- handoff 时无法快速确认：这次 review 到底有没有触碰 v1 freeze 边界

因此，这份模板只做一件事：

> **把 review matrix 的判定结果，沉淀成最小而稳定的交付记录。**

---

## 3. 使用前默认前提

填写本模板之前，默认以下结论已经成立，记录时不再重开：

- terminal = terminal write + snapshot read，不是调度入口
- SDK 只围绕 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`
- 不重定义 API contract
- 不重开 complete / fail / snapshot 语义
- 不扩展到 claim / heartbeat / retry orchestration
- SDK 不做业务仲裁
- SDK 不自动 retry 409
- SDK 不自动修补 payload
- SDK 不自动替换 `claim_token`
- `job_id / attempt_id / worker_id / claim_token` 必须来自同一次真实 attempt
- `completion_status` 不等于 `job_status`
- complete / fail 成功后建议做 snapshot 核验
- 422 保持 FastAPI / Pydantic 默认行为，不强制包装为新的 terminal 自定义错误 contract

若 review 过程中重新打开上述问题，建议不要继续把争论写进本模板，而应先标记为：

- `Freeze boundary reopened = Yes`
- 并升级为独立议题处理

---

## 4. 适用场景

本文档适用于以下场景：

1. SDK 最小实现包的首次 review 记录
2. README / handoff 包补齐后的复审记录
3. receiver 正式接收前的验收记录
4. reviewer 需要给出结构化结论并指向修正文档
5. 多轮 review 之间需要保持统一结论口径

不建议用于：

- 新架构方案讨论
- API contract 改动提案
- 写侧实现语义争论
- claim / heartbeat / orchestration 范围扩展讨论

---

## 5. 填写原则

建议 reviewer / handoff owner 按以下原则填写：

### 5.1 先写结论，再写评论
先明确总体结论：
- `Pass`
- `Conditional Pass`
- `Fail`

不要只写“整体还行”“基本可交接”这类模糊表述。

### 5.2 每个不通过项都要能回溯
只要出现阻塞项或补齐项，都应明确写出：
- 问题现象
- 影响判断
- 应回看哪份既有文档

不要把问题写成新的开放设计题。

### 5.3 区分阻塞项与补齐项
- **阻塞项**：一票否决、越界、语义错误、README 明显误导、异常契约错误、public surface 明显失控
- **补齐项**：边界没错，但文档导航、示例闭环、导出面、交接材料还不完整

### 5.4 发现 freeze 被重开时要立刻标记
如果 review 过程开始讨论：
- 是否纳入 claim / heartbeat
- 是否自动 retry 409
- 是否让 SDK 自动推导 payload / 状态分支
- 是否重写 422 contract

则不应在本记录内继续细化解决方案，而应直接标记：
- `Freeze boundary reopened = Yes`

### 5.5 记录必须对下一个接手人可读
一个从未参与前序讨论的人，读完记录后应至少能回答：
- 这次 review 审的是什么对象
- 结果是过 / 有条件过 / 不过
- 阻塞点在哪里
- 下一步该回哪份文档修

---

## 6. 结论等级定义

| 结论 | 含义 | 适用情况 |
|---|---|---|
| Pass | 可作为 v1 最小 SDK 包继续交接 | 范围、surface、异常、README、packaging、handoff 都无显著问题 |
| Conditional Pass | 边界基本正确，但还需补齐少量文档/表达/导出细节 | 没有一票否决项，但存在推荐补齐项 |
| Fail | 当前不应进入交接 | 已触碰一票否决项，或已明显越过 v1 freeze |

建议纪律：
- 出现一票否决项时，不建议写成 `Conditional Pass`
- 只有当问题主要属于“表达不完整”而非“边界做反”时，才适合 `Conditional Pass`

---

## 7. 推荐填写顺序

建议按以下顺序填写 review record：

1. 基本信息
2. review 对象与版本范围
3. 已检查材料
4. 总体结论
5. 范围确认
6. 核心发现
7. 阻塞项 / 补齐项
8. 问题回溯文档
9. freeze boundary 是否被重开
10. 跟进动作与责任人

---

## 8. 可直接复用的 Markdown 模板

以下模板可直接复制使用。

```md
# Runtime terminal SDK review record

## 1. Review metadata

- Review target:
- Review scope:
- Review date:
- Reviewer:
- Receiver / handoff owner:
- Related package / branch / commit:

## 2. Overall verdict

- Verdict: Pass / Conditional Pass / Fail
- Ready for handoff: Yes / No
- Freeze boundary reopened: No / Yes

## 3. Scope confirmation

- Is this still runtime terminal v1 minimal SDK? Yes / No
- Still limited to terminal write + snapshot read? Yes / No
- Still limited to `complete_job(...)` / `fail_job(...)` / `get_job_snapshot(...)`? Yes / No
- Any claim / heartbeat / retry orchestration capability mixed in? No / Yes
- Any API contract or write-side semantics reopened? No / Yes

## 4. Materials checked

- [ ] `runtime_terminal_sdk_review_matrix_v1.md`
- [ ] `runtime_terminal_sdk_docs_index_v1.md`
- [ ] `runtime_terminal_sdk_readme_handoff_note_v1.md`
- [ ] `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- [ ] `runtime_terminal_sdk_scaffold_checklist_v1.md`
- [ ] `runtime_terminal_sdk_exception_contract_note_v1.md`
- [ ] `runtime_terminal_sdk_packaging_note_v1.md`
- [ ] `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- [ ] README / package landing page
- [ ] SDK code surface (`client.py / models.py / errors.py / __init__.py`)

## 5. Summary findings

### 5.1 What is confirmed correct
1.
2.
3.

### 5.2 Conditional issues
1.
2.
3.

### 5.3 Blocking issues
1.
2.
3.

## 6. Matrix-based assessment

| Dimension | Verdict | Notes |
|---|---|---|
| Positioning / scope | Pass / Conditional Pass / Fail | |
| Public surface | Pass / Conditional Pass / Fail | |
| Attempt context | Pass / Conditional Pass / Fail | |
| Exception contract | Pass / Conditional Pass / Fail | |
| Payload / semantic expression | Pass / Conditional Pass / Fail | |
| README / quick start | Pass / Conditional Pass / Fail | |
| Packaging / maintainability | Pass / Conditional Pass / Fail | |
| Handoff completeness | Pass / Conditional Pass / Fail | |

## 7. Boundary checks

- README clearly says this is **not** a unified runtime platform SDK: Yes / No
- SDK does **not** auto-retry 409: Yes / No
- SDK does **not** auto-repair payload: Yes / No
- SDK does **not** auto-replace `claim_token`: Yes / No
- SDK does **not** auto-guess `attempt_id`: Yes / No
- `job_id / attempt_id / worker_id / claim_token` are explicitly treated as same-attempt identity: Yes / No
- 422 keeps FastAPI / Pydantic validation detail semantics: Yes / No
- README quick start suggests snapshot verification after complete / fail: Yes / No

## 8. Required document backtracks

| Issue | Backtrack document | Reason |
|---|---|---|
|  |  |  |
|  |  |  |
|  |  |  |

## 9. Follow-up actions

| Priority | Action | Owner | Due date |
|---|---|---|---|
| P0 |  |  |  |
| P1 |  |  |  |
| P2 |  |  |  |

## 10. Handoff decision

- Can receiver continue maintenance without reopening design? Yes / No
- Can this package be handed off as runtime terminal v1 minimal SDK? Yes / No
- Next recommended artifact or patch:

## 11. Reviewer note

> 
```

---

## 9. 极简文本模板

如果场景不适合保留完整 Markdown，可使用以下极简版本：

```text
Review target:
Review date:
Reviewer:
Receiver / handoff owner:

Overall verdict:
- Pass / Conditional Pass / Fail

Confirmed scope:
- Still runtime terminal v1 minimal SDK: Yes / No
- Freeze boundary reopened: Yes / No

Key findings:
1.
2.
3.

Blocking issues:
1.
2.

Conditional issues:
1.
2.

Backtrack docs:
- 
- 

Follow-up actions:
- 
- 

Handoff decision:
- Ready for handoff: Yes / No
- Next recommended artifact:
```

---

## 10. 推荐写法示例

下面给出一个更贴近实际 handoff 的简短示例。

```md
## Overall verdict
- Verdict: Conditional Pass
- Ready for handoff: Yes, after README quick start patch
- Freeze boundary reopened: No

## Summary findings
### What is confirmed correct
1. SDK public surface 仍然收束在 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`。
2. `RuntimeAttemptContext` 已显式收束四元身份字段，并强调同一次真实 attempt。
3. 409 / 422 / 5xx / transport 语义分层未越界。

### Conditional issues
1. README 首页尚未明确链接 docs index，导致 handoff 导航不足。
2. Quick start 示例未体现 complete 成功后的 snapshot 核验。

### Blocking issues
1. None.

## Required document backtracks
| Issue | Backtrack document | Reason |
|---|---|---|
| README 未提供导航入口 | `runtime_terminal_sdk_docs_index_v1.md` | 应补齐主线阅读顺序 |
| Quick start 未体现 snapshot 核验 | `runtime_terminal_sdk_readme_handoff_note_v1.md` | README 默认闭环应固定为 write then verify |
```

这个示例体现的重点不是措辞漂亮，而是：
- 结论等级明确
- 阻塞项与补齐项分开
- 问题可追溯到既有文档

---

## 11. 最小记录完成标准

一次合格的 SDK review record，建议至少满足以下条件：

1. 写清 review target、日期、角色。
2. 明确给出 `Pass / Conditional Pass / Fail` 之一。
3. 明确写出是否仍是 runtime terminal v1 minimal SDK。
4. 明确写出 freeze boundary 是否被重开。
5. 至少列出 1 组 summary findings。
6. 若有问题，必须区分 blocking 与 conditional。
7. 若有问题，必须指向既有文档进行回溯修正。
8. 明确写出 handoff 是否可继续。

如果一份记录只写“review 通过，后续再看”，则不建议视为有效交接记录。

---

## 12. 本文档明确不做什么

本文档不负责：

- 替代 `runtime_terminal_sdk_review_matrix_v1.md`
- 重写 review 维度或新增技术结论
- 给出新的 API 设计建议
- 讨论 claim / heartbeat / orchestration 的未来扩展
- 取代 README、docs index、exception note、packaging note 的原始职责

它只负责把现有冻结结论，沉淀为一份最小、稳定、可复用的 review 记录模板。

---

## 13. 后续最自然增量方向

如果这一层也固定完成，后续最自然的增量方向通常有两个：

1. 面向实际包落地的 `README.md` 最小样板稿
2. 面向 reviewer / receiver 的 review record 实例稿（基于真实 SDK 包填一份样例）

推荐优先级上，若当前目标仍是 **文档交接闭环**，下一步更自然的是：

- `runtime_terminal_sdk_readme_minimal_template_v1.md`

因为 review matrix 与 review record template 已经把“怎么审、怎么记”固定下来，接下来最容易落地的是“README 到底怎么写成最小可交接文本”。
