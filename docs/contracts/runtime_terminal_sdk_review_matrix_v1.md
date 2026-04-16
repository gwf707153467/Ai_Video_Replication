# Runtime terminal SDK review matrix v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK review matrix**。

它服务于一个比 scaffold checklist 更偏 review / handoff / 验收的问题：

> 当最小 SDK 文档包已经逐步成形后，reviewer、receiver、交接负责人应该按什么维度审查，才能快速判断这个 SDK 包是否仍然停留在 v1 冻结边界内，而没有被 README、示例、异常包装或 package 组织方式悄悄带偏。

本文档与以下材料配套使用：
- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_readme_handoff_note_v1.md`
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`

本文档不重定义 API contract，不重开 complete / fail / snapshot 语义，不把 review matrix 扩成新的架构设计稿，也不越过 runtime terminal v1 freeze。

---

## 2. 这份 review matrix 要解决什么问题

scaffold checklist 已经回答了“实现者在落 SDK 时应该逐项检查什么”。

但到了 review / 交接阶段，问题通常会变成：
- reviewer 应先看 README 还是先看 client surface
- receiver 应如何判断 README 没有把 SDK 误写成平台 SDK
- 哪些点属于“一票否决”的越界问题，哪些点只是说明还不够完整
- 如果 review 失败，应该回到哪份文档修，而不是重新发散设计
- 如何把“边界正确”“示例正确”“异常分层正确”“交接包足够完整”放到同一个审查框架里

因此，本文档的目标不是新增规范，而是把现有已冻结结论组织成一份 **review 维度矩阵**，让不同角色可以用同一套口径判断：

> **这个 runtime terminal v1 SDK 包是否已经达到‘可交接、可复核、可继续维护’的最小标准。**

---

## 3. review 前默认前提

进入本 matrix 之前，以下结论默认已成立，review 时不再重开：

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

如果 review 过程中有人试图重新打开上述问题，默认视为 **超出本次 v1 review 范围**。

---

## 4. review 角色分工

| 角色 | 主要关注点 | 优先查看材料 |
|---|---|---|
| SDK 实作者 | 是否按最小骨架实现、是否越界 | scaffold note + scaffold checklist |
| reviewer | public surface、异常分层、README 口径、非目标能力是否混入 | review matrix + exception note + packaging note |
| receiver / handoff owner | 交接包是否够用、README 是否足够自解释、docs 是否能导航后续维护 | readme handoff note + docs index + review matrix |
| caller / adapter 维护者 | 接入路径、错误处理、snapshot 核验习惯是否清楚 | usage snippet + README + exception note |

推荐理解方式：
- **checklist** 更适合实现时逐项打勾
- **review matrix** 更适合 review / handoff 时做集中判定

---

## 5. review 使用方式

建议按以下顺序执行：

1. 先确认 review 对象是否仍然是“runtime terminal v1 最小 SDK 包”，而不是更大范围的 runtime 平台改造。
2. 按本 matrix 逐项判断 `通过 / 有条件通过 / 不通过`。
3. 每个“不通过”项都必须指向一份已有文档作为修正依据，而不是现场创造新口径。
4. 若发现问题涉及 API contract、写侧语义、调度能力扩展，默认记为 **越过 v1 freeze**。
5. review 结论应输出到一个简短结论记录中，便于后续 handoff 跟踪。

建议判定口径：
- **通过**：与当前冻结边界一致，表达完整，无显著误导
- **有条件通过**：边界没错，但文档、示例或导出面说明不足，需补充
- **不通过**：已出现语义越界、README 误导、异常口径错误或 package 失控

---

## 6. 核心 review matrix

### 6.1 范围与定位矩阵

| review 维度 | 必查问题 | 通过标准 | 常见不通过信号 | 主要依据文档 |
|---|---|---|---|---|
| SDK 定位 | 文档和代码是否仍把包定义为 runtime terminal v1 最小 SDK | 明确只覆盖 terminal write + snapshot read | README 或 package 命名把其写成统一 runtime platform SDK | docs index + readme handoff note |
| terminal 边界 | 是否仍围绕 complete / fail / snapshot | 只暴露 terminal write + snapshot read 主线 | 混入 claim、heartbeat、retry orchestration | scaffold note + packaging note |
| freeze 纪律 | 是否没有重开 API contract 和写侧语义 | review 只检视表达与封装，不改 contract | 借 review 名义重设计 complete / fail 语义 | docs index + scaffold note |
| 调用责任边界 | 是否保持 SDK 不做业务仲裁 | caller 决定 complete/fail、next_job_status、attempt_terminal_status 等 | SDK 自动替 caller 推导业务分支 | scaffold note + readme handoff note |

### 6.2 public surface 与骨架矩阵

| review 维度 | 必查问题 | 通过标准 | 常见不通过信号 | 主要依据文档 |
|---|---|---|---|---|
| public methods | 对外方法面是否最小 | 只围绕 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)` | 为“以后可能要用”提前暴露大量 endpoint wrapper | scaffold note + scaffold checklist |
| attempt context | 是否显式收束四元身份字段 | 存在 `RuntimeAttemptContext`，并收束 `job_id / attempt_id / worker_id / claim_token` | complete / fail 各自散落传参，或 SDK 内自行拼装上下文 | scaffold note + scaffold checklist |
| request helper | 是否存在统一 `_request(...)` 或等价最小 helper | request 层只负责发送请求、最小映射和返回结果 | `_request(...)` 内开始做自动恢复、自动决策、自动 payload 改写 | scaffold note + exception note |
| 导出面 | `__init__.py` 是否只导出稳定概念 | 只导出 client、attempt context、最小异常树 | 把内部 helper、payload builder、实验性对象也暴露出去 | packaging note |

### 6.3 异常契约矩阵

| review 维度 | 必查问题 | 通过标准 | 常见不通过信号 | 主要依据文档 |
|---|---|---|---|---|
| 最小异常树 | 是否保留统一基类 + `404 / 409 / 422 / 5xx / transport` 五层概念 | 至少有等价区分能力 | 所有失败都压成一个模糊大异常 | exception note |
| 409 语义 | 是否仍优先视为状态/上下文冲突 | README、代码、示例都不把 409 当默认网络重试 | 文档写成“409 可自动重试直到成功” | exception note + readme handoff note |
| 422 语义 | 是否仍优先视为 payload / schema 构造错误 | 保留 FastAPI / Pydantic 默认校验细节或其摘要 | 把 422 包成新的业务失败类型，掩盖字段错误 | exception note |
| transport 区分 | 是否把网络失败与 HTTP 语义错误分离 | transport error 与 404/409/422/5xx 可区分 | timeout 被归类成 conflict，或连接错误被归类成 validation | exception note |
| SDK 越权恢复 | SDK 是否没有在异常层自动修补或猜测 | 不自动重试 409、不自动猜其他 ID、不自动替换 claim_token | SDK 捕获错误后悄悄二次发送请求 | exception note + scaffold checklist |

### 6.4 payload 与语义表达矩阵

| review 维度 | 必查问题 | 通过标准 | 常见不通过信号 | 主要依据文档 |
|---|---|---|---|---|
| 四元身份同源 | 文档和示例是否重复强调同一次真实 attempt | README / 示例 / client 设计都要求四元字段同源 | 示例中从多个来源拼字段，或 SDK 自动补猜缺失字段 | scaffold note + readme handoff note |
| complete 语义 | 是否没有混淆 `completion_status` 与 `job_status` | 两者被明确区分 | 代码或 README 把 complete 成功直接写成 job 已达最终业务状态 | scaffold checklist + readme handoff note |
| fail 语义 | 是否把失败分支决策保留给 caller | `next_job_status`、`attempt_terminal_status`、`expire_lease` 由 caller 显式决定 | SDK 根据 error_code 自动改写 WAITING_RETRY / FAILED / STALE | scaffold checklist |
| payload 克制性 | 是否没有为了“统一风格”硬塞无意义字段 | 关键字段显式，非必要字段可省略 | 所有 payload 强制携带大量 null 或模糊 status 字段 | scaffold checklist |

### 6.5 README / 示例 / 交接矩阵

| review 维度 | 必查问题 | 通过标准 | 常见不通过信号 | 主要依据文档 |
|---|---|---|---|---|
| README 首页口径 | 首页是否足够快地说明“是什么 / 不是什么” | 前两屏内能看到最小定位与非目标能力 | README 像营销页，只讲好处不讲边界 | readme handoff note |
| 默认闭环示例 | README 示例是否体现 `build context -> write terminal -> handle explicit errors -> verify by snapshot` | 示例包含 context、terminal write、显式错误处理、snapshot 核验 | 只贴一段 POST 代码，完全不提 snapshot | readme handoff note + usage snippet |
| 相关文档导航 | README 是否指向 docs index / exception / packaging 等材料 | reviewer 与 receiver 能从 README 跳到主线文档 | README 孤立存在，接手人不知道下一份该看什么 | docs index + readme handoff note |
| 交接包组成 | 交付时是否至少包含最小代码面和最小文档面 | 代码 + README + docs index + usage snippet + exception note + packaging note 齐备 | 只交一个 README，或只交代码不交文档导航 | readme handoff note |

### 6.6 packaging 与可维护性矩阵

| review 维度 | 必查问题 | 通过标准 | 常见不通过信号 | 主要依据文档 |
|---|---|---|---|---|
| 最小包结构 | 是否优先维持 `client.py / models.py / errors.py / __init__.py` | 目录清楚、职责分层明确 | 单文件巨石实现，或目录提前膨胀成框架 | packaging note |
| 包命名 | 命名是否贴近 terminal 范围 | 名称围绕 runtime terminal SDK / client / adapter | 直接命名为 runtime platform SDK 或 orchestration SDK | packaging note |
| 依赖克制 | 是否没有为 v1 预支复杂度 | 单一主 HTTP 客户端、无双栈、无复杂 plugin/middleware | sync/async 双栈并上，或塞入 serializer / plugin 系统 | packaging note |
| 可抽离性 | 仓内包是否具备后续独立抽离条件 | 不把业务 repo 内部耦合直接暴露为 public API | public import 深度耦合业务仓内模块 | packaging note |

---

## 7. 一票否决项

出现以下任一情况，建议直接判定为 **review 不通过**：

1. README 或包命名把最小 terminal SDK 误写成统一 runtime 平台 SDK。
2. 对外 surface 超出 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)` 主线，且没有明确证明仍属 v1 最小范围。
3. SDK 自动 retry 409，或把 409 视为默认网络重试信号。
4. SDK 自动修补 payload、自动替换 `claim_token`、自动猜 `attempt_id`。
5. SDK 替 caller 自动决定 `next_job_status`、`attempt_terminal_status` 或 `expire_lease`。
6. 422 被包装成新的模糊 terminal 业务错误，导致字段校验细节丢失。
7. 包结构已明显膨胀为 claim / heartbeat / retry orchestration / workflow engine 入口。
8. README 示例没有任何 attempt context 同源约束提醒，反而鼓励拼装四元身份字段。

这些问题不是“文档再润色一下”能解决的，而是已经触碰 v1 freeze 边界。

---

## 8. 有条件通过项

以下问题通常不必直接一票否决，但应要求补齐：

- README 没有明确链接 docs index，导致导航性不足
- Quick start 示例过短，没有体现 snapshot 核验
- `__init__.py` 导出面虽然没越界，但缺少显式 `__all__`
- 异常对象保留的信息偏少，排障上下文不足
- handoff 包中缺失 scaffold checklist 或 caller FAQ 这类推荐材料
- package 说明没写清楚“为何不做 sync / async 双栈”

这类问题通常属于：
- 边界没错
- 但交接可用性、review 可读性或维护清晰度不足

---

## 9. 问题回溯矩阵

当某个 review 项失败时，建议优先回到下列文档修正，而不是现场新造规则。

| 失败类型 | 优先回看文档 | 原因 |
|---|---|---|
| README 把能力边界写大了 | `runtime_terminal_sdk_readme_handoff_note_v1.md` | 这里固定了 README 首页口径、非目标能力和交接表达纪律 |
| reviewer 不知道先看哪份文档 | `runtime_terminal_sdk_docs_index_v1.md` | 这里负责导航整个 SDK 文档主线 |
| public methods 或 attempt context 越界 | `runtime_terminal_minimal_sdk_scaffold_note_v1.md` | 这里固定了最小骨架和对象关系 |
| 实现细节模糊、需要逐项核对 | `runtime_terminal_sdk_scaffold_checklist_v1.md` | 这里提供逐项打勾的检查表 |
| 409 / 422 / transport 语义被写乱 | `runtime_terminal_sdk_exception_contract_note_v1.md` | 这里固定了最小异常树和状态码语义映射 |
| 目录、导出面、命名开始失控 | `runtime_terminal_sdk_packaging_note_v1.md` | 这里固定了最小包结构与导出边界 |
| 示例不够像真实接入闭环 | `runtime_terminal_sdk_usage_snippet_pack_v1.md` | 这里提供更接近调用侧动作的样例基础 |

---

## 10. 最小 review 结论模板

建议每次 review 至少留下如下结论记录：

```text
Review target:
Review date:
Reviewer:

Overall verdict:
- Pass / Conditional Pass / Fail

Confirmed scope:
- 是否仍是 runtime terminal v1 minimal SDK: Yes / No

Key findings:
1.
2.
3.

Blocking issues:
1.
2.

Required follow-up docs:
- 
- 

Freeze boundary reopened?:
- No / Yes (if yes, stop current review and escalate separately)
```

建议原则：
- 如果是 **Fail**，必须指出触发的是哪条一票否决项
- 如果是 **Conditional Pass**，必须指出还缺哪些交付物或表达补丁
- 如果 review 已触碰 freeze 边界，应单独升级讨论，不混在本次 handoff review 里继续推进

---

## 11. 建议的最小通过标准

一个 runtime terminal v1 SDK 包，如果想被判定为“最小可交接”，建议至少同时满足以下条件：

1. 定位正确：仍然只是 terminal write + snapshot read 的最小 SDK。
2. surface 正确：只围绕 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`。
3. context 正确：四元身份字段被显式收束，并强调同一次真实 attempt。
4. exception 正确：404 / 409 / 422 / 5xx / transport 语义可区分。
5. README 正确：清楚说明是什么、不是什么，并提供默认接入闭环。
6. packaging 正确：目录、导出面、命名、依赖保持克制。
7. handoff 正确：至少交付最小代码面和主线文档面，receiver 能继续维护而不必重新猜边界。

若这 7 条中有 1 到 2 条只是表达不充分，通常可记为 **有条件通过**。
若其中任何一条已经被明确做反，则通常应记为 **不通过**。

---

## 12. 本文档明确不做什么

本文档不负责：
- 重新设计 API contract
- 决定 complete / fail 的写侧实现细节
- 讨论 claim / heartbeat / retry orchestration 方案
- 扩展为统一 runtime platform review framework
- 替代 scaffold checklist、exception note、packaging note 的原始职责

它只负责把当前已冻结的 v1 SDK 结论整理成一份 **review / handoff 判定矩阵**。

---

## 13. 后续最自然增量方向

如果当前 review matrix 已经补齐，下一步最自然的增量通常不是继续扩 SDK 范围，而是补一个更贴交接动作的轻量成果，例如：

- `runtime_terminal_sdk_review_record_template_v1.md`
- 或一个面向实际包落地的 `README.md` 最小样板稿

优先级建议仍低于现有 freeze 边界内的主线清晰度；不要借 review matrix 之名重新打开更大范围设计。
