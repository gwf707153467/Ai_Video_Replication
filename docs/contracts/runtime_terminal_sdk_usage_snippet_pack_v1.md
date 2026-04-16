# Runtime terminal SDK usage snippet pack v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK / adapter 接入样例包**。

它不重新定义 API contract，也不扩写内部实现，而是把调用方最常见的接入动作压缩成可直接复用、可二次封装、可粘贴改造的代码片段，帮助以下角色快速落地：
- Python SDK / adapter 封装者
- worker runtime reporter 开发者
- orchestrator / job executor 接入开发者
- 需要给上层业务提供统一 terminal reporter 的平台开发者

本文档与以下材料配套阅读：
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_orchestration_explainer_v1.md`
- `runtime_terminal_external_docs_index_v1.md`

本文档严格遵守当前 v1 冻结边界：
- 不改变 complete / fail 写侧语义
- facade 写侧不绕过 service 直写 repository
- 不触碰冻结测试 `tests/test_runtime_terminal_workflow.py`
- 422 继续保持 FastAPI / Pydantic 默认行为

---

## 2. 使用前先记住的 5 条规则

### 2.1 terminal 是终态回写接口，不是调度接口

这些 snippet 只覆盖：
- `POST /complete`
- `POST /fail`
- `GET /jobs/{job_id}`

不覆盖：
- claim
- heartbeat
- retry 调度
- worker 抢占
- 历史终态修正

### 2.2 四个身份字段必须来自同一次真实 attempt

无论 complete 还是 fail，最关键的都是同一组上下文：
- `job_id`
- `attempt_id`
- `worker_id`
- `claim_token`

不要在 SDK 内部二次猜测，不要从多个来源重新拼装。

### 2.3 409 不是“网络抖动默认重试”

409 更接近“状态冲突 / lease 冲突 / 已终态 / 上下文失配”。

SDK 应把它视为 **需要上层判定或人工排障的业务冲突**，而不是简单 HTTP retry。

### 2.4 422 保持 FastAPI / Pydantic 默认校验行为

这意味着：
- 请求字段缺失
- 枚举值非法
- 类型不匹配

都会直接返回框架默认 422 结构。SDK 最好把它归类成 **调用方构造错误**。

### 2.5 成功写入后，必要时用 snapshot 再核验

对于重要链路，建议 complete / fail 之后补一次：

```text
GET /api/v1/runtime/terminal/jobs/{job_id}
```

重点看：
- `job_status`
- `finished_at`
- `latest_attempt.attempt_status`
- `latest_attempt.completion_status`
- `latest_attempt.result_ref`
- `active_lease`

---

## 3. 推荐 SDK 结构

一个最小可维护的 Python terminal adapter，建议拆成：

```text
RuntimeTerminalClient
├── complete_job(...)
├── fail_job(...)
├── get_job_snapshot(...)
└── _request(...)
```

再往上可以有：

```text
RuntimeAttemptContext
├── job_id
├── attempt_id
├── worker_id
└── claim_token
```

这样做的好处是：
- 身份字段天然捆绑
- complete / fail 共享上下文
- 降低“从不同缓存拼字段”导致 409 的概率

---

## 4. 最小 Python SDK 骨架

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class RuntimeTerminalError(Exception):
    """Base error for runtime terminal client."""


class RuntimeTerminalNotFound(RuntimeTerminalError):
    pass


class RuntimeTerminalConflict(RuntimeTerminalError):
    pass


class RuntimeTerminalValidationError(RuntimeTerminalError):
    pass


class RuntimeTerminalServerError(RuntimeTerminalError):
    pass


@dataclass(frozen=True)
class RuntimeAttemptContext:
    job_id: str
    attempt_id: str
    worker_id: str
    claim_token: str


class RuntimeTerminalClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            timeout=self.timeout_seconds,
            **kwargs,
        )

        if response.status_code == 404:
            raise RuntimeTerminalNotFound(response.text)
        if response.status_code == 409:
            raise RuntimeTerminalConflict(response.text)
        if response.status_code == 422:
            raise RuntimeTerminalValidationError(response.text)
        if response.status_code >= 500:
            raise RuntimeTerminalServerError(response.text)

        response.raise_for_status()
        return response.json()
```

说明：
- 404：优先理解为 job 不存在，或读取对象不存在
- 409：优先理解为上下文冲突，不要默认自动重试
- 422：优先理解为 SDK / caller 构造请求不合法
- 5xx：才更像基础设施异常，可进入有限重试策略

---

## 5. Python 最小 complete 调用样例

## 5.1 最小 payload 版本

```python
from typing import Any


def complete_job(
    client: RuntimeTerminalClient,
    ctx: RuntimeAttemptContext,
    *,
    result_ref: str,
    manifest_artifact_id: str | None = None,
    runtime_ms: int | None = None,
    provider_runtime_ms: int | None = None,
    upload_ms: int | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "job_id": ctx.job_id,
        "attempt_id": ctx.attempt_id,
        "worker_id": ctx.worker_id,
        "claim_token": ctx.claim_token,
        "completion_status": "SUCCEEDED",
        "result_ref": result_ref,
        "manifest_artifact_id": manifest_artifact_id,
        "runtime_ms": runtime_ms,
        "provider_runtime_ms": provider_runtime_ms,
        "upload_ms": upload_ms,
        "metadata_json": metadata_json or {},
    }
    return client._request("POST", "/api/v1/runtime/terminal/complete", json=payload)
```

适用场景：
- 本次 attempt 已经真实成功
- 成功结果引用已经稳定
- 不再需要继续维持运行态

### 5.2 更接近生产的调用示例

```python
ctx = RuntimeAttemptContext(
    job_id="job-123",
    attempt_id="attempt-7",
    worker_id="worker-video-a",
    claim_token="claim-9f3d",
)

response = complete_job(
    client=terminal_client,
    ctx=ctx,
    result_ref="minio://video-results/job-123/final.mp4",
    manifest_artifact_id="manifest-123",
    runtime_ms=31_000,
    provider_runtime_ms=27_000,
    upload_ms=1_800,
    metadata_json={
        "provider": "veo",
        "pipeline": "beauty_replication_v1",
        "creative_id": "creative-88",
    },
)

print(response)
```

### 5.3 complete 后的调用方动作建议

推荐顺序：
1. 记录 200 返回结果
2. 如链路关键，立刻读取 snapshot 做二次核验
3. 清理本地 attempt 运行上下文
4. 不再对同一 attempt 重复提交 complete / fail

---

## 6. Python 最小 fail 调用样例

## 6.1 标准失败收口样例

```python
from typing import Any


def fail_job(
    client: RuntimeTerminalClient,
    ctx: RuntimeAttemptContext,
    *,
    next_job_status: str,
    attempt_terminal_status: str,
    terminal_reason: str,
    error_code: str,
    error_message: str,
    error_payload_json: dict[str, Any] | None = None,
    expire_lease: bool = False,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "job_id": ctx.job_id,
        "attempt_id": ctx.attempt_id,
        "worker_id": ctx.worker_id,
        "claim_token": ctx.claim_token,
        "next_job_status": next_job_status,
        "attempt_terminal_status": attempt_terminal_status,
        "terminal_reason": terminal_reason,
        "error_code": error_code,
        "error_message": error_message,
        "expire_lease": expire_lease,
        "metadata_json": metadata_json or {},
    }

    if error_payload_json is not None:
        payload["error_payload_json"] = error_payload_json

    return client._request("POST", "/api/v1/runtime/terminal/fail", json=payload)
```

注意：
- `next_job_status` 仅允许：`FAILED` / `WAITING_RETRY` / `STALE`
- `attempt_terminal_status` 仅允许：`FAILED` / `TIMED_OUT` / `STALE`
- `error_payload_json` 不要显式传 `null`；没有就不传该字段

## 6.2 可重试失败样例

```python
response = fail_job(
    client=terminal_client,
    ctx=ctx,
    next_job_status="WAITING_RETRY",
    attempt_terminal_status="TIMED_OUT",
    terminal_reason="provider_timeout",
    error_code="VEO_TIMEOUT",
    error_message="Provider did not finish within timeout budget.",
    error_payload_json={
        "provider": "veo",
        "timeout_seconds": 900,
        "phase": "render",
    },
    expire_lease=True,
    metadata_json={
        "retry_planned": True,
        "reporter": "worker-runtime-reporter",
    },
)
```

适用场景：
- 本次 attempt 已超时
- job 允许进入等待重试
- 需要尽快使 lease 过期，允许后续接管

## 6.3 不再继续的失败样例

```python
response = fail_job(
    client=terminal_client,
    ctx=ctx,
    next_job_status="FAILED",
    attempt_terminal_status="FAILED",
    terminal_reason="provider_rejected_request",
    error_code="BAD_PROVIDER_INPUT",
    error_message="Provider rejected the request because the prompt payload is invalid.",
    error_payload_json={
        "provider": "veo",
        "http_status": 400,
        "provider_error_code": "INVALID_PROMPT",
    },
    expire_lease=False,
    metadata_json={
        "requires_manual_fix": True,
    },
)
```

适用场景：
- 本次错误已明确不是瞬时问题
- 任务不应无脑重试
- 需要人工或上游修正输入后再重开新任务

---

## 7. snapshot 查询样例

## 7.1 最小读取接口

```python
def get_job_snapshot(client: RuntimeTerminalClient, job_id: str) -> dict[str, Any]:
    return client._request("GET", f"/api/v1/runtime/terminal/jobs/{job_id}")
```

## 7.2 读取后做三层核验

```python
snapshot = get_job_snapshot(terminal_client, "job-123")

job_status = snapshot.get("job_status")
latest_attempt = snapshot.get("latest_attempt") or {}
active_lease = snapshot.get("active_lease")

print("job_status=", job_status)
print("attempt_status=", latest_attempt.get("attempt_status"))
print("completion_status=", latest_attempt.get("completion_status"))
print("result_ref=", latest_attempt.get("result_ref"))
print("active_lease=", active_lease)
```

推荐核验顺序：

### job 层
看：
- `job_status`
- `finished_at`

回答的问题：
- job 是否已成功或失败收口
- 是否仍停留在非预期状态

### latest attempt 层
看：
- `attempt_status`
- `completion_status`
- `terminal_reason`
- `error_code`
- `result_ref`
- `manifest_artifact_id`

回答的问题：
- 当前最新 attempt 到底是成功、失败、超时还是 stale
- 成功产物或失败原因是否符合预期

### active lease 层
看：
- `active_lease` 是否存在
- 若存在，其 worker / token 是否仍符合预期

回答的问题：
- lease 是否已正常释放或过期
- 是否存在冲突上下文仍占有执行权

---

## 8. 409 / 422 caller 侧处理骨架

## 8.1 推荐异常分类

```python
def report_complete_with_handling(
    client: RuntimeTerminalClient,
    ctx: RuntimeAttemptContext,
    *,
    result_ref: str,
) -> dict[str, Any] | None:
    try:
        return complete_job(client, ctx, result_ref=result_ref)
    except RuntimeTerminalConflict as exc:
        # 409: 优先按状态冲突处理，不做无脑自动重试
        log_conflict(ctx, exc)
        escalate_or_read_snapshot(client, ctx.job_id)
        return None
    except RuntimeTerminalValidationError as exc:
        # 422: 优先按调用方 payload 构造错误处理
        log_bad_payload(ctx, exc)
        raise
    except RuntimeTerminalServerError as exc:
        # 5xx: 可进入有限重试
        log_server_error(ctx, exc)
        raise
```

## 8.2 推荐决策原则

### 遇到 409
做：
- 记录 `job_id / attempt_id / worker_id / claim_token`
- 读取 snapshot
- 判断是 lease conflict、attempt 不匹配、job 已终态，还是重复提交
- 必要时转 operator / 人工排障

不要做：
- 原样 payload 死循环重试
- 擅自替换 claim_token 再重提
- 盲目把 complete 改成 fail，或把 fail 改成 complete

### 遇到 422
做：
- 直接把它归类成 SDK / caller 构造错误
- 修 payload、字段类型、枚举值、必填项
- 尤其检查 `next_job_status` / `attempt_terminal_status` / `error_payload_json`

不要做：
- 期望平台自动兜底改写
- 把 422 当成 provider 瞬时错误

---

## 9. 身份字段透传模板

如果上层有 worker 执行上下文对象，建议固定成类似结构：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerExecutionContext:
    job_id: str
    attempt_id: str
    worker_id: str
    claim_token: str
    run_id: str | None = None
    provider_task_id: str | None = None
```

对 terminal SDK 的边界要求是：
- SDK 只消费这 4 个核心身份字段
- 不从数据库、缓存、环境变量补猜
- 不自行替换 `attempt_id` 或 `claim_token`

转换模板：

```python
def to_terminal_attempt_context(exec_ctx: WorkerExecutionContext) -> RuntimeAttemptContext:
    return RuntimeAttemptContext(
        job_id=exec_ctx.job_id,
        attempt_id=exec_ctx.attempt_id,
        worker_id=exec_ctx.worker_id,
        claim_token=exec_ctx.claim_token,
    )
```

这能显著降低以下错误：
- 用旧 attempt 回写新任务
- 用错误 worker_id 回写他人 lease
- 从多个缓存源拼出了不一致字段

---

## 10. 常见封装误区

### 10.1 在 SDK 内默认自动重试 409
不推荐。

原因：409 通常代表语义冲突，而不是网络抖动。

### 10.2 把 `completion_status` 当成 job 最终状态
不推荐。

原因：`completion_status` 是 attempt 成功完成时的补充标签，不等于 job 聚合状态。

### 10.3 显式传 `error_payload_json: null`
不推荐。

原因：当前 caller 文档已明确，没有 payload 时应直接省略该字段。

### 10.4 在 complete 成功后继续补提 fail
不推荐。

原因：同一 attempt 已经收口，再补提另一终态大概率会进入冲突语义。

### 10.5 在 fail 时临时决定替换 claim_token
不推荐。

原因：claim_token 是并发归属校验字段，不应该由 SDK 在上报瞬间“修正”。

---

## 11. 推荐给接入方的最小落地包

如果你要把本文档交给 SDK / adapter 开发者，最小建议同时附上：
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_orchestration_explainer_v1.md`

推荐阅读顺序：
1. 本文档：先复制样例，快速接入
2. caller integration guide：补齐 complete/fail/snapshot 的行为边界
3. orchestration explainer：补齐 404 / 409 / 422 / snapshot 字段语义

---

## 12. 本包完成度判断

当前 `runtime terminal SDK usage snippet pack v1` 已覆盖 caller / SDK 接入最常见的最小落地需求：
- Python 最小 terminal client 骨架
- complete 调用样例
- fail 调用样例
- snapshot 查询样例
- 409 / 422 caller 侧处理骨架
- 身份字段透传模板
- 常见 SDK 封装误区

因此它已经达到：
- **可直接交给 SDK / adapter 开发者使用**
- **可直接作为 worker runtime reporter 接入模板使用**
- **可作为 caller integration guide 的代码补充包使用**

后续如果还要扩一小步，最自然增量有两个：
- `runtime terminal FAQ / decision memo v1`
- `runtime terminal language-specific snippets pack v1`（例如 requests / httpx / TypeScript）
