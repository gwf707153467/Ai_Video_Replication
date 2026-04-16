# Runtime terminal SDK README minimal template v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK README minimal template**。

它不是新的 SDK 设计文档，也不是新的 handoff note，而是把已经在以下材料中冻结的 README / handoff 表达口径，压缩成一份可直接复用的 **README 最小模板**：

- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_readme_handoff_note_v1.md`
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_sdk_review_matrix_v1.md`
- `runtime_terminal_sdk_review_record_template_v1.md`

本文档服务于一个更实际的问题：

> 当 runtime terminal v1 的最小 SDK 包已经冻结后，README 到底应该怎样写，才能让接手人快速理解、快速接入、快速避坑，同时不把 README 写成新的平台方案文档。

本文档不新增 API contract，不重开 complete / fail / snapshot 语义，不扩展 runtime terminal v1 freeze，也不替代 README handoff note 本身。它只负责把“**README 最少应该写什么、怎样写才不越界**”固定下来。

---

## 2. 这份模板要解决什么问题

runtime terminal v1 的最小 SDK 包，在代码层面的边界已经很清楚；真正容易失控的，往往是 README。

常见偏差包括：

- 把最小 terminal client 写成“统一 runtime platform SDK”
- 把 README 写成功能介绍页，却没有把能力边界说清楚
- 只给调用片段，不说明 409 / 422 / 5xx 的责任归属
- 只写如何 `complete` / `fail`，不提醒成功后建议做 snapshot 核验
- 首页没有明确说明：四元身份字段必须来自同一次真实 attempt
- 没告诉接手人：哪些问题已经冻结，哪些问题不要在 README 里重新展开设计
- 交接时缺少一个可以直接复制、轻改、即用的 README 结构

因此，这份模板只做一件事：

> **把 runtime terminal v1 最小 SDK 的 README 表达，固定成一份可直接复用、可 review、可 handoff 的最小骨架。**

---

## 3. 使用前默认前提

在填写本模板之前，默认以下结论已经冻结，README 不应重新争论：

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
- 422 保持 FastAPI / Pydantic 默认行为
- 最小 package surface 以 `client.py`、`models.py`、`errors.py`、`__init__.py` 为主

如果 README 编写过程重新打开上述争论，建议不要继续在 README 里扩写，而应直接升级为独立议题。

---

## 4. 适用场景

本文档适用于以下场景：

1. 为 runtime terminal v1 最小 SDK 编写首版 README
2. 将已有 README 收敛成更稳定的最小交接文本
3. 为仓内 handoff / 对外 package landing page 提供统一骨架
4. 为 reviewer 提供 README 是否越界的检查参考
5. 为 receiver 提供一个可快速判断边界是否清晰的模板基础

不建议用于：

- 新架构方案讨论
- API contract 改造提案
- claim / heartbeat / retry orchestration 范围扩张说明
- 平台级统一 SDK 设计草案
- 复杂多语言 SDK 落地方案比较

---

## 5. 编写原则

### 5.1 先写“是什么”，再写“怎么用”

README 首页前两屏，应优先回答：

- 这是什么包
- 它不是什麽包
- 它解决什么问题
- 它不解决什么问题

不要一上来就堆代码片段。

### 5.2 先写边界，再写便利性

runtime terminal v1 的 README 首要目标不是“显得功能很多”，而是“防止调用方误用”。

因此建议优先强调：

- terminal write + snapshot read
- 最小 public surface
- 责任边界
- 错误处理口径
- snapshot verification 建议

### 5.3 Quick start 只展示默认闭环

README 的 quick start 不应试图覆盖所有参数组合，而应优先体现默认闭环：

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

### 5.4 非目标必须写成显式文字

不要把“非目标”留给接手人猜。

至少应显式写出：

- 不是调度入口
- 不是 claim client
- 不是 heartbeat manager
- 不是 retry orchestrator
- 不是 business arbiter
- 不是 unified runtime platform SDK

### 5.5 让 README 对陌生接手人可读

一个从未参与前序讨论的人，读完 README 后，至少应能回答：

- 这个 SDK 负责什么
- 它不负责什么
- 怎么做最小接入
- 遇到 409 / 422 / 404 / 5xx 时大致怎么判断
- 接下来该去看哪份文档

---

## 6. 推荐 section 顺序

建议 README 最小结构按以下顺序组织：

1. Package summary
2. What this package is
3. What this package is not
4. Public surface
5. Installation / dependency note
6. Quick start
7. Error handling
8. Boundary / non-goals
9. Related docs
10. Handoff note

如果篇幅必须更短，至少保留：

1. Summary
2. Not a unified runtime SDK
3. Public surface
4. Quick start
5. Error handling summary
6. Related docs

---

## 7. 可直接复用的 README Markdown 模板

以下模板可直接复制使用。

```md
# {package_name}

> A minimal SDK for runtime terminal v1 terminal writes and snapshot reads.

## What this package is

`{package_name}` is a minimal SDK for runtime terminal v1. It is designed for terminal writes and job snapshot reads only.

This package focuses on a narrow, stable integration surface:

- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`

It is intended for worker reporters, lightweight adapters, and caller-side integrations that need a stable runtime terminal client.

## What this package is not

This package is **not**:

- a unified runtime platform SDK
- a claim client
- a heartbeat manager
- a retry orchestration framework
- a business-state arbiter
- a scheduler entrypoint

## Fixed boundary reminders

Before integrating this package, keep the following rules in mind:

- terminal = terminal write + snapshot read
- the SDK does not make business decisions for the caller
- the SDK does not auto-retry 409 conflicts
- the SDK does not auto-repair payloads
- the SDK does not auto-replace `claim_token`
- `job_id / attempt_id / worker_id / claim_token` must come from the same real attempt
- `completion_status` is not the same as `job_status`
- after `complete` / `fail`, snapshot verification is recommended

## Public surface

The minimal public surface is expected to stay centered on:

- `RuntimeTerminalClient`
- `RuntimeAttemptContext`
- minimal exception tree

Typical package layout:

```text
{package_name}/
├── client.py
├── models.py
├── errors.py
└── __init__.py
```

## Installation / dependency note

Use this package as a minimal caller-side integration SDK. Keep dependencies small and avoid turning it into a platform framework.

If this package is shipped as part of a repo handoff, keep the README aligned with the frozen runtime terminal v1 boundary.

## Quick start

Recommended default flow:

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

```python
from {package_import} import (
    RuntimeAttemptContext,
    RuntimeTerminalClient,
    RuntimeTerminalConflictError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)

client = RuntimeTerminalClient(
    base_url="{base_url}",
    api_key="{api_key}",
)

ctx = RuntimeAttemptContext(
    job_id="{job_id}",
    attempt_id="{attempt_id}",
    worker_id="{worker_id}",
    claim_token="{claim_token}",
)

try:
    result = client.complete_job(
        context=ctx,
        completion_status="SUCCEEDED",
        result_ref="{result_ref}",
        manifest_artifact_id=None,
        runtime_ms=31000,
        provider_runtime_ms=27000,
        upload_ms=1800,
        metadata_json={"provider": "{provider_name}"},
    )

    snapshot = client.get_job_snapshot(job_id=ctx.job_id)
    print(result)
    print(snapshot)

except RuntimeTerminalConflictError:
    # Usually a state / context conflict, not a default auto-retry case.
    raise
except RuntimeTerminalValidationError:
    # Usually a caller / payload construction issue.
    raise
except RuntimeTerminalNotFoundError:
    # Usually wrong object id or missing resource.
    raise
except RuntimeTerminalServerError:
    # Server-side or infrastructure-side failure; limited retry may be considered.
    raise
except RuntimeTerminalTransportError:
    # Transport-level failure; handle separately from HTTP semantic errors.
    raise
```

If your flow ends in failure instead of success, use `fail_job(...)` with the same attempt identity context rather than reconstructing the four identity fields from multiple sources.

## Error handling

Recommended mental model:

| Status / category | Preferred interpretation | Default suggestion |
|---|---|---|
| 409 | state / lease / attempt-context conflict | do not auto-retry by default |
| 422 | caller or payload construction issue | fix request construction first |
| 404 | object missing or wrong identifier | verify identifiers and resource existence |
| 5xx | server or infrastructure issue | limited retry may be acceptable |
| transport error | network / transport failure | handle separately from HTTP semantic conflicts |

If you need the detailed exception mapping policy, see the exception contract note and language-specific mapping appendix.

## Boundary / non-goals

This package does not:

- redefine terminal API contracts
- guess `attempt_id`
- replace `claim_token`
- auto-repair payload fields
- hide FastAPI / Pydantic 422 validation detail semantics
- add claim / heartbeat / retry orchestration capabilities
- arbitrate business meaning on behalf of the caller

## Related docs

Suggested reading order:

1. `runtime_terminal_sdk_docs_index_v1.md`
2. `runtime_terminal_sdk_readme_handoff_note_v1.md`
3. `runtime_terminal_sdk_usage_snippet_pack_v1.md`
4. `runtime_terminal_sdk_exception_contract_note_v1.md`
5. `runtime_terminal_sdk_packaging_note_v1.md`
6. `runtime_terminal_sdk_review_matrix_v1.md`
7. `runtime_terminal_sdk_review_record_template_v1.md`

## Handoff note

This package is intentionally kept minimal for runtime terminal v1.

When handing it off:

- do not reopen claim / heartbeat / retry orchestration scope in README
- do not market it as a unified runtime platform SDK
- do not blur 409 / 422 / 404 / 5xx responsibilities
- do keep snapshot verification as the recommended post-write practice
```

---

## 8. 极简 README 模板

如果只允许保留极少文字，可压缩成以下版本：

```md
# {package_name}

A minimal SDK for runtime terminal v1 terminal writes and snapshot reads.

## Scope

This package only covers:

- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`

It is not a unified runtime platform SDK.
It does not provide claim, heartbeat, or retry orchestration.
It does not auto-retry 409, auto-repair payloads, or auto-replace `claim_token`.

## Quick start

Recommended flow:

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

## Key reminder

`job_id / attempt_id / worker_id / claim_token` must come from the same real attempt.

## Errors

- 409: conflict, not default retry
- 422: request construction issue
- 404: missing object / wrong identifier
- 5xx: server / infrastructure issue

## Related docs

See:
- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
```

---

## 9. 推荐写法示例

### 9.1 首页一句话简介

> A minimal SDK for runtime terminal v1 terminal writes and snapshot reads.

### 9.2 中文版定位说明

> 这是 runtime terminal v1 的最小 SDK，用于封装 terminal complete、terminal fail 与 job snapshot read。它强调最小、稳定、可复用、可交接；不扩展为 claim、heartbeat、retry orchestration 或统一 runtime 平台框架。

### 9.3 首页警示语示例

> This package is intentionally narrow. It does not make business decisions for callers and does not auto-retry 409 conflicts.

### 9.4 Quick start 前提示语示例

> Use one real attempt context for all terminal writes. After a successful write, verify the resulting job state with a snapshot read when the workflow is important.

### 9.5 Error handling 小节提示语示例

> Treat 409 as a context or state conflict first, 422 as a request construction issue first, and 5xx / transport failures as the more likely retry candidates.

---

## 10. README 最小完成标准

一份可交接的 runtime terminal v1 SDK README，建议至少满足以下条件：

1. 明确写出这是 runtime terminal v1 最小 SDK
2. 明确写出 terminal = terminal write + snapshot read
3. 明确写出不是 unified runtime platform SDK
4. 明确列出最小 public surface：`complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`
5. 明确提醒四元身份字段必须来自同一次真实 attempt
6. 明确说明 409 不默认自动重试
7. 明确说明 422 保持 caller / payload 构造错误语义
8. Quick start 至少体现一次 snapshot verification 建议
9. 明确列出非目标：claim / heartbeat / retry orchestration / business arbitration
10. 至少挂出 docs index、exception note、packaging note 作为后续阅读入口

如果上述 10 条不能同时满足，README 通常仍不够稳定，不建议作为最终 handoff landing page。

---

## 11. 明确不做什么

本文档不做以下事情：

- 不重新设计 README 文风规范体系
- 不规定多语言 README 的排版细则
- 不引入新的异常层级或新的 public surface
- 不把 README 扩展成完整架构白皮书
- 不替代 `runtime_terminal_sdk_readme_handoff_note_v1.md`
- 不替代 `runtime_terminal_sdk_review_matrix_v1.md` 或 review record
- 不把 v1 最小 SDK 推进成平台级产品说明书

---

## 12. 后续最自然增量方向

在本模板之后，最自然的下一步通常只有两类：

1. 基于真实最小 SDK 包填写一份 **README 实例稿**
2. 补一份 **runtime_terminal_sdk_handoff_bundle_checklist_v1.md**，把 README、docs index、exception note、packaging note、review record 的交付组合固定下来

若只选择一个更自然的下一步，优先建议：

- **基于真实 SDK 包填写一份 README 实例稿**
