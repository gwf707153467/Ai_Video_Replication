# Runtime terminal SDK README handoff note v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK README / handoff note**。

它服务于一个更窄、更实际的问题：

> 当团队已经确定 runtime terminal v1 只做最小 SDK 封装时，README 应该如何写、交接包应该如何组织，才能让下游调用方快速接入，同时不把 README 写成新的平台设计文档。

本文档与以下材料配套使用：
- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`

本文档不重定义 API contract，不重开 complete / fail / snapshot 语义，也不替代 exception / packaging note。它只负责把“**怎么对外说明这个最小 SDK**”和“**交接时最少要带什么**”固定下来。

---

## 2. 这份 note 要解决什么问题

runtime terminal v1 的 SDK 已经完成了最小边界冻结：
- terminal = terminal write + snapshot read
- SDK 只做最小 client 封装
- 不做业务仲裁
- 不自动 retry 409
- 不自动修补 payload
- 不自动替换 `claim_token`

真正容易在交接时出问题的，通常不是代码本身，而是 README 写偏了。常见问题包括：
- 把 terminal client 写成“统一 runtime 平台 SDK”
- 把 README 写成功能宣传页，却没有明确边界
- 只放代码片段，不说 409 / 422 / 5xx 的责任归属
- 只说怎么 `complete` / `fail`，不提醒成功后建议做 snapshot 核验
- 没有告诉接手人：哪些文档该先看，哪些问题不要在 README 里重开

因此，这份 note 的目的不是扩展能力，而是固定 README 与 handoff 的表达纪律。

一句话概括：

> **README 应帮助下游正确使用最小 SDK，而不是诱导他们误解它的能力边界。**

---

## 3. README 必须重复强调的固定结论

无论 README 长短如何，以下结论都建议在首页或前两屏中明确出现。

### 3.1 范围定义
- runtime terminal v1 只覆盖 terminal write + snapshot read
- 最小 public methods 只围绕：`complete_job(...)`、`fail_job(...)`、`get_job_snapshot(...)`
- 这不是 claim / heartbeat / retry orchestration SDK
- 这不是统一 runtime platform SDK

### 3.2 责任边界
- SDK 只负责最小请求封装、基础错误分层和稳定导出面
- SDK 不替 caller 隐式决定业务语义
- 调用方必须自己保证 `job_id / attempt_id / worker_id / claim_token` 来自同一次真实 attempt
- `completion_status` 不等于 `job_status`

### 3.3 错误处理口径
- 409 优先视为状态或上下文冲突，不默认自动重试
- 422 优先视为 caller / SDK payload 构造错误
- 404 优先视为对象不存在或标识错误
- 5xx 更接近服务端或基础设施异常，可有限重试
- transport error 与 HTTP 语义错误应分离理解

### 3.4 成功后建议
- `complete` / `fail` 成功后，建议显式做一次 snapshot 核验
- README 应提醒调用方不要把“写入成功”直接等同于“业务状态已按预期消费”

---

## 4. 推荐 README 最小结构

建议 README 控制在“快速理解 + 正确接入 + 不误解边界”的长度，不要演变成第二份 architecture note。

推荐最小结构如下：

```text
1. What this package is
2. What this package is not
3. Public surface
4. Quick start
5. Error handling
6. Boundary / non-goals
7. Related docs
8. Handoff notes
```

下面给出每一段建议承载的内容。

### 4.1 What this package is

建议用 2 到 4 句话说明：
- 这是 runtime terminal v1 的最小 SDK / client
- 它封装 terminal complete、terminal fail 和 snapshot read
- 它面向 worker reporter、adapter、轻量调用方集成
- 它优先追求最小、稳定、可复用、可交接

### 4.2 What this package is not

这段非常关键，建议显式写出：
- 不是调度入口
- 不是任务领取客户端
- 不是 heartbeat 管理器
- 不是自动重试编排器
- 不是业务状态仲裁器
- 不是“大一统 runtime SDK”

### 4.3 Public surface

README 里只展示稳定公共概念，不要暴露过多内部实现。

建议列出：
- `RuntimeTerminalClient`
- `RuntimeAttemptContext`
- 最小异常树

并简要说明：
- `RuntimeAttemptContext` 用于收束同一次 attempt 的四元身份字段
- `RuntimeTerminalClient` 负责最小写入与读取动作
- 异常树用于区分 not found / conflict / validation / server / transport 场景

### 4.4 Quick start

建议给一个最小可复制示例，只展示：
- 初始化 client
- 构造 `RuntimeAttemptContext`
- 调用 `complete_job(...)` 或 `fail_job(...)`
- 再调用 `get_job_snapshot(...)`

Quick start 的目标不是覆盖所有参数，而是传达一个默认实践：

> **写 terminal 后，再做 snapshot 核验。**

### 4.5 Error handling

README 里不要把错误处理写得过于复杂，但至少应保留：
- 409 不应被默认当成“网络抖动可重试”
- 422 更像接入层构造错误，应先修调用方或 SDK payload 生成逻辑
- 5xx / transport 才更接近有限重试候选

如果篇幅有限，这一节可以只放一张简表，然后链接到：
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_language_specific_error_mapping_appendix_v1.md`

### 4.6 Boundary / non-goals

建议把非目标单独成段，防止使用者误以为“README 没写，只是还没实现”。

建议明确列出：
- 不提供 sync / async 双栈
- 不内置 claim / heartbeat / retry orchestration
- 不自动修补 payload
- 不自动替换 `claim_token`
- 不对 FastAPI / Pydantic 默认 422 做二次语义包装
- 不提供复杂 DTO / plugin / middleware 体系

### 4.7 Related docs

README 不应独自承担全部说明责任。

建议固定挂出以下材料：
- docs index：从哪份文档开始读
- usage snippet：快速改造接入
- scaffold note：最小 SDK 骨架
- exception note：错误分层口径
- packaging note：目录与导出边界
- caller FAQ：常见误解

### 4.8 Handoff notes

如果 README 会用于仓内交接或交付，建议最后保留一个 handoff 段，说明：
- 当前 v1 冻结边界是什么
- 后续增量应该优先补文档还是补代码
- 哪些问题不要在接手时重新发散设计

---

## 5. 推荐 README 首页模板口径

下面是一段可直接复用或轻改的 README 首页口径。

### 5.1 一句话简介

> A minimal SDK for runtime terminal v1 terminal writes and snapshot reads.

### 5.2 中文说明版

> 这是 runtime terminal v1 的最小 SDK，用于封装 terminal complete、terminal fail 与 job snapshot read。它强调最小、稳定、可复用、可交接；不扩展为 claim、heartbeat、retry orchestration 或统一 runtime 平台框架。

### 5.3 首页警示语

建议在 README 靠前位置重复以下事实：
- terminal = terminal write + snapshot read
- SDK 不做业务仲裁
- SDK 不自动 retry 409
- SDK 不自动修补 payload
- SDK 不自动替换 `claim_token`

如果只能保留一条最重要的接入提醒，建议保留：

> **请确保 `job_id / attempt_id / worker_id / claim_token` 来自同一次真实 attempt。**

---

## 6. 推荐交接包最小组成

如果要把 runtime terminal SDK 作为一个可交接成果移交给下游团队，建议最少包含以下内容。

### 6.1 代码侧
- `client.py`
- `models.py`
- `errors.py`
- `__init__.py`

### 6.2 文档侧
- `README.md` 或等价 handoff readme
- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`

### 6.3 可选但推荐
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_caller_faq_v1.md`
- `runtime_terminal_language_specific_error_mapping_appendix_v1.md`

### 6.4 为什么不建议只交 README

只交 README 往往会带来两个问题：
- 接手人不知道哪些结论是 README 摘要、哪些是已冻结规则
- 接手人会把 README 没展开的地方重新当成开放设计问题

因此更合理的 handoff 方式是：

> **README 负责快速进入，docs index 负责导航，exception / packaging / scaffold 文档负责冻结细节。**

---

## 7. README 里建议出现的最小示例要点

README 示例建议体现以下顺序，而不是只贴一段请求代码：

1. 准备 base URL 和认证方式
2. 构造 `RuntimeAttemptContext`
3. 发起 `complete_job(...)` 或 `fail_job(...)`
4. 对结果做基础异常处理
5. 再调用 `get_job_snapshot(...)` 做核验

如果 README 只能留一个默认流程图，建议表达为：

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

这样能帮助使用者理解：
- terminal SDK 不是“调完即结束”
- snapshot read 是推荐闭环的一部分
- 成功后的校验责任仍然在调用方

---

## 8. README 不要写成什么样

以下是应主动避免的 README 失真写法。

### 8.1 不要把范围写大

不建议使用类似表述：
- “统一 runtime worker SDK”
- “任务执行全流程管理客户端”
- “内置失败恢复与自动重试能力”
- “完整运行时编排抽象层”

这些表述会直接破坏 v1 冻结边界。

### 8.2 不要制造隐式承诺

README 不应暗示：
- 409 一定会被自动恢复
- claim token 过期会被 SDK 自动修复
- payload 填错字段也会被 SDK 自动矫正
- 只要返回成功就无需 snapshot 核验

### 8.3 不要把内部实现当成外部 contract

README 不建议大量暴露：
- 内部 `_request(...)` 实现
- 非稳定 helper
- 暂时性的 payload builder
- 为仓内便利加入的实验性模块

README 的职责是稳定对外表达，而不是记录全部内部细节。

---

## 9. 交接时建议附带的 reviewer / receiver 检查点

交接 README 或 SDK 包时，建议接收方快速检查以下问题：

### 9.1 边界是否说清
- 是否明确写出 terminal = terminal write + snapshot read
- 是否明确写出不包含 claim / heartbeat / retry orchestration
- 是否明确写出 SDK 不做业务仲裁

### 9.2 public surface 是否说清
- 是否只强调 `RuntimeTerminalClient`、`RuntimeAttemptContext` 与最小异常树
- 是否避免把内部 helper 公开成使用主路径

### 9.3 错误处理是否说清
- 是否明确 409 / 422 / 404 / 5xx / transport 的基本分层
- 是否明确 409 不默认自动重试
- 是否明确 422 更像 payload / caller 构造问题

### 9.4 推荐闭环是否说清
- 是否提醒 complete / fail 成功后建议做 snapshot 核验
- 是否明确“请求成功”不等于“业务侧已完全达成预期”

### 9.5 文档导航是否说清
- 是否提供 docs index
- 是否链接 exception / packaging / scaffold 相关文档
- 是否让接手人知道：哪些结论已经冻结、哪些仍可后续增量补充

---

## 10. 与现有文档的分工关系

这份 README handoff note 与现有文档的职责分工建议如下：

- `runtime_terminal_sdk_docs_index_v1.md`
  - 负责作为 SDK 文档总入口
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
  - 负责“怎么调”的最短路径
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
  - 负责“最小骨架怎么收束”
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
  - 负责“实现/评审时怎么打勾”
- `runtime_terminal_sdk_exception_contract_note_v1.md`
  - 负责“错误分类与责任边界”
- `runtime_terminal_sdk_packaging_note_v1.md`
  - 负责“包结构与导出边界”
- 本文档
  - 负责“README 应如何表达，以及 handoff 最少应怎么交”

因此，本文档的角色不是再造一份总设计，而是把“**对外说明**”与“**交接动作**”单独冻结下来。

---

## 11. 当前阶段最自然的使用方式

在当前 v1 冻结阶段，更推荐这样使用本文档：

- 当需要补仓内 SDK README 时，用本文档作为口径模板
- 当需要把 SDK 交接给其他 worker / service 团队时，用本文档校验 README 是否越界
- 当 reviewer 判断“这个 README 是否把 SDK 写大了”时，用本文档做边界对照

如果后续继续增量，最自然的方向不是重写本文档，而是基于它补充更具体的交付物，例如：
- `runtime_terminal_sdk_readme_template_v1.md`
- `runtime_terminal_sdk_handoff_checklist_v1.md`
- `runtime_terminal_sdk_private_package_release_note_v1.md`

这些都应建立在当前固定口径之上，而不是重新打开 v1 范围设计。
