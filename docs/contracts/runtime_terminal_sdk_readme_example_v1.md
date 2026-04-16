# Runtime terminal SDK README example v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK README 实例稿**。

它不是新的设计文档，不新增 API contract，不重开 complete / fail / snapshot 语义，也不扩展 v1 freeze 边界。它的作用更窄：

> 基于已经冻结的 README minimal template、README handoff note、packaging note、exception note 等材料，给出一份 **可直接复制、轻改、落地交接** 的 README 实例稿。

如果说：
- `runtime_terminal_sdk_readme_minimal_template_v1.md` 解决的是“README 最少应该怎么写”；
- 那么本文档解决的是“**一份真实 README 样稿可以长什么样**”。

本文档默认沿用以下既有材料，不重复改写：
- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_readme_handoff_note_v1.md`
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_sdk_review_matrix_v1.md`
- `runtime_terminal_sdk_review_record_template_v1.md`
- `runtime_terminal_sdk_readme_minimal_template_v1.md`

---

## 2. 使用前默认前提

本实例稿默认以下边界已经冻结，README 只负责表达，不负责重新讨论：

- terminal = terminal write + snapshot read
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
- `complete` / `fail` 成功后建议做 snapshot 核验
- 422 保持 FastAPI / Pydantic 默认行为
- facade 写侧不绕过 service 直写 repository

如果接手方想在 README 里重新打开上述议题，建议升级为独立设计问题，而不是继续扩写 README。

---

## 3. 本实例稿采用的假定包形态

为了让 README 样稿可以直接落地，本文假定最小 SDK 包名采用：

- package name：`runtime_terminal_sdk`
- import root：`runtime_terminal_sdk`

假定最小目录结构为：

```text
runtime_terminal_sdk/
├── client.py
├── models.py
├── errors.py
└── __init__.py
```

假定对外 public surface 为：
- `RuntimeTerminalClient`
- `RuntimeAttemptContext`
- `RuntimeTerminalError`
- `RuntimeTerminalNotFoundError`
- `RuntimeTerminalConflictError`
- `RuntimeTerminalValidationError`
- `RuntimeTerminalServerError`
- `RuntimeTerminalTransportError`

如果后续真实包名不同，建议只替换包名、安装方式、仓内路径与认证说明，不改动边界口径。

---

## 4. 可直接复用的 README 实例稿

下面给出一份按当前 v1 freeze 直接填写后的 README 正文示例。若真实 SDK 包已落地，可将本节作为 `README.md` 初稿直接复制后轻改。

# runtime_terminal_sdk

> A minimal SDK for runtime terminal v1 terminal writes and snapshot reads.

## Package summary

`runtime_terminal_sdk` is a minimal caller-side SDK for runtime terminal v1.
It is intentionally small and stable, and it only covers terminal writes and job snapshot reads.

This package exists to make the following integration path predictable and reusable:

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

## What this package is

`runtime_terminal_sdk` is a minimal client package for runtime terminal v1.

Its public surface is intentionally centered on three actions only:

- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`

This package is suitable for:
- worker reporters
- lightweight adapters
- caller-side runtime terminal integrations
- small internal SDK handoff scenarios

The package aims to be:
- minimal
- stable
- reusable
- handoff-friendly

## What this package is not

This package is **not**:

- a unified runtime platform SDK
- a claim client
- a heartbeat manager
- a retry orchestration framework
- a business-state arbiter
- a scheduler entrypoint

If your integration needs claim, heartbeat, retry scheduling, or business-state arbitration, those responsibilities should remain outside this package.

## Public surface

The minimal public surface stays centered on:

- `RuntimeTerminalClient`
- `RuntimeAttemptContext`
- minimal exception tree

Typical package layout:

```text
runtime_terminal_sdk/
├── client.py
├── models.py
├── errors.py
└── __init__.py
```

Recommended imports:

```python
from runtime_terminal_sdk import (
    RuntimeAttemptContext,
    RuntimeTerminalClient,
    RuntimeTerminalConflictError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)
```

`RuntimeAttemptContext` is used to keep the four identity fields from the same real attempt together:

- `job_id`
- `attempt_id`
- `worker_id`
- `claim_token`

## Installation / dependency note

Use this package as a minimal caller-side integration SDK.
Keep dependencies small and avoid turning it into a platform framework.

Recommended packaging stance for v1:
- small internal package or repo-local package first
- explicit exports only
- no sync / async dual-stack in v1
- no plugin or middleware framework

If this package is shipped through repo handoff instead of a public package registry, keep the README aligned with the frozen runtime terminal v1 boundary rather than expanding feature promises.

## Quick start

Recommended default flow:

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

Important reminder before any write:

> `job_id / attempt_id / worker_id / claim_token` must come from the same real attempt. Do not reconstruct the four identity fields from multiple sources.

Example:

```python
from runtime_terminal_sdk import (
    RuntimeAttemptContext,
    RuntimeTerminalClient,
    RuntimeTerminalConflictError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)

client = RuntimeTerminalClient(
    base_url="https://runtime.example.internal",
    api_key="your-api-key",
)

ctx = RuntimeAttemptContext(
    job_id="job-123",
    attempt_id="attempt-7",
    worker_id="worker-video-a",
    claim_token="claim-9f3d",
)

try:
    result = client.complete_job(
        context=ctx,
        completion_status="SUCCEEDED",
        result_ref="minio://video-results/job-123/final.mp4",
        manifest_artifact_id=None,
        runtime_ms=31000,
        provider_runtime_ms=27000,
        upload_ms=1800,
        metadata_json={
            "provider": "veo",
            "pipeline": "beauty_replication_v1",
        },
    )

    snapshot = client.get_job_snapshot(job_id=ctx.job_id)

    print(result)
    print(snapshot)

except RuntimeTerminalConflictError:
    # Usually a state / lease / attempt-context conflict.
    # Do not auto-retry by default.
    raise
except RuntimeTerminalValidationError:
    # Usually a caller or payload construction issue.
    raise
except RuntimeTerminalNotFoundError:
    # Usually a wrong identifier or missing resource.
    raise
except RuntimeTerminalServerError:
    # Server-side or infrastructure-side failure.
    # Limited retry may be considered by the caller.
    raise
except RuntimeTerminalTransportError:
    # Transport failure should be handled separately from HTTP semantic errors.
    raise
```

If your flow ends in failure instead of success, call `fail_job(...)` with the same `RuntimeAttemptContext` rather than rebuilding the four identity fields from mixed sources.

Minimal failure-side example:

```python
client.fail_job(
    context=ctx,
    failure_reason="provider timeout",
    next_job_status="WAITING_RETRY",
    attempt_terminal_status="TIMED_OUT",
    metadata_json={"provider": "veo"},
)
```

## Error handling

Use the following mental model:

| Status / category | Preferred interpretation | Default suggestion |
|---|---|---|
| 409 | state / lease / attempt-context conflict | do not auto-retry by default |
| 422 | caller or payload construction issue | fix request construction first |
| 404 | object missing or wrong identifier | verify identifiers and resource existence |
| 5xx | server or infrastructure issue | limited retry may be acceptable |
| transport error | network / transport failure | handle separately from HTTP semantic conflicts |

Additional reminders:
- `completion_status` is not the same as `job_status`
- a successful terminal write does not automatically mean the business side has consumed the expected state
- snapshot verification is recommended after `complete` / `fail`, especially on critical paths
- keep HTTP semantic errors and transport failures as separate branches in caller logic

## Boundary / non-goals

Keep the following boundary fixed:

- terminal = terminal write + snapshot read
- the SDK does not make business decisions for the caller
- the SDK does not auto-retry 409 conflicts
- the SDK does not auto-repair payloads
- the SDK does not auto-replace `claim_token`
- the SDK does not infer or synthesize attempt identity fields
- the SDK does not wrap FastAPI / Pydantic 422 into a new business-specific schema

Non-goals in v1:
- claim support
- heartbeat support
- retry orchestration
- scheduler entrypoints
- business arbitration
- large DTO frameworks
- plugin or middleware systems
- dual sync / async client stacks

## Related docs

For deeper details, read the following documents together with this README:

- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_readme_handoff_note_v1.md`

Recommended reading order for a new maintainer:
1. `runtime_terminal_sdk_docs_index_v1.md`
2. `runtime_terminal_sdk_exception_contract_note_v1.md`
3. `runtime_terminal_sdk_packaging_note_v1.md`
4. `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
5. `runtime_terminal_sdk_usage_snippet_pack_v1.md`

## Handoff note

This README assumes the runtime terminal v1 boundary is frozen.

Do not reopen the following questions in this package README:
- whether terminal should become a scheduler entrypoint
- whether claim / heartbeat should be included
- whether 409 should be auto-retried by default
- whether caller payload issues should be silently repaired by the SDK
- whether the SDK should arbitrate business state transitions

If future work is needed, prefer additive documentation or a separate design track rather than silently expanding this README beyond the v1 boundary.

---

## 5. 为什么这份实例稿可以直接用于 handoff

这份实例稿已经覆盖了 README 最小模板要求的关键检查点：

1. 首页先回答“是什么”，不是先堆代码。
2. 首页显式回答“它不是什么”。
3. public surface 只围绕最小导出面。
4. quick start 体现默认闭环：`build context -> write terminal -> handle explicit errors -> verify by snapshot`。
5. 显式提醒四元身份字段必须来自同一次真实 attempt。
6. 显式把 409 / 422 / 404 / 5xx / transport error 分开表达。
7. 显式提醒 `completion_status` 不等于 `job_status`。
8. 显式提醒成功写入后建议 snapshot 核验。
9. 显式列出 non-goals，避免 README 被误解为开放能力列表。
10. 显式挂出 docs index、exception note、packaging note 等后续入口。

因此，它适合作为：
- 仓内最小 SDK 包的 `README.md` 初稿
- handoff bundle 内的 README 样稿
- reviewer 对照 README minimal template 做快速审阅的参考样本

---

## 6. 使用这份实例稿时建议只替换什么

如果后续真实 SDK 包已经存在，建议只替换以下信息：

- 真实 package name / import path
- 真实 base URL、认证字段与初始化参数
- 真实安装方式（如仓内 path、internal wheel、内部源）
- 真实 metadata 字段样例
- 真实 related docs 路径

不建议在替换时改动以下固定表达：

- terminal = terminal write + snapshot read
- 最小 public surface 只围绕 `complete_job(...)` / `fail_job(...)` / `get_job_snapshot(...)`
- 409 不默认自动重试
- 422 保持 caller / payload 构造错误语义
- SDK 不做业务仲裁
- SDK 不自动修补 payload
- SDK 不自动替换 `claim_token`
- 四元身份字段必须来自同一次真实 attempt
- complete / fail 成功后建议 snapshot verification

---

## 7. 明确不做什么

本文档不做以下事情：

- 不替真实 SDK 包补代码实现
- 不替 README 模板重新定义边界
- 不把实例稿扩写成平台级设计文档
- 不新增 claim / heartbeat / retry orchestration 说明
- 不把 README 样稿变成对外宣传页

如果下一步只继续做一个自然增量，建议从本实例稿继续推进为：

- 真实最小 SDK 包对应的正式 `README.md` 落稿 / 对位版

而不是再新增一份更抽象的 README 规则文档。
