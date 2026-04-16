# Runtime terminal FAQ / decision memo v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **FAQ / decision memo**。

它不重新定义 API contract，不重开写侧实现，也不替代 caller integration guide / SDK snippet pack，而是把当前最容易反复被问到、最容易被误解、最值得冻结说明的设计决策集中写清楚，方便以下角色统一口径：
- terminal caller / SDK 封装者
- worker runtime reporter 开发者
- orchestrator / job executor 接入开发者
- 值班排障人员
- 后续接手维护者

本文档的目标只有两个：
1. 回答高频 FAQ，减少重复解释
2. 固化关键决策理由，避免后续在冻结边界外反复重开

配套阅读材料：
- `runtime_terminal_caller_integration_guide_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_orchestration_explainer_v1.md`
- `runtime_terminal_external_docs_index_v1.md`

本文档严格遵守当前 v1 冻结边界：
- 不改变 complete / fail 写侧语义
- facade 写侧不绕过 service 直写 repository
- 不触碰冻结测试 `tests/test_runtime_terminal_workflow.py`
- 422 继续保持 FastAPI / Pydantic 默认行为

---

## 2. 先给结论：runtime terminal v1 的 8 条固定认知

1. runtime terminal 是 **终态回写接口**，不是调度接口。
2. `POST /complete` 和 `POST /fail` 只回答“这次 attempt 如何收口”，不回答“谁该继续跑”。
3. `job_id / attempt_id / worker_id / claim_token` 必须来自 **同一次真实 attempt 上下文**。
4. 409 优先理解为 **状态/上下文冲突**，不是默认网络重试信号。
5. 422 优先理解为 **caller / SDK payload 构造错误**，不是 terminal 自定义业务错误。
6. `completion_status` 不是 `job_status`，attempt 标签与 job 走向不是一个维度。
7. facade 写侧的职责是委托与收口，**不能绕过 service 直写 repository**。
8. complete / fail 成功后，如链路关键，应使用 `GET /jobs/{job_id}` 做 snapshot 核验。

---

## 3. FAQ：能力边界

### Q1. runtime terminal 到底是做什么的？

**答：**它负责把一次 runtime attempt 的最终结果回写为 terminal state。

更直白地说：
- complete：这次 attempt 成功收口
- fail：这次 attempt 失败类收口
- snapshot：读取当前 terminal 结果用于核验/排障

它不负责：
- claim
- heartbeat
- worker 抢占
- retry 调度
- 历史终态修正
- “下一步由谁来执行”的编排决策

**决策 memo：**
之所以强行把 runtime terminal 收窄成“终态回写”，就是为了避免把调度、租约、回写、修正、恢复混成一个写口，导致调用方把所有异常都塞进同一个 endpoint 里。v1 明确只做 terminal write + snapshot read。

### Q2. 为什么 complete / fail 不被设计成一个通用 update endpoint？

**答：**因为 success-path 和 failure-path 的语义不同，调用方决策不同，排障分类也不同。

拆开后有三个直接收益：
- 调用方更容易在代码层表达“成功收口”与“失败收口”
- 错误字段、状态字段、枚举字段能更清晰约束
- 排障时能快速判断是成功路径误写还是失败路径误写

**决策 memo：**
v1 不追求“一个万能更新接口”，而追求“调用语义一眼可判”。这是为了降低接入歧义，而不是为了追求接口数量最少。

### Q3. 为什么 snapshot 要单独保留 `GET /jobs/{job_id}`？

**答：**因为 terminal 写成功不代表调用方就一定拿到了完整、可信、可追责的最终视图。

重要链路里，调用方经常还需要确认：
- job 是否已终态
- latest attempt 是否符合预期
- active lease 是否释放/过期
- `result_ref` / `manifest_artifact_id` 是否已落到可读快照中

**决策 memo：**
写完再读一次 snapshot，是把“主观以为写成功”变成“客观确认系统状态已收敛”。这也是把 409 排障和终态核验统一到同一个读取入口的原因。

---

## 4. FAQ：身份字段与上下文一致性

### Q4. 为什么四元身份字段必须来自同一次真实 attempt？

**答：**因为 terminal write 的本质不是“按 job 覆盖结果”，而是“由当前持有有效执行上下文的一方，对当前 attempt 做终态回写”。

四元字段：
- `job_id`
- `attempt_id`
- `worker_id`
- `claim_token`

只要其中一项来自旧上下文、并行上下文、或猜测上下文，就很容易造成：
- lease 冲突
- attempt mismatch
- 已终态重复提交
- 错 worker 回写

**决策 memo：**
v1 把这四个字段视为一次执行上下文的最小身份束，不允许 SDK 内部“补猜”“重拼”“自动纠错”。这样虽然对调用方更严格，但能最大化暴露真实状态问题，避免 silent corruption。

### Q5. 为什么 SDK 不能从数据库、缓存、环境变量补猜这四个字段？

**答：**因为补猜常常在“看起来更方便”的同时，把真正的上下文错配隐掉了。

典型坏处：
- 你以为拿到了当前 attempt，实际拿到的是上一次 attempt
- 你以为 claim_token 还有效，实际 lease 已切换归属
- 你以为 worker_id 只是标识，实际它参与冲突判定

**决策 memo：**
terminal SDK 的职责不是“帮你猜对”，而是“忠实透传执行上下文”。调用链越长，越要避免在末端做隐式修复。

### Q6. 为什么 complete / fail 后不允许对同一 attempt 再补提另一种终态？

**答：**因为 terminal write 是收口动作，不是事后修补动作。

例如：
- complete 成功后再补 fail
- fail 成功后再补 complete

这都会破坏“同一 attempt 只应有一种终态收口”的基本认知，也会让排障与审计变得不可信。

**决策 memo：**
v1 宁可把这类行为显式暴露为冲突，也不允许调用方把 terminal 接口当成“可多次覆盖的最终状态修订器”。

---

## 5. FAQ：409 / 422 / 404 应该怎么理解

### Q7. 为什么 409 不是默认网络重试？

**答：**因为 409 的核心含义不是“这次请求没送到”，而是“这次请求送到了，但当前系统状态不接受它”。

优先怀疑的方向通常是：
- claim_token 不匹配
- attempt_id 不匹配
- worker_id 不匹配
- job 已终态
- 同一请求重复提交
- lease 归属已变化

**决策 memo：**
把 409 当成普通 HTTP retry，会把真实冲突放大成大量无效重复请求，既解决不了问题，还会污染日志与排障路径。v1 明确要求：409 先读 snapshot，再做判定，必要时升级人工。

### Q8. 什么时候 409 可以重试？

**答：**不是“HTTP 层自动重试”，而是“在完成状态判定后，按新的真实上下文重新发起新的业务动作”。

可接受的方向是：
- 先确认旧请求其实已经成功，只是 caller 没拿到返回
- 或确认当前已有新的合法 attempt / lease，需要在新上下文中做新动作

不接受的方向是：
- 原样 payload 无限重放
- 擅自替换 claim_token 再重提
- 把 complete 改成 fail 试图硬闯

**决策 memo：**
这里的“重试”是业务级重新判定后的再动作，不是 transport-level blind retry。

### Q9. 为什么 422 不统一包成 terminal 自定义错误结构？

**答：**因为 422 在这里就是框架层输入校验失败，保留 FastAPI / Pydantic 默认行为，能最大化降低额外封装复杂度，并保留标准化校验定位能力。

422 常见含义：
- 必填字段缺失
- 字段类型不对
- 枚举值非法
- payload 结构不符合 schema

**决策 memo：**
v1 不为了“响应长得整齐”而牺牲框架默认 validator 可读性。调用方若拿到 422，应优先修 SDK / caller 构造逻辑，而不是要求 terminal 再包一层统一错误壳。

### Q10. 404 在 terminal 里一般意味着什么？

**答：**最常见是读取对象不存在，例如 `GET /jobs/{job_id}` 查不到 job。

对于调用方，404 更接近：
- job 不存在
- 读取目标不存在
- 上下游引用的 job_id 有误

**决策 memo：**
404 的优先排查方向是“对象是否存在 / 标识是否正确”，而不是与 409 混在一起当成状态冲突。

---

## 6. FAQ：状态语义与字段选择

### Q11. 为什么 `completion_status` 不能当作 `job_status`？

**答：**因为 `completion_status` 描述的是 attempt 成功完成时的补充标签，而 `job_status` 描述的是 job 整体所处状态，两者不是同一层级。

例如：
- complete 请求里的 `completion_status="SUCCEEDED"`，强调的是这次 attempt 成功完成
- snapshot 里的 `job_status`，强调的是整个 job 是否已经成功收口/进入其他终态

**决策 memo：**
如果让调用方把两者混用，后续在 retry、stale、历史 attempt 排障时会非常混乱。v1 明确保留两个维度。

### Q12. 为什么 fail 要同时提供 `next_job_status` 和 `attempt_terminal_status`？

**答：**因为 job 走向和 attempt 收口并不是一个维度。

典型例子：
- 本次 attempt 超时，但 job 允许重试：`WAITING_RETRY` + `TIMED_OUT`
- 本次 attempt 失败，job 也不再继续：`FAILED` + `FAILED`
- 本次 attempt 已 stale，job 也 stale：`STALE` + `STALE`

**决策 memo：**
若只保留一个状态字段，调用方就不得不把“当前 attempt 怎样结束”与“整个 job 下一步如何走”压成同一个值，会显著增加歧义。

### Q13. 为什么 `error_payload_json` 不能显式传 `null`？

**答：**因为 v1 对它的理解是“对象型补充错误上下文”，不是“三态空值协议”。

所以：
- 有内容：传对象
- 没内容：省略字段，或使用空对象语义
- 不要显式传 `null`

**决策 memo：**
显式 `null` 容易把“字段不存在”“字段为空对象”“字段被显式清空”混成一团。v1 选择更严格但更清晰的边界。

### Q14. 为什么 `manifest_artifact_id` 允许 `UUID | str | None`？

**答：**因为接入侧实际存在不同阶段、不同存储约定、不同产物链路，统一只收 UUID 反而会导致大量不必要适配。

**决策 memo：**
这个字段的设计偏兼容性：它允许更宽的引用形态，但不影响 complete/fail 的主干语义。v1 在这里优先选“兼容现有调用方落地”，而不是过度收紧。

### Q15. 为什么 `expire_lease` 不能被固定写死？

**答：**因为“lease 正常释放”与“lease 以过期语义结束”不是一回事。

- `expire_lease=true`：强调过期/超时类结束语义
- `expire_lease=false`：强调正常 release

**决策 memo：**
这个开关是业务语义的一部分，不是实现噪音。v1 要求调用方按真实结束场景选择，而不是为图省事一律写成同一个值。

---

## 7. FAQ：分层设计与冻结边界

### Q16. 为什么 facade 写侧不能绕过 service 直写 repository？

**答：**因为 service 层持有 terminal write 的业务语义、前置条件校验、冲突规则与状态收口逻辑；如果 facade 直接写 repository，就会把这些规则打散到边界层，最终导致：
- 规则重复
- 事务语义不一致
- 错误边界漂移
- 后续维护者难以判断哪一层才是语义源头

**决策 memo：**
v1 明确把 service 作为写侧语义中心，facade 只是边界与委托层。这个边界不是代码风格偏好，而是为了冻结行为一致性。

### Q17. 为什么不改 complete / fail 写侧事务顺序？

**答：**因为这部分已经通过当前实现与既有验证路径封板，继续改动会放大回归面，且收益不成比例。

**决策 memo：**
v1 当前目标不是“把理论上可能更优的内部顺序都再优化一轮”，而是“保持已验证闭环稳定，并把外向可用材料补齐”。冻结写侧顺序，是为了保证交付稳定性。

### Q18. 为什么不能去改 `tests/test_runtime_terminal_workflow.py`？

**答：**因为它已经被当作 v1 关键闭环与边界语义的冻结验证面之一。

**决策 memo：**
在当前阶段，测试文件不仅是检查工具，也是一部分冻结事实。随意修改它，等于同时改动了回归基线和行为解释基线。

---

## 8. FAQ：caller / SDK 实践建议

### Q19. complete / fail 成功返回后，调用方还应该做什么？

**答：**最小建议是：
1. 记录 200 返回
2. 如链路关键，读取 snapshot
3. 对照 job / latest attempt / active lease 三层核验
4. 清理本地 attempt 上下文
5. 不要对同一 attempt 再重复提交终态

**决策 memo：**
terminal 写成功只代表“服务端接受了收口动作”，而链路闭环通常还需要 caller 自己做一次结果确认与上下文清理。

### Q20. SDK 最小该封什么，不该封什么？

**答：**建议最小封装：
- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`
- `_request(...)`
- `RuntimeAttemptContext`

不建议 SDK 默默做的事：
- 自动重试 409
- 自动补猜四元身份字段
- 自动把 complete 改成 fail
- 自动替换 claim_token
- 把 422 吞掉再包装成模糊异常

**决策 memo：**
v1 的 SDK 设计原则是“帮调用方少写样板代码”，不是“替调用方隐式决策业务语义”。

### Q21. 为什么建议 caller 在关键链路里补一次 snapshot 核验？

**答：**因为 snapshot 是唯一统一的、可用于成功核验与冲突排障的读侧入口。

它能同时回答：
- job 现在是什么状态
- latest attempt 最终是什么状态
- result / manifest 是否落库
- active lease 是否还存在

**决策 memo：**
同一个读取入口既可服务 happy path 核验，也可服务 409 排障，这是 v1 读侧设计最有价值的统一点之一。

---

## 9. 常见误解纠偏清单

### 误解 1：terminal 是 runtime 调度总入口
纠偏：不是。它只负责终态回写与结果快照读取。

### 误解 2：409 基本等于网络抖动
纠偏：不是。409 优先代表状态冲突、上下文失配、重复提交或 lease 冲突。

### 误解 3：422 应该也包装成 terminal 统一错误 schema
纠偏：v1 明确保留 FastAPI / Pydantic 默认校验行为。

### 误解 4：拿不到 claim_token 时，SDK 可以自己补一个
纠偏：不可以。claim_token 是冲突判定的一部分，不是装饰字段。

### 误解 5：`completion_status` 就是 job 的最终状态
纠偏：不是。它只描述 attempt 成功完成标签。

### 误解 6：fail 时把 `error_payload_json` 显式写成 `null` 更清楚
纠偏：不对。无内容时应省略字段或按空对象语义处理。

### 误解 7：complete 成功后如果又发现一点问题，可以再补一个 fail 修正
纠偏：不可以。terminal write 是收口动作，不是修订器。

### 误解 8：遇到 409，换个 claim_token 再试一下可能就好了
纠偏：不可以。这会制造伪造上下文，破坏冲突排查真实性。

---

## 10. 决策摘要：哪些结论应视为 v1 默认前提

以下结论建议在后续讨论中直接视为默认前提，不再反复重开：

### 10.1 接口定位前提
- terminal = terminal write + snapshot read
- 不承担调度职责
- 不承担历史终态修订职责

### 10.2 调用方前提
- 四元身份字段必须原样透传
- 409 先读 snapshot，再判定
- 422 优先修 caller / SDK payload

### 10.3 架构前提
- facade 写侧不绕过 service
- service 是 terminal 语义中心
- repository 不承载业务决策解释

### 10.4 冻结前提
- 不改 complete / fail 写侧语义
- 不触碰 `tests/test_runtime_terminal_workflow.py`
- 不把 422 强制改造成 terminal 错误包装

---

## 11. 推荐使用方式

如果你的问题是：

### “我到底该调 complete 还是 fail？”
先看：`runtime_terminal_caller_integration_guide_v1.md`

### “我想直接复制一个最小 Python terminal adapter 骨架”
先看：`runtime_terminal_sdk_usage_snippet_pack_v1.md`

### “我不理解为什么这里会 409 / lease conflict / attempt mismatch”
先看：`runtime_terminal_orchestration_explainer_v1.md`

### “我只想知道这些设计为什么定成现在这样，不想重读一堆实现细节”
先看：本文档

---

## 12. 下一步最自然的增量方向

在不重开 v1 冻结边界的前提下，本文档之后最自然的增量有两类：

### 12.1 language-specific snippets pack v1
补充不同语言/客户端栈的样例：
- `requests`
- `httpx`
- `curl`
- TypeScript

### 12.2 operator / caller FAQ 扩展版
如果后续真实接入问题开始集中，可再把 FAQ 拆成：
- caller FAQ
- operator FAQ
- decision log appendix

当前阶段，本文档已经足够承担 v1 的统一口径说明职责。
