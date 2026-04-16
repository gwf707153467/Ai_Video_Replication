# Runtime terminal minimal SDK scaffold note v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **minimal SDK scaffold note**。

它面向以下角色：
- Python SDK / adapter 封装者
- worker runtime reporter 开发者
- 需要把 terminal 调用收敛成统一 client 的平台开发者
- 后续准备从 snippet 过渡到可维护 SDK 骨架的维护者

它不重新定义 API contract，不替代 caller integration guide、caller FAQ、SDK usage snippet pack、language-specific error mapping appendix，也不引入新的写侧语义。

它的目标更窄：
- 说明一个 **最小但可维护** 的 terminal SDK 骨架应该长什么样
- 明确哪些能力应进入 v1 scaffold，哪些不应提前做重封装
- 帮调用方从“能调通”过渡到“能长期维护”

建议配套阅读：
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_language_specific_error_mapping_appendix_v1.md`
- `runtime_terminal_caller_faq_v1.md`

本文档严格遵守当前 v1 冻结边界：
- terminal = terminal write + snapshot read，不是调度入口
- 不重定义 API contract
- 不改变 complete / fail 写侧语义
- facade 写侧不绕过 service 直写 repository
- 不触碰 `tests/test_runtime_terminal_workflow.py`
- 422 保持 FastAPI / Pydantic 默认行为

---

## 2. 这份 scaffold note 要解决什么问题

已有 snippet pack 已经回答了“怎么发请求”。

但当调用方准备沉淀 SDK 时，常见问题会变成：
- client 最小应该有哪些 public method
- attempt 上下文应该怎么收束
- 异常类型要不要分层
- 哪些事情应该由 SDK 做，哪些必须留给 caller
- 如何在不放大封装范围的情况下保留可扩展性

因此，这份 note 不再给一组“可粘贴的 endpoint 示例”为主，而是给出一份 **建议长期保留的最小骨架轮廓**。

---

## 3. v1 最小 SDK 的职责边界

### 3.1 应该做的事

v1 最小 SDK 建议只做以下 5 件事：

1. 提供统一 HTTP 调用入口。
2. 暴露 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)` 三个最小能力。
3. 用一个显式 attempt context 承载四元身份字段。
4. 对 `404 / 409 / 422 / 5xx` 做最小异常分层。
5. 允许 caller 在成功后自行决定是否补 snapshot 核验。

### 3.2 不应该做的事

v1 最小 SDK 不建议内建以下能力：
- claim / heartbeat / retry 调度
- 自动补猜 `attempt_id` 或 `claim_token`
- 自动把 `complete` 改写成 `fail`
- 自动重试 409
- 吞掉 422 细节后改造成模糊错误
- 帮 caller 猜测 `expire_lease`
- 帮 caller 推导 `next_job_status` 或 `attempt_terminal_status`
- 在 SDK 内部缓存并复写旧 attempt 上下文

一句话说，**v1 SDK 负责稳定透传与清晰分类，不负责替业务做判断**。

---

## 4. 推荐骨架总览

建议最小结构如下：

```text
runtime_terminal_sdk/
├── __init__.py
├── client.py
├── models.py
└── errors.py
```

推荐最小对象关系如下：

```text
RuntimeAttemptContext
├── job_id
├── attempt_id
├── worker_id
└── claim_token

RuntimeTerminalClient
├── complete_job(...)
├── fail_job(...)
├── get_job_snapshot(...)
└── _request(...)

RuntimeTerminalError
├── RuntimeTerminalNotFoundError
├── RuntimeTerminalConflictError
├── RuntimeTerminalValidationError
├── RuntimeTerminalServerError
└── RuntimeTerminalTransportError   # 可选
```

这个拆法的价值在于：
- `models.py` 收住调用上下文和少量共享结构
- `errors.py` 固定异常分层口径
- `client.py` 把 endpoint 调用集中到一个地方
- 后续若扩 header、auth、trace_id、日志注入，不需要改业务层接口形态

---

## 5. 推荐 public surface

### 5.1 `RuntimeAttemptContext`

建议把四元身份字段绑成一个不可变对象，由上游在拿到真实 attempt 上下文时一次性构造。

示意：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeAttemptContext:
    job_id: str
    attempt_id: str
    worker_id: str
    claim_token: str
```

建议：
- 使用不可变对象，降低调用过程被改写的概率。
- 不要让 SDK 在内部再去补这些字段。
- complete / fail 共用同一份 context。

### 5.2 `RuntimeTerminalClient`

建议 public method 固定为：
- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`

建议 private helper 至少保留：
- `_request(...)`

这意味着 v1 不需要一开始就暴露大量 endpoint wrapper，也不需要做泛型资源客户端。

---

## 6. 推荐异常分层

### 6.1 最小异常树

建议至少保留下面 5 层概念：

```python
class RuntimeTerminalError(Exception):
    pass


class RuntimeTerminalNotFoundError(RuntimeTerminalError):
    pass


class RuntimeTerminalConflictError(RuntimeTerminalError):
    pass


class RuntimeTerminalValidationError(RuntimeTerminalError):
    pass


class RuntimeTerminalServerError(RuntimeTerminalError):
    pass


class RuntimeTerminalTransportError(RuntimeTerminalError):
    pass
```

### 6.2 对应口径

- `RuntimeTerminalNotFoundError`：优先对应 404。
- `RuntimeTerminalConflictError`：优先对应 409。
- `RuntimeTerminalValidationError`：优先对应 422。
- `RuntimeTerminalServerError`：优先对应 5xx。
- `RuntimeTerminalTransportError`：网络超时、连接失败、DNS、TLS 等 HTTP 未成型异常；该层可选，但建议预留。

### 6.3 为什么不要只保留一个大而全异常

如果全部都抛一个 `RuntimeTerminalError`，上层会很快失去最小分支能力：
- 404 是对象不存在/标识错误
- 409 是状态或上下文冲突
- 422 是 payload 构造错误
- 5xx 才更接近基础设施异常

这些分支的处置方式完全不同，因此 v1 scaffold 就应该把它们分开。

---

## 7. 推荐 request 层骨架

### 7.1 `_request(...)` 应承担的职责

建议 `_request(...)` 只做：
- 统一拼接 base URL 与 path
- 统一 timeout
- 发起 HTTP 请求
- 把状态码映射到最小异常层
- 成功时返回 JSON body

不建议 `_request(...)` 做：
- 自动重试业务冲突
- 重写 caller payload
- 自动读取 snapshot 再二次决策
- 把 422 响应裁剪成看不出字段错误的模糊异常

### 7.2 一个最小可维护示意

```python
from __future__ import annotations

from typing import Any

import requests


class RuntimeTerminalClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise RuntimeTerminalTransportError(str(exc)) from exc

        if response.status_code == 404:
            raise RuntimeTerminalNotFoundError(response.text)
        if response.status_code == 409:
            raise RuntimeTerminalConflictError(response.text)
        if response.status_code == 422:
            raise RuntimeTerminalValidationError(response.text)
        if response.status_code >= 500:
            raise RuntimeTerminalServerError(response.text)

        response.raise_for_status()
        return response.json()
```

说明：
- 404 / 409 / 422 / 5xx 先按固定类分流。
- `response.text` 是否进一步结构化，可留给 v1.1 以后。
- 200 后直接 `response.json()` 即可，不必过早引入复杂 response model。

---

## 8. 推荐 terminal method 形态

### 8.1 `complete_job(...)`

建议输入形态：
- `ctx: RuntimeAttemptContext`
- 业务必须提供的成功字段，如 `result_ref`
- 少量可选字段，如 `manifest_artifact_id`、时间统计、`metadata_json`

示意原则：
- 四元身份字段从 `ctx` 原样透传。
- `completion_status` 由 caller 显式看见且保持固定成功语义。
- 不替 caller 猜 `manifest_artifact_id`。

### 8.2 `fail_job(...)`

建议输入形态：
- `ctx: RuntimeAttemptContext`
- caller 显式提供 `next_job_status`
- caller 显式提供 `attempt_terminal_status`
- caller 显式提供 `terminal_reason / error_code / error_message`
- `expire_lease` 必须由 caller 按真实语义决定

示意原则：
- 不要在 SDK 内部推导“这次失败应该进入 WAITING_RETRY 还是 FAILED”。
- 不要自动传 `error_payload_json = null`。
- caller 不提供该字段时，就省略该字段。

### 8.3 `get_job_snapshot(...)`

建议只接受：
- `job_id`

用途固定为：
- complete / fail 后核验
- 409 后判定上下文是否已失效
- caller 排障

它不应被包装成“自动纠错器”，也不应在 SDK 内默默串联到每次 complete / fail 之后。

---

## 9. 一个建议保留的最小代码轮廓

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class RuntimeTerminalError(Exception):
    pass


class RuntimeTerminalNotFoundError(RuntimeTerminalError):
    pass


class RuntimeTerminalConflictError(RuntimeTerminalError):
    pass


class RuntimeTerminalValidationError(RuntimeTerminalError):
    pass


class RuntimeTerminalServerError(RuntimeTerminalError):
    pass


class RuntimeTerminalTransportError(RuntimeTerminalError):
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
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise RuntimeTerminalTransportError(str(exc)) from exc

        if response.status_code == 404:
            raise RuntimeTerminalNotFoundError(response.text)
        if response.status_code == 409:
            raise RuntimeTerminalConflictError(response.text)
        if response.status_code == 422:
            raise RuntimeTerminalValidationError(response.text)
        if response.status_code >= 500:
            raise RuntimeTerminalServerError(response.text)

        response.raise_for_status()
        return response.json()

    def complete_job(
        self,
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
        return self._request("POST", "/api/v1/runtime/terminal/complete", json=payload)

    def fail_job(
        self,
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
        return self._request("POST", "/api/v1/runtime/terminal/fail", json=payload)

    def get_job_snapshot(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/runtime/terminal/jobs/{job_id}")
```

说明：
- 这个轮廓已经足够支撑 caller / worker / orchestrator 的最小接入。
- 它刻意不引入 response DTO、middleware 栈、重试插件、trace adapter 等扩展层。
- 只有在多调用方、跨项目复用、统一日志/认证已明确稳定时，才建议继续外扩。

---

## 10. caller 与 SDK 的责任切分

### 10.1 caller 负责

caller 应继续负责：
- 提供真实的四元身份字段
- 选择 complete 还是 fail
- 决定 `next_job_status`
- 决定 `attempt_terminal_status`
- 决定 `expire_lease`
- 决定 200 后是否补 snapshot 核验
- 决定 409 后是否人工介入、是否发起新动作

### 10.2 SDK 负责

SDK 只负责：
- 提供稳定调用面
- 保持参数原样表达
- 做最小错误分类
- 降低重复样板代码

### 10.3 这样切分的原因

因为 runtime terminal 的争议点，从来不是“HTTP 怎么发”，而是“业务语义该由谁决定”。

v1 的答案已经固定：
- 业务语义由 caller 决定
- SDK 不替 caller 猜测

---

## 11. scaffold 实现时的 7 条硬约束

1. `RuntimeAttemptContext` 必须来自同一次真实 attempt。
2. `complete_job(...)` 只用于真实成功收口。
3. `fail_job(...)` 不得在 SDK 内自动推导失败语义。
4. 409 不做默认自动重试。
5. 422 直接保留为调用方构造错误。
6. 成功后 snapshot 核验能力可以提供，但不强制隐式触发。
7. terminal SDK 不扩张成 claim / heartbeat / scheduler client。

---

## 12. 最小目录建议

如果调用方准备单独沉淀一个轻量 Python 包，建议先到这里为止：

```text
runtime_terminal_sdk/
├── __init__.py
├── client.py
├── errors.py
└── models.py
```

`__init__.py` 建议仅导出：
- `RuntimeAttemptContext`
- `RuntimeTerminalClient`
- `RuntimeTerminalError`
- `RuntimeTerminalNotFoundError`
- `RuntimeTerminalConflictError`
- `RuntimeTerminalValidationError`
- `RuntimeTerminalServerError`
- `RuntimeTerminalTransportError`

不建议 v1 一开始就加：
- async client 与 sync client 双栈
- 自动重试配置系统
- 复杂 serializer / deserializer
- 抽象基类与插件注册机制
- 大量 response dataclass

这些都容易把“最小可维护骨架”重新做成“过度设计骨架”。

---

## 13. 与已有文档的分工

### 13.1 和 snippet pack 的区别

- snippet pack 重点是“怎么调用”。
- scaffold note 重点是“SDK 应该怎么组织”。

### 13.2 和 caller FAQ 的区别

- caller FAQ 重点是“caller 应怎么理解语义和处理常见问题”。
- scaffold note 重点是“当你开始沉淀 SDK 时，哪些边界必须保留”。

### 13.3 和 error mapping appendix 的区别

- error mapping appendix 重点是“状态码在不同语言里怎么映射和处理”。
- scaffold note 重点是“最小异常树和 client 骨架该如何放置在一个 SDK 里”。

---

## 14. 一页式落地建议

如果现在就要落一个 runtime terminal 最小 SDK，建议按这个顺序：

1. 先建 `RuntimeAttemptContext`。
2. 再建 `RuntimeTerminalError` 及 404 / 409 / 422 / 5xx 对应子类。
3. 实现一个只做最小映射的 `_request(...)`。
4. 暴露 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`。
5. 保持 409 / 422 分支对 caller 可见。
6. 不做隐式 snapshot、隐式重试、隐式字段补猜。
7. 只有当多项目复用需求明确后，再继续扩 response model、日志钩子、认证注入、async 版本。

---

## 15. 一句话结论

runtime terminal v1 的最小 SDK 骨架，不追求“替 caller 更聪明”，而追求 **把 attempt 上下文、terminal 调用和错误分类稳定地收束到一个足够小、足够清晰、足够不越权的 client 中**。
