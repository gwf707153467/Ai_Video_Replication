# Runtime terminal SDK scaffold checklist v1

## 1. 文档定位

本文档是 `runtime_terminal_minimal_sdk_scaffold_note_v1.md` 的配套检查清单。

它面向以下角色：
- Python SDK / adapter 实作者
- worker runtime reporter 封装者
- 需要对 runtime terminal client 做最小收口的维护者
- 代码 review / 自检 / 交接时的检查执行者

它不重写 API contract，不替代 caller integration guide，不替代 snippet pack，也不替代 caller FAQ 或 error mapping appendix。

它的目标只有一个：

> 把“最小 SDK scaffold 应该怎么搭”进一步收敛成一份可逐项打勾的检查表，便于实现、review、验收和后续交接。

---

## 2. 使用方式

建议在以下时点使用本 checklist：
- 第一次落一个 runtime terminal SDK scaffold 时
- 从 snippet 升级为可维护 client 时
- 做 code review 时
- 做版本封板前自检时
- 把 SDK 交给别的团队接手时

推荐执行原则：
- 每一项只回答 `是 / 否 / 不适用`
- 若答案为“否”，优先记录差异原因，而不是现场扩 scope
- 若某项会引入新的业务语义、自动决策或调度能力，默认判定为超出 v1 scaffold 范围

---

## 3. 入口边界检查

### 3.1 terminal 范围是否保持收敛

- [ ] SDK 是否仍只面向 terminal write + snapshot read
- [ ] 是否没有把 terminal client 扩成调度入口
- [ ] 是否没有额外塞入 claim / heartbeat / retry orchestration 能力
- [ ] 是否没有重写现有 complete / fail 写侧语义
- [ ] 是否没有试图改造 422 为新的 terminal contract

### 3.2 对外方法面是否最小

- [ ] public surface 是否至少收敛为 `complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`
- [ ] 是否存在一个统一 request helper，如 `_request(...)`
- [ ] 是否没有因为“未来可能用到”而先暴露大量 endpoint wrapper
- [ ] 是否没有在 v1 就引入泛型资源 client 抽象

---

## 4. 模块结构检查

### 4.1 最小目录骨架

- [ ] 是否至少有 `client.py`
- [ ] 是否至少有 `models.py`
- [ ] 是否至少有 `errors.py`
- [ ] `__init__.py` 是否只做有限导出，而不是重新堆叠实现逻辑

### 4.2 职责分层是否清楚

- [ ] `models.py` 是否主要承载 `RuntimeAttemptContext` 与少量共享结构
- [ ] `errors.py` 是否只负责异常分层
- [ ] `client.py` 是否集中 terminal endpoint 调用
- [ ] 是否没有把请求构造、业务决策、错误映射、排障逻辑揉成一个大文件

---

## 5. attempt context 检查

### 5.1 四元身份字段是否被显式收束

- [ ] 是否存在 `RuntimeAttemptContext`
- [ ] `RuntimeAttemptContext` 是否显式包含 `job_id`
- [ ] `RuntimeAttemptContext` 是否显式包含 `attempt_id`
- [ ] `RuntimeAttemptContext` 是否显式包含 `worker_id`
- [ ] `RuntimeAttemptContext` 是否显式包含 `claim_token`

### 5.2 上下文来源是否保持真实同源

- [ ] SDK 是否要求四元身份字段来自同一次真实 attempt
- [ ] 是否没有在 SDK 内部跨来源拼接四元身份字段
- [ ] 是否没有在 complete / fail 时自动补猜缺失字段
- [ ] complete / fail 是否共用同一类 attempt context，而不是各自散落传参

### 5.3 数据对象是否避免被隐式篡改

- [ ] `RuntimeAttemptContext` 是否优先采用不可变结构（如 frozen dataclass）
- [ ] 是否没有在调用过程中修改 caller 传入的 context
- [ ] 是否没有把旧 context 缓存在 SDK 内并在后续调用中自动复用

---

## 6. request 层检查

### 6.1 `_request(...)` 的职责是否足够小

- [ ] `_request(...)` 是否只负责 HTTP 请求发送
- [ ] 是否在 `_request(...)` 内统一处理 base URL 拼接
- [ ] 是否在 `_request(...)` 内统一处理 timeout
- [ ] 成功时是否返回 JSON body 或等价最小结构
- [ ] 是否在 `_request(...)` 内集中做状态码到异常的映射

### 6.2 `_request(...)` 是否没有越权

- [ ] 是否没有在 `_request(...)` 内自动重试 409
- [ ] 是否没有在 `_request(...)` 内自动读取 snapshot 再替 caller 决策
- [ ] 是否没有在 `_request(...)` 内重写 caller payload
- [ ] 是否没有把 422 压扁成看不出字段错误的模糊异常
- [ ] 是否没有在 `_request(...)` 内偷偷替换 `claim_token`

### 6.3 transport 层失败是否可区分

- [ ] 网络连接失败是否可以与 HTTP 404 / 409 / 422 / 5xx 区分
- [ ] 超时是否不会被错误地混同为业务冲突
- [ ] SDK 是否保留 transport error 这一层概念或等价能力

---

## 7. public method 检查

### 7.1 `complete_job(...)`

- [ ] `complete_job(...)` 是否显式接收 `RuntimeAttemptContext`
- [ ] 是否由 caller 显式提供成功所需关键字段（如 `result_ref`）
- [ ] 是否没有在 SDK 内替 caller 猜 `manifest_artifact_id`
- [ ] 是否没有把 `completion_status` 和 `job_status` 混为一谈
- [ ] 是否没有在成功分支里隐式触发额外业务动作

### 7.2 `fail_job(...)`

- [ ] `fail_job(...)` 是否显式接收 `RuntimeAttemptContext`
- [ ] `next_job_status` 是否由 caller 显式提供
- [ ] `attempt_terminal_status` 是否由 caller 显式提供
- [ ] `terminal_reason / error_code / error_message` 是否由 caller 显式提供
- [ ] `expire_lease` 是否由 caller 显式决定
- [ ] 是否没有在 SDK 内自动把某类 complete 改写成 fail
- [ ] 是否没有在 SDK 内自动推导 WAITING_RETRY / FAILED / STALE 等业务分支
- [ ] caller 未提供 `error_payload_json` 时，是否可以省略该字段而不是显式传 `null`

### 7.3 `get_job_snapshot(...)`

- [ ] `get_job_snapshot(...)` 是否保持为一个独立且显式的方法
- [ ] 是否只要求最小必要输入（如 `job_id`）
- [ ] 是否没有被包装成每次 complete / fail 后必然自动触发的隐式流程
- [ ] 是否没有被误实现为调度器或纠错器

---

## 8. 异常分层检查

### 8.1 最小异常树是否存在

- [ ] 是否存在统一基类（如 `RuntimeTerminalError`）
- [ ] 是否存在 404 对应异常（如 `RuntimeTerminalNotFoundError`）
- [ ] 是否存在 409 对应异常（如 `RuntimeTerminalConflictError`）
- [ ] 是否存在 422 对应异常（如 `RuntimeTerminalValidationError`）
- [ ] 是否存在 5xx 对应异常（如 `RuntimeTerminalServerError`）
- [ ] 是否保留 transport error 概念（可选但推荐）

### 8.2 错误语义是否保持清楚

- [ ] 404 是否仍表示对象不存在或标识错误
- [ ] 409 是否仍优先表示状态/上下文冲突
- [ ] 422 是否仍优先表示 caller / SDK payload 构造错误
- [ ] 5xx 是否仍更接近服务端或基础设施异常
- [ ] 是否没有把所有失败都包成一个无法区分的大异常

### 8.3 错误处理是否没有过度聪明

- [ ] 是否没有默认自动重试 409
- [ ] 是否没有在 422 时自动吞错后重构 payload 再重发
- [ ] 是否没有在 404 时自动猜测其他 job_id / attempt_id
- [ ] 是否把分支判断权保留给 caller

---

## 9. 参数表达与 payload 检查

### 9.1 参数是否尽量显式

- [ ] public method 的关键参数是否尽量显式命名
- [ ] 是否没有靠隐式全局状态补足 terminal 请求
- [ ] 是否没有在 SDK 内部偷偷推导业务字段
- [ ] 是否没有将多个语义不同的字段折叠成一个模糊 `status`

### 9.2 payload 构造是否符合 v1 原则

- [ ] complete payload 是否显式包含四元身份字段
- [ ] fail payload 是否显式包含四元身份字段
- [ ] fail payload 的失败语义字段是否来自 caller 显式决策
- [ ] 是否没有混淆 `completion_status` 与 `job_status`
- [ ] 是否没有为了“统一风格”而硬塞不必要的 null 字段

---

## 10. caller 与 SDK 责任切分检查

### 10.1 caller 责任是否仍在 caller

- [ ] 选择 complete 还是 fail 的决定权是否仍在 caller
- [ ] `next_job_status` 的决定权是否仍在 caller
- [ ] `attempt_terminal_status` 的决定权是否仍在 caller
- [ ] `expire_lease` 的决定权是否仍在 caller
- [ ] complete / fail 成功后是否补 snapshot 核验的决定权是否仍在 caller
- [ ] 409 之后是人工介入、核验 snapshot 还是放弃动作，是否仍由 caller 决定

### 10.2 SDK 是否只做最小封装

- [ ] SDK 是否主要只降低重复样板代码
- [ ] SDK 是否主要只统一错误分类和请求入口
- [ ] 是否没有把 SDK 做成业务语义仲裁器
- [ ] 是否没有把 SDK 做成 workflow engine

---

## 11. 成功后核验能力检查

### 11.1 snapshot 核验能力是否可用

- [ ] SDK 是否提供显式的 snapshot read 能力
- [ ] complete / fail 成功后，caller 是否能够方便地追加 snapshot 核验
- [ ] 核验链路是否能覆盖 job / latest attempt / active lease 三层信息

### 11.2 snapshot 核验能力是否没有越界

- [ ] SDK 是否没有把 snapshot 核验做成每次都自动执行的隐式副作用
- [ ] 是否没有把 snapshot 结果自动解释为新的业务动作
- [ ] 是否没有在 SDK 内根据 snapshot 结果自动再次提交 terminal write

---

## 12. 非目标能力检查

以下能力若已进入 SDK，应默认先问一句：它们是否超出了 v1 scaffold 范围？

- [ ] 自动重试策略编排
- [ ] 幂等键/去重抽象
- [ ] claim / heartbeat / retry 调度能力
- [ ] 自动 snapshot poller
- [ ] 自动 payload 修补
- [ ] 自动枚举转换并改写业务字段
- [ ] 自动 claim_token 刷新
- [ ] sync / async 双栈同时上
- [ ] 复杂 response DTO / serializer 体系
- [ ] 插件注册、middleware 栈、抽象基类系统

若以上任一项被打勾，应补充说明：
- 为什么它不是过度设计
- 为什么它不改变 v1 冻结边界
- 为什么它不会替 caller 做隐式决策

---

## 13. review 结论模板

可在 code review、交接或封板前使用以下最小模板：

```text
[Runtime terminal SDK scaffold review]
- 评审对象：
- 评审版本：
- 评审日期：

一、范围结论
- 是否仍属于 terminal minimal SDK scaffold：是 / 否
- 是否引入超出 v1 的能力：是 / 否

二、关键结论
- attempt context 收束：通过 / 不通过
- request 层边界：通过 / 不通过
- public methods 最小面：通过 / 不通过
- 错误分层：通过 / 不通过
- caller / SDK 责任切分：通过 / 不通过

三、主要问题
- 1.
- 2.
- 3.

四、处理建议
- 维持现状 / 小修后通过 / 需要收缩范围 / 退回重做
```

---

## 14. 一句话结论

如果一份 runtime terminal SDK 实现能够通过这份 checklist，大概率意味着它已经满足 v1 所要求的最小骨架目标：**把 terminal 调用、attempt 上下文和错误分类收束到清晰可维护的 client 中，同时没有越权替 caller 做业务决策。**
