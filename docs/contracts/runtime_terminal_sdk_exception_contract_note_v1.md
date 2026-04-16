# Runtime terminal SDK exception contract note v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK exception contract note**。

它面向以下角色：
- Python SDK / adapter 封装者
- worker runtime reporter 维护者
- 需要把 runtime terminal 错误分类收敛成统一 client contract 的平台开发者
- 做 code review、自检、交接验收的维护者

它与以下材料配套使用：
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_language_specific_error_mapping_appendix_v1.md`
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_caller_faq_v1.md`

它不重新定义 API contract，不替代 caller integration guide，不重写 language-specific appendix，也不引入新的 terminal 写侧语义。

它只回答一个更窄的问题：

> 当调用方把 runtime terminal 接口封成最小 SDK 时，异常契约最少应该保留到什么程度，才能既不丢失语义，又不越权替 caller 做业务决策。

本文档严格遵守当前 v1 冻结边界：
- terminal = terminal write + snapshot read，不是调度入口
- 不重定义 `complete / fail / snapshot` 的 API contract
- 不改变 complete / fail 写侧语义
- 422 保持 FastAPI / Pydantic 默认行为
- 409 优先视为状态/上下文冲突，而不是默认网络重试信号
- SDK 只做最小错误分类，不做业务仲裁

---

## 2. 这份文档要解决什么问题

当调用方还停留在 snippet 阶段时，常见做法是：
- 请求失败后统一抛一个 HTTPError
- 或者直接把 `response.status_code` 往外透传

这种做法在“能调通”阶段问题不大，但一旦进入长期维护，马上会遇到几个实际问题：
- 404、409、422、5xx 在 runtime terminal 中语义完全不同，不能混成一个错误
- caller 需要基于最小异常分层决定是否读 snapshot、是否人工介入、是否重试
- 如果 SDK 把 422 压扁成模糊 bad request，会让 schema / payload 问题排查变慢
- 如果 SDK 把 409 当成 transport retry，会在终态链路引入错误重放
- 如果 transport failure 和 HTTP failure 不可区分，调用方无法判断这是网络问题还是 terminal contract 问题

所以，v1 需要冻结的不只是“有哪些 endpoint”，还包括：

> **最小异常契约必须让上层还能做正确分支，但又不能把 SDK 做成过度设计的异常框架。**

---

## 3. 先给固定结论

runtime terminal v1 的 SDK 异常契约，建议固定为以下 8 条：

1. SDK 至少应保留统一基类 + `404 / 409 / 422 / 5xx / transport` 五层概念。
2. `404` 优先表示对象不存在或标识错误，不优先表示状态冲突。
3. `409` 优先表示状态/上下文冲突，不应默认自动重试。
4. `422` 优先表示 caller / SDK payload 构造错误，应尽量保留框架原始校验细节。
5. `5xx` 更接近服务端或基础设施异常，可由 caller 做有限重试。
6. transport error 应与 HTTP 语义错误分离，不能混在同一个“请求失败”异常中。
7. SDK 可以统一映射错误，但不应在异常层偷偷重写 payload、替换 `claim_token`、猜测其他 ID。
8. caller 仍负责决定：409 后如何处理、是否补 snapshot 核验、是否重试 5xx、是否人工介入。

一句话总结：

> **v1 SDK 的异常契约目标不是“聪明恢复”，而是“稳定分类 + 保留上下文 + 不篡改语义”。**

---

## 4. 最小异常树建议

## 4.1 推荐异常层级

建议至少保留以下异常树：

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

说明：
- 名称可以因团队风格略有变化。
- 但 404 / 409 / 422 / 5xx / transport 这五层语义，建议不要合并丢失。
- 如果团队确实不想暴露太多类名，也至少应在统一异常对象上保留等价区分能力。

## 4.2 为什么 v1 就要分层

因为这些错误的默认处置动作天然不同：

| 类型 | 优先语义 | 默认动作 | 不建议做 |
| --- | --- | --- | --- |
| 404 | 对象不存在 / 标识错误 | 校验 ID 与对象存在性 | 当成冲突自动重试 |
| 409 | 状态/上下文冲突 | 读 snapshot，再做业务判定 | 原样 payload blind retry |
| 422 | payload 构造错误 | 修 schema / 字段 / 枚举 | 吞细节后模糊包装 |
| 5xx | 服务端/基础设施异常 | 有上限重试，并结合 snapshot | 无限重试终态写入 |
| transport | 超时/连接/网络异常 | 与 HTTP 语义错误分开处理 | 误判成 409 或 422 |

如果 SDK 只抛一个大而全的 `RuntimeTerminalError`，上层很快就会失去这些最基本的分支能力。

---

## 5. 每类异常应承载的最小信息

v1 不需要做复杂 error DTO 体系，但建议异常对象至少能保留以下最小信息：

- `message`：可读错误摘要
- `status_code`：HTTP 状态码；transport error 可为空
- `method`：请求方法，如 `POST` / `GET`
- `path`：请求 path，而不是模糊“某个请求失败”
- `response_text` 或原始 body 摘要：方便排障
- `cause`：底层异常；transport 场景尤其重要

推荐原则：
- **保留足够排障信息，但不要因为 v1 就引入复杂序列化体系。**
- 如有 `request_id`、trace id、响应 headers，可作为增强项保留，但不应成为 v1 最小依赖。

一个足够克制的写法示意：

```python
class RuntimeTerminalError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        method: str | None = None,
        path: str | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.path = path
        self.response_text = response_text
```

这个层级已经足以支撑：
- 日志定位
- 值班排障
- 409 / 422 / 5xx 的上层分支处理
- 后续扩充 trace 信息，而不破坏 public surface

---

## 6. HTTP 状态码到异常的固定映射

## 6.1 推荐固定映射

建议 `_request(...)` 采用固定映射：

- `200`：正常返回解析后的成功结果
- `404`：抛 `RuntimeTerminalNotFoundError`
- `409`：抛 `RuntimeTerminalConflictError`
- `422`：抛 `RuntimeTerminalValidationError`
- `5xx`：抛 `RuntimeTerminalServerError`
- 网络层异常、超时、连接失败、TLS、DNS：抛 `RuntimeTerminalTransportError`

## 6.2 为什么 422 不要重包成新的 terminal contract

因为当前冻结结论已经明确：
- 422 继续保持 FastAPI / Pydantic 默认行为
- 其主要价值是直接暴露字段、类型、枚举、结构错误

因此 SDK 最好：
- 保留原始响应体或其摘要
- 把它归类为 validation error
- 不要擅自改造成“业务失败”或“terminal rejected”之类模糊概念

## 6.3 为什么 409 不要自动重试

因为 runtime terminal 的 409 更接近：
- claim_token 已失效
- attempt 上下文不匹配
- 已终态重复提交
- lease 已切换

这些都不是“等一会儿网络恢复就会好”的问题。

所以 SDK 应做的是：
- 明确抛出 conflict
- 把判断权交回 caller

而不是：
- 自动 sleep + retry
- 自动换 claim_token 重发
- 自动改成读 snapshot 后再替 caller 做收口决策

---

## 7. `_request(...)` 层的异常职责边界

## 7.1 应该做的事

`_request(...)` 在异常层只建议做以下几件事：
- 捕获底层 HTTP client 的 transport 异常并映射为 `RuntimeTerminalTransportError`
- 按状态码映射到最小异常树
- 在异常对象中保留 method、path、status_code、response_text 等最小上下文
- 成功时返回 JSON body 或等价最小结构

## 7.2 不应该做的事

`_request(...)` 不建议做：
- 自动重试 409
- 看到 422 后自动修补 payload 再重发
- 看到 404 后自动猜别的 `job_id / attempt_id`
- 根据 5xx 自动无限重放终态写入
- 捕获所有异常后统一改造成一个无差别字符串错误

示意：

```python
def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            timeout=self.timeout_seconds,
            **kwargs,
        )
    except Exception as exc:
        raise RuntimeTerminalTransportError(
            "runtime terminal transport failure",
            method=method,
            path=path,
        ) from exc

    if response.status_code == 404:
        raise RuntimeTerminalNotFoundError(
            "runtime terminal resource not found",
            status_code=404,
            method=method,
            path=path,
            response_text=response.text,
        )
    if response.status_code == 409:
        raise RuntimeTerminalConflictError(
            "runtime terminal conflict",
            status_code=409,
            method=method,
            path=path,
            response_text=response.text,
        )
    if response.status_code == 422:
        raise RuntimeTerminalValidationError(
            "runtime terminal validation failed",
            status_code=422,
            method=method,
            path=path,
            response_text=response.text,
        )
    if response.status_code >= 500:
        raise RuntimeTerminalServerError(
            "runtime terminal server failure",
            status_code=response.status_code,
            method=method,
            path=path,
            response_text=response.text,
        )

    response.raise_for_status()
    return response.json()
```

这里的重点不是类名，而是边界：
- 统一请求入口映射错误
- 保留状态码语义
- 不注入业务决策

---

## 8. public method 与异常契约的关系

## 8.1 `complete_job(...)`

`complete_job(...)` 建议直接透传以下异常分层：
- `RuntimeTerminalNotFoundError`
- `RuntimeTerminalConflictError`
- `RuntimeTerminalValidationError`
- `RuntimeTerminalServerError`
- `RuntimeTerminalTransportError`

调用方应理解为：
- 404：通常是对象不存在或标识错误
- 409：多半是 attempt / claim / 状态上下文冲突
- 422：多半是 complete payload 构造错误
- 5xx / transport：才更接近链路故障

SDK 不应在这里做：
- 自动把 complete 改成 fail
- 自动再读 snapshot 并根据结果二次写 terminal
- 自动替 caller 认定“这次其实成功了”

## 8.2 `fail_job(...)`

`fail_job(...)` 的异常分层应与 `complete_job(...)` 保持一致。

尤其要保留对 422 的敏感度，因为 fail 路径更容易出现：
- `next_job_status` 非法
- `attempt_terminal_status` 非法
- `error_payload_json` 表达不符合约定
- `expire_lease` 使用错误

SDK 不应：
- 遇到 422 时自动重组 fail payload
- 遇到 409 时自动切换 `WAITING_RETRY / FAILED / STALE`

## 8.3 `get_job_snapshot(...)`

`snapshot` 读取通常只涉及：
- 200
- 404
- 5xx
- transport

其异常契约仍应与写侧共用同一套基类和分类习惯，避免 caller 在不同方法间处理风格漂移。

---

## 9. caller 对不同异常的最小处理建议

SDK 负责分类；caller 负责动作。

推荐 caller 收到异常后的默认处理方式如下：

### 9.1 `RuntimeTerminalNotFoundError`

建议动作：
- 先核对 `job_id`、path、对象存在性
- 回查 attempt 上下文来源是否错误
- 不要先入为主当成 lease 冲突

### 9.2 `RuntimeTerminalConflictError`

建议动作：
- 停止 blind retry
- 读取 snapshot
- 核验 `job_status / latest_attempt / active_lease`
- 判断是旧 attempt、旧 claim、已终态重复提交还是状态切换

### 9.3 `RuntimeTerminalValidationError`

建议动作：
- 直接检查 schema、字段类型、枚举、payload omission / null 表达
- 尽量保留原始 422 响应细节
- 不把它当成“服务端不稳定”

### 9.4 `RuntimeTerminalServerError`

建议动作：
- 依据上层策略做有限重试
- 如链路关键，重试前后都可追加 snapshot 核验
- 留意“第一次已成功但响应未返回”的可能性

### 9.5 `RuntimeTerminalTransportError`

建议动作：
- 明确这是网络/连接级失败
- 不与 409 / 422 混同
- 结合 timeout、连接状态与必要的 snapshot 判断是否需要补偿动作

---

## 10. 最小异常契约的 review 检查点

若在 code review 中要快速判断一个 SDK 的异常设计是否符合 v1，建议至少检查：

- 是否存在统一基类
- 是否能区分 404 / 409 / 422 / 5xx / transport
- 是否保留最小请求上下文（method / path / status_code / response_text）
- 是否没有把 422 压扁成模糊 bad request
- 是否没有把 409 做成默认自动重试
- 是否没有在异常层偷偷改写 payload 或替换 claim_token
- 是否把业务判断权保留给 caller
- 是否让 `complete_job(...) / fail_job(...) / get_job_snapshot(...)` 共享一致的异常契约

---

## 11. 反模式清单

以下做法若出现在 SDK 中，默认应视为偏离 v1：

1. **只有一个大异常，没有状态语义分层**
   - 结果：caller 无法区别冲突、构造错误、服务端异常。

2. **把 409 当成可透明重试的普通失败**
   - 结果：终态写入可能出现错误重放与更难解释的后续冲突。

3. **把 422 重新包装成看不出字段错误的模糊消息**
   - 结果：调用方失去最快定位 payload 问题的路径。

4. **transport failure 与 HTTP failure 不区分**
   - 结果：超时、连接问题会被误判为业务冲突或 contract 问题。

5. **在异常处理中自动猜测 ID、自动替换 claim_token、自动重提 terminal 请求**
   - 结果：SDK 越权，caller 失去对业务语义的控制。

6. **把异常层做成复杂框架，反而提高接入成本**
   - 结果：偏离“最小骨架”目标。

---

## 12. 一句话结论

如果一个 runtime terminal SDK 能稳定保留 `404 / 409 / 422 / 5xx / transport` 的最小异常分层，保留必要上下文，又不在异常处理中偷偷做自动重试、payload 修补或业务决策，那么它基本就满足了 v1 exception contract 的目标：

> **让 caller 看清楚发生了什么，而不是让 SDK 自作主张地替 caller 解释一切。**
