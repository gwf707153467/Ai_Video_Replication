# Runtime terminal caller FAQ v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **caller FAQ**。

它面向直接接入 terminal 的调用方，包括：
- worker runtime reporter
- job executor / orchestrator
- SDK / adapter 封装者
- 接手排障的一线开发与值班同学

它不重新定义 API contract，不替代 caller integration guide、FAQ decision memo、language-specific snippets pack，也不重开写侧实现讨论。

它的目标更窄：
- 用 caller 视角回答最常见接入问题
- 减少“已在其他文档定过，但接入时仍反复确认”的问题
- 给出最小可执行判断口径

建议配套阅读：
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_faq_decision_memo_v1.md`
- `runtime_terminal_language_specific_snippets_pack_v1.md`
- `runtime_terminal_language_specific_error_mapping_appendix_v1.md`

本文档严格遵守当前 v1 冻结边界：
- terminal = terminal write + snapshot read，不是调度入口
- 不重定义 API contract
- 不改变 complete / fail 写侧语义
- facade 写侧不绕过 service 直写 repository
- 不触碰 `tests/test_runtime_terminal_workflow.py`
- 422 保持 FastAPI / Pydantic 默认行为

---

## 2. 先给 caller 的最小固定认知

接 terminal 前，先把下面 8 条当成固定前提：

1. terminal 负责 **收口一次 attempt**，不是安排下一次执行。
2. `POST /complete` 表示成功收口，`POST /fail` 表示失败类收口。
3. `GET /jobs/{job_id}` 是 snapshot 读取入口，用于核验和排障。
4. `job_id / attempt_id / worker_id / claim_token` 必须来自同一次真实 attempt。
5. 409 优先视为状态或上下文冲突，不是默认自动重试信号。
6. 422 优先视为 payload/schema 构造错误。
7. `completion_status` 不等于 `job_status`。
8. complete / fail 成功后，关键链路建议补一次 snapshot 核验。

---

## 3. Caller FAQ

### Q1. 我什么时候应该调用 complete？

**答：**只有在“这次 attempt 已经明确成功结束”时才调用。

至少应满足：
- 本次 attempt 的实际工作已经完成
- 成功产物引用已经确定，例如 `result_ref`
- 当前调用方仍持有匹配的 `worker_id + claim_token`
- 不再需要把这个 attempt 维持在运行态

不要在这些场景调用 complete：
- 只是“基本快完成了”
- 产物还没稳定落地
- 不确定当前 attempt / lease 是否还是自己的
- 只是想试探服务端会不会帮你收口

### Q2. 我什么时候应该调用 fail？

**答：**当本次 attempt 已确认不能按成功路径收口，而且你已经明确知道 job 下一步怎么走时。

至少应满足：
- 本次 attempt 确认不能成功完成
- 已选定 `next_job_status`
- 已选定 `attempt_terminal_status`
- 四元身份字段来自同一次真实 attempt

典型例子：
- 当前 attempt 执行失败，job 不再继续：`FAILED + FAILED`
- 当前 attempt 超时，但 job 允许继续重试：`WAITING_RETRY + TIMED_OUT`
- 当前 attempt 已 stale：`STALE + STALE`

### Q3. complete 和 fail 能不能统一理解成“更新 job 状态”？

**答：**不能。

caller 应把它理解成：
- complete / fail = 对 **当前 attempt** 做 terminal 收口
- snapshot = 读取当前 job 的可观察状态

terminal 不是一个“万能 update endpoint”，也不是“按 job 覆盖最新状态”的写口。

### Q4. 为什么四元身份字段必须来自同一次真实 attempt？

**答：**因为 terminal 判断的不是“这个 job 看起来像不像同一个”，而是“你是否真的是这次 attempt 的合法终态提交者”。

四元字段是：
- `job_id`
- `attempt_id`
- `worker_id`
- `claim_token`

只要其中一项来自旧上下文、缓存残留、并行 worker、人工拼接，都会显著增加 409 风险。

### Q5. SDK 能不能帮我自动补猜 `attempt_id` 或 `claim_token`？

**答：**不建议，也不应作为 v1 推荐做法。

原因很直接：
- 自动补猜会掩盖真实上下文错配
- 你以为更方便，实际更难排障
- 很容易把旧 attempt / 旧 lease 当成当前上下文继续回写

推荐做法是：
- 把四元身份字段作为同一份 attempt context 原样透传
- SDK 只做最小封装，不做隐式修复

### Q6. 409 到底代表什么？

**答：**优先代表“请求已到服务端，但当前状态不接受它”。

caller 的第一反应应该是：
- 这是不是旧 claim_token？
- 这是不是旧 attempt_id？
- 这是不是已经被别的动作收口了？
- 这是不是 worker / lease 已变更？

不应把 409 先当成普通网络失败。

### Q7. 409 之后我该怎么做？

**答：**先停，不要 blind retry。先读 snapshot。

建议顺序：
1. 记录 409 请求与响应摘要
2. 调 `GET /jobs/{job_id}`
3. 看 `job_status / latest_attempt / active_lease`
4. 判断是“其实已成功收口”还是“当前上下文已失效”
5. 再决定是否由上层业务发起新动作

不建议：
- 原样 payload 无限重放
- 擅自替换 `claim_token`
- 把 complete 改成 fail 硬闯
- 看到 409 就做 HTTP 层自动重试

### Q8. 422 到底代表什么？

**答：**优先代表 caller 自己构造的请求不合法。

常见情况：
- 缺字段
- 类型错误
- 枚举值非法
- payload 结构不符合 schema

caller 处理 422 的正确方向通常是：
- 回头检查自己的 payload 构造
- 保留 FastAPI / Pydantic 返回细节
- 修字段、修类型、修枚举

不建议把 422 包装成一个只有“请求失败”的模糊异常。

### Q9. 404 在 caller 侧通常怎么理解？

**答：**优先理解为对象不存在或标识错误。

最典型的是 snapshot 读取：
- job 不存在
- 路径或 `job_id` 写错

caller 不应把 404 与 409 混成一类“状态冲突”。

### Q10. complete 成功返回 200 后，我是不是就可以完全不再检查了？

**答：**非关键链路可以按业务自行决定，但关键链路建议补一次 snapshot 核验。

建议重点看：
- `job_status`
- `finished_at`
- `latest_attempt`
- `active_lease`
- 成功产物引用是否符合预期

原因很简单：
- 你拿到 200，只能说明写入动作成功返回
- 但 caller 往往还需要做审计、清理上下文、确认结果视图已收敛

### Q11. fail 成功返回 200 后，我应该核验什么？

**答：**重点核验三层：
- job 层：`job_status`
- attempt 层：`latest_attempt` 中的失败信息与终态字段
- lease 层：`active_lease` 是否符合预期释放/过期

特别是超时、重试、stale 场景，建议核对：
- `next_job_status`
- `attempt_terminal_status`
- `error_code`
- `error_message`
- `active_lease`

### Q12. `completion_status` 为什么不能直接当 `job_status` 用？

**答：**因为两个字段描述的层级不同。

- `completion_status`：成功 attempt 的完成标签
- `job_status`：整个 job 当前状态

caller 一旦把两者混用，就很容易在 snapshot 核验、错误处理、重试判断里做错分支。

### Q13. fail 里为什么要同时有 `next_job_status` 和 `attempt_terminal_status`？

**答：**因为“这次 attempt 怎么结束”与“整个 job 接下来怎么走”不是一个问题。

例如：
- attempt 超时，但 job 仍可重试
- attempt 失败，但 job 直接失败收口
- attempt stale，job 也 stale

这就是为什么 caller 必须显式给出两个字段，而不是期待服务端替你猜。

### Q14. `next_job_status` 允许哪些值？

**答：**仅允许：
- `FAILED`
- `WAITING_RETRY`
- `STALE`

caller 不应传其他值，也不应让 SDK 在底层偷偷改写。

### Q15. `attempt_terminal_status` 允许哪些值？

**答：**仅允许：
- `FAILED`
- `TIMED_OUT`
- `STALE`

caller 应按真实 attempt 收口语义选择，不要为了“先提交成功”而随便凑一个值。

### Q16. `error_payload_json` 为什么不能显式传 `null`？

**答：**因为 v1 不把它当作一个“三态空值协议”字段。

caller 的处理原则应是：
- 有补充上下文：传对象
- 没补充上下文：省略字段，或传空对象语义
- 不要显式传 `null`

### Q17. `expire_lease` 应该怎么选？

**答：**按真实业务语义选，不能写死。

可粗略理解为：
- `true`：更接近过期/超时类结束
- `false`：更接近正常释放

caller 不要把它当成无关实现细节；它属于失败收口语义的一部分。

### Q18. `manifest_artifact_id` 为什么可以是字符串、UUID 或空？

**答：**因为 caller 的上游产物链路与引用约定可能不完全一致，v1 对这里采用兼容策略。

对 caller 来说，关键不是“它一定长成哪种强约束类型”，而是：
- 有值时传真实引用
- 没有时允许为空
- 不要因为这个字段过度阻塞 complete 主路径

### Q19. caller 最小应该封哪些 SDK 方法？

**答：**推荐只先封最小集合：
- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`
- `_request(...)`
- `RuntimeAttemptContext`

这样既能减少样板代码，也不会把业务语义偷偷包进 SDK 黑盒。

### Q20. caller 最不该让 SDK 自动做什么？

**答：**至少不要自动做这些事：
- 自动重试 409
- 自动补猜四元身份字段
- 自动替换 `claim_token`
- 自动把 complete 改成 fail，或反过来
- 吞掉 422 细节，只抛一个模糊异常
- 把 terminal 当 claim / heartbeat / retry 调度入口

### Q21. 调 complete / fail 之前，caller 最小自检清单是什么？

**答：**建议至少检查：
- 四元身份字段是否来自同一次真实 attempt
- 当前动作是否真的是“终态收口”而不是中间状态汇报
- 成功/失败路径是否已经分清
- fail 路径是否已明确 `next_job_status` 与 `attempt_terminal_status`
- payload 是否满足 schema
- 是否准备在关键链路上补一次 snapshot 核验

### Q22. terminal 能不能拿来做 claim、heartbeat、重试调度？

**答：**不能。

caller 要始终记住：
- terminal 只做 terminal write + snapshot read
- 它不是调度入口
- 也不是 runtime 生命周期的所有动作入口

把 terminal 当成 claim / heartbeat / retry 调度入口，会让 caller 语义越来越混乱，最终把冲突、回写、编排、恢复混在一起。

---

## 4. Caller 最小动作建议

如果你只是想知道 caller 在接 terminal 时最小该怎么做，可以直接记下面这套：

1. 从同一次真实 attempt 上下文拿到 `job_id / attempt_id / worker_id / claim_token`
2. 成功场景调用 complete；失败场景调用 fail
3. 显式处理 `404 / 409 / 422 / 5xx`
4. 409 时先读 snapshot，不 blind retry
5. 422 时优先回头检查 payload 构造
6. 关键链路在 200 后再读一次 snapshot 做核验
7. 清理本地 attempt 上下文，不重复提交终态

---

## 5. Caller 统一“不要做”清单

以下行为在 caller / SDK / adapter 中都不推荐：

- 自动补猜四元身份字段
- 从多个来源拼装 attempt 身份
- 409 后原样 payload 无限重放
- 擅自替换 `claim_token`
- 自动把 complete 改成 fail，或反过来
- 自动重写 `next_job_status` / `attempt_terminal_status`
- 吞掉 422 细节
- 把 terminal 当成 claim / heartbeat / retry 调度入口
- complete / fail 成功后继续对同一 attempt 重复提终态

---

## 6. 一句话结论

对 caller 来说，runtime terminal v1 最重要的不是“怎么把请求发出去”，而是：

**只在真实 attempt 上下文中做正确的终态收口，并在关键链路里用 snapshot 验证系统状态已经按预期收敛。**
