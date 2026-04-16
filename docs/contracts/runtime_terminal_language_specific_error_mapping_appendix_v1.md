# Runtime terminal language-specific error mapping appendix v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **language-specific error mapping appendix**。

它不重新定义 API contract，不改动 complete / fail 的写侧语义，也不替代 caller integration guide / FAQ / language-specific snippets pack，而是把不同语言调用方在接入 terminal 时最常见的 HTTP 错误，整理成一份 **可直接映射到调用栈、异常模型、处理动作的附录**。

本文档目标只有 3 件事：

1. 帮不同语言调用方统一理解 `200 / 404 / 409 / 422 / 5xx`
2. 帮 SDK / adapter / wrapper 设计者决定“哪些错误该透传，哪些动作不该自动做”
3. 帮值班排障和接入开发者减少跨语言口径漂移

配套阅读材料：
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_faq_decision_memo_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_language_specific_snippets_pack_v1.md`

本文档严格遵守当前 v1 冻结边界：
- 不改变 complete / fail 写侧语义
- facade 写侧不绕过 service 直写 repository
- 不触碰冻结测试 `tests/test_runtime_terminal_workflow.py`
- 422 继续保持 FastAPI / Pydantic 默认行为

---

## 2. 先给固定结论

无论使用哪种语言，runtime terminal v1 的错误理解都应先固定为下面 5 条：

1. `200` 表示请求被接受并成功完成终态回写，不代表调用方可以跳过必要的 snapshot 核验。
2. `404` 优先理解为对象不存在或标识错误，不优先理解为状态冲突。
3. `409` 优先理解为状态/上下文冲突，不是默认网络重试信号。
4. `422` 优先理解为 caller / SDK payload 构造错误，应保留 FastAPI / Pydantic 默认校验语义。
5. `5xx` 更接近基础设施或服务端异常，可做有限重试，但仍要避免把终态写入当成无限重放任务。

补一条最重要的总规则：

- **任何语言都不应该自动补猜 `job_id / attempt_id / worker_id / claim_token`，也不应该在 409 后擅自替换 claim_token 再重提。**

---

## 3. terminal 调用方的统一错误处理骨架

建议所有语言调用方都收敛到同一个处理骨架：

### 3.1 `POST /complete` 或 `POST /fail` 返回 200

建议动作：
- 记录 200 返回与请求上下文
- 在关键链路读取一次 snapshot
- 核验 `job_status / finished_at / latest_attempt / active_lease`
- 清理本地 attempt 上下文
- 不再重复提交终态

### 3.2 返回 404

建议动作：
- 优先核对 `job_id` 与调用路径是否正确
- 若是 snapshot 读取，优先排查对象是否存在
- 若是接入期问题，回到 caller / SDK 构造链路检查标识来源
- 不把 404 当成“稍后自动重试就会好”的默认场景

### 3.3 返回 409

建议动作：
- 立即停止 blind retry
- 读取 `GET /jobs/{job_id}` snapshot
- 判断是旧 claim、旧 attempt、已终态重复提交，还是 lease 已切换
- 只有在完成业务级判定后，才决定后续动作

### 3.4 返回 422

建议动作：
- 把它视为请求构造错误
- 直接检查字段缺失、字段类型、枚举值、对象结构
- 保留框架默认错误体，方便快速定位字段
- 不要吞掉细节后包装成模糊异常

### 3.5 返回 5xx

建议动作：
- 按调用栈做有限重试
- 每次重试前确认是否存在“前一次其实已经成功写入，但 caller 没拿到响应”的可能
- 如链路关键，重试前后都建议补 snapshot 核验
- 避免无上限重放同一 terminal payload

---

## 4. HTTP 状态码到处理语义的统一映射表

| HTTP 状态 | 统一语义 | 首要怀疑方向 | 默认动作 | 不建议做 |
| --- | --- | --- | --- | --- |
| 200 | 已成功回写 terminal 结果 | 无 | 记录结果，必要时读 snapshot | 继续重复提交同一终态 |
| 404 | 对象不存在 / 标识错误 | job_id 错、读取目标不存在、路径错 | 校对标识与对象存在性 | 当作状态冲突处理 |
| 409 | 状态或上下文冲突 | claim_token 不匹配、attempt 不匹配、已终态重复提交 | 先读 snapshot，再做业务判定 | 原样 payload 自动重放 |
| 422 | 请求构造不合法 | 字段缺失、类型错误、枚举非法、结构错误 | 修 payload / schema 构造 | 吞错误细节后模糊包装 |
| 5xx | 服务端 / 基础设施异常 | 临时依赖故障、服务抖动、未预期异常 | 有上限重试，并结合 snapshot 核验 | 无限重试或自动改写语义 |

---

## 5. 按 endpoint 理解错误差异

## 5.1 `POST /complete`

### 200
表示这次 attempt 的成功收口已被接受。调用方后续重点核验：
- `job_status`
- `finished_at`
- `latest_attempt.completion_status`
- `latest_attempt.result_ref`
- `active_lease`

### 409
优先说明以下问题之一：
- 四元身份字段不来自同一次真实 attempt
- 该 job / attempt 已收口
- 当前 worker / lease 上下文已不是合法提交者

**不应自动做：**
- 把 complete 改成 fail 再提交
- 自动换 claim_token
- 原样 payload 反复重试

### 422
complete 常见触发点：
- 缺少必填字段
- `completion_status` 非法
- 字段类型错误
- `metadata_json` 结构不符

### 5xx
更接近写入链路或基础设施异常。可有限重试，但关键链路仍应补 snapshot，避免把“第一次已成功，第二次变冲突”误判成纯失败。

## 5.2 `POST /fail`

### 200
表示这次 attempt 已按失败类路径收口。调用方后续重点核验：
- `job_status`
- `latest_attempt.attempt_status`
- `latest_attempt.error_code`
- `latest_attempt.error_message`
- `active_lease`

### 409
优先说明以下问题之一：
- 当前上下文已失效
- terminal 已被其他动作收口
- 该 attempt 与 claim / worker 不匹配

**不应自动做：**
- 为了“碰碰运气”替换 `claim_token`
- 自动把 `WAITING_RETRY` 改成 `FAILED`
- 自动切换 `attempt_terminal_status`

### 422
fail 常见触发点：
- `next_job_status` 不在 `FAILED / WAITING_RETRY / STALE` 中
- `attempt_terminal_status` 不在 `FAILED / TIMED_OUT / STALE` 中
- `error_payload_json` 显式传了 `null`
- `expire_lease` 被错误硬编码

### 5xx
更接近服务端失败。允许有限重试，但不要绕过业务判断把 fail 当成可无限投递消息。

## 5.3 `GET /jobs/{job_id}`

### 200
表示读取快照成功，可用于：
- 核验 complete / fail 是否已生效
- 排查 409
- 观察 `latest_attempt` 与 `active_lease`

### 404
最常见语义是：
- job 不存在
- job_id 错误
- 调用方读取了错误对象

### 5xx
表示读取链路故障。若它发生在 409 排障链路中，说明当前还缺少足够证据，不应仓促做状态推断。

---

## 6. 不同语言的异常映射建议

## 6.1 Python `requests`

建议映射：
- `200`：正常返回 `response.json()`
- `404`：抛出显式资源不存在类异常，或按业务返回 `None + 上下文`
- `409`：抛出 `RuntimeTerminalConflictError`
- `422`：抛出 `RuntimeTerminalValidationError`
- `5xx`：抛出 `RuntimeTerminalServerError`
- 网络层异常：保留 `requests.Timeout` / `requests.ConnectionError` 语义

建议原则：
- 不要只调用 `raise_for_status()` 后把 409 / 422 全抹平成同一种 `HTTPError`
- 至少保留 `status_code + response.text + request payload 摘要`

示意：

```python
if response.status_code == 200:
    return response.json()
if response.status_code == 404:
    raise RuntimeTerminalNotFoundError(response.text)
if response.status_code == 409:
    raise RuntimeTerminalConflictError(response.text)
if response.status_code == 422:
    raise RuntimeTerminalValidationError(response.text)
if 500 <= response.status_code < 600:
    raise RuntimeTerminalServerError(response.text)
response.raise_for_status()
```

## 6.2 Python `httpx`

建议映射与 `requests` 保持一致，但额外保留：
- `httpx.TimeoutException`
- `httpx.NetworkError`

建议原则：
- SDK 若基于 `httpx`，应把 HTTP 语义错误与 transport-level 异常分开
- 409 / 422 不应被混成统一“请求失败”异常

## 6.3 Shell / `curl`

Shell 场景通常没有强异常模型，因此建议最小映射为：
- `200`：退出 0，打印 body
- `404`：退出非 0，并打印“对象不存在/标识错误”
- `409`：退出非 0，并打印“状态冲突，请先读 snapshot”
- `422`：退出非 0，并打印“payload 不合法，请检查字段与枚举”
- `5xx`：退出非 0，可由外层脚本做有限重试

建议原则：
- 不要只看 `curl` 进程是否成功，还要显式检查 HTTP code
- CI / shell wrapper 不要把所有非 200 统称为“网络失败”

## 6.4 TypeScript / Node.js

建议映射：
- `200`：返回解析后的 JSON
- `404`：抛出 `RuntimeTerminalNotFoundError`
- `409`：抛出 `RuntimeTerminalConflictError`
- `422`：抛出 `RuntimeTerminalValidationError`
- `5xx`：抛出 `RuntimeTerminalServerError`
- `fetch` 自身失败：保留网络层异常

建议原则：
- 若封装统一 `request(...)` helper，应保留 `status`、`body`、`endpoint`、`request_id`（若有）
- 不要吞掉 422 明细后只返回 `bad request`

示意：

```ts
if (response.status === 200) {
  return await response.json();
}
if (response.status === 404) {
  throw new RuntimeTerminalNotFoundError(await response.text());
}
if (response.status === 409) {
  throw new RuntimeTerminalConflictError(await response.text());
}
if (response.status === 422) {
  throw new RuntimeTerminalValidationError(await response.text());
}
if (response.status >= 500) {
  throw new RuntimeTerminalServerError(await response.text());
}
throw new Error(`unexpected status: ${response.status}`);
```

---

## 7. 推荐异常分层

建议不同语言都尽量保留下面这组概念层，而不是只暴露一个笼统 `TerminalError`：

- `RuntimeTerminalNotFoundError`
- `RuntimeTerminalConflictError`
- `RuntimeTerminalValidationError`
- `RuntimeTerminalServerError`
- `RuntimeTerminalTransportError`（可选，承接 timeout / connection / DNS 等）

这样做的好处：
- 业务方能明确区分“该修 payload”还是“该读 snapshot”
- SDK 不必靠解析模糊错误字符串做分支
- 值班排障能快速按类别聚类

不建议的做法：
- 所有错误统一包成 `RuntimeTerminalError`
- 409 / 422 / 404 都只留一句 `request failed`
- 自动改写错误类别，让调用方失去真实状态信息

---

## 8. 语言无关的“不要做”清单

无论哪种语言，都不建议在错误处理层自动做下面这些动作：

1. 自动补猜 `job_id / attempt_id / worker_id / claim_token`
2. 409 后原样 payload 无限重放
3. 擅自替换 `claim_token`
4. 自动把 complete 改成 fail，或把 fail 改成 complete
5. 自动重写 `next_job_status` / `attempt_terminal_status`
6. 吞掉 422 后只抛一个模糊异常
7. 把 terminal 当成 claim / heartbeat / retry 调度入口

---

## 9. 推荐最小日志字段

为方便跨语言排障，建议各语言在记录 terminal 错误时统一保留：

- endpoint
- method
- job_id
- attempt_id
- worker_id
- HTTP status
- terminal action（complete / fail / snapshot）
- terminal_reason（若有）
- error_code（若有）
- request timestamp
- response body 摘要

注意：
- `claim_token` 通常不建议完整明文打日志，可按安全要求做脱敏
- 不要为了日志完整性泄漏敏感 payload

---

## 10. 最小落地建议

如果你正在做一层新的语言 SDK / adapter，最小可落地建议是：

1. 只先封装 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`
2. 统一保留 `404 / 409 / 422 / 5xx` 的显式分支
3. 409 后只给出“先读 snapshot”的动作建议，不自动帮业务重试
4. 422 原样保留框架校验细节
5. 关键链路在 200 后增加 snapshot 核验能力

一句话总结：

- **runtime terminal v1 的跨语言错误映射重点，不是做花哨异常体系，而是确保所有调用方都对 409 / 422 / 404 有相同语义认知，并且不在 SDK 层偷偷替业务做决定。**
