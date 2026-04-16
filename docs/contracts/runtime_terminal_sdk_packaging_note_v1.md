# Runtime terminal SDK packaging note v1

## 1. 文档定位

本文档是 runtime terminal v1 的 **SDK packaging note**。

它面向以下角色：
- 准备把 snippet 升级成可复用 SDK 包的开发者
- 需要把 runtime terminal client 内部发布给多个 worker / service 复用的平台维护者
- 做仓内封装、目录整理、导出面控制、版本交接的维护者
- 做 code review / 自检 / 交接验收的负责人

它与以下材料配套使用：
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_package_index_v1.md`

它不重新定义 API contract，不替代 exception contract note，也不讨论完整发布流水线、PyPI 发布策略或多语言包生态。

它只解决一个更窄的问题：

> 在 runtime terminal v1 冻结边界下，一个最小、可维护、可交接的 SDK 包应该如何组织，才能既方便复用，又不把 terminal client 过度工程化。

本文档严格遵守当前 v1 冻结边界：
- terminal = terminal write + snapshot read，不是调度入口
- 不重开 `complete / fail / snapshot` 语义
- 不把 SDK 扩成 workflow engine
- 不把 422 包装成新的 terminal error schema
- 不引入 claim / heartbeat / retry orchestration 能力

---

## 2. 这份 packaging note 要解决什么问题

当团队决定把 snippet 收束成 SDK 时，最容易失控的不是“能不能调通”，而是“包会不会越做越大”。

常见失控路径包括：
- 一开始只有 terminal client，随后被塞进 claim、heartbeat、retry、scheduler 入口
- `__init__.py` 越堆越厚，最后变成重新拼装实现逻辑的总入口
- models、errors、request helper、业务决策都揉进一个文件
- 为了“以后可能需要”先做 sync / async 双栈
- 引入复杂 response DTO、插件系统、middleware 栈，但 v1 实际并不需要
- 对外导出面太宽，导致后续内部重构难以进行

因此，这份 note 的目标不是教“怎么发版”，而是冻结下面这件事：

> **runtime terminal v1 的 SDK 包应优先服务于最小复用与长期维护，而不是预支未来复杂性。**

---

## 3. 先给固定结论

runtime terminal v1 的 SDK packaging，建议固定为以下 10 条：

1. 包结构应最小化，优先维持 `client.py / models.py / errors.py / __init__.py` 四件套。
2. public surface 应尽量收敛到 `RuntimeTerminalClient`、`RuntimeAttemptContext` 和最小异常树。
3. `__init__.py` 只做有限导出，不承担实现编排逻辑。
4. request helper 应留在 `client.py` 内部，不必过早抽成通用 HTTP 框架。
5. package 的命名、目录、导出面应围绕 terminal write + snapshot read，而不是围绕“未来可能扩的 runtime platform”。
6. 不要在 v1 同时上 sync / async 双栈。
7. 不要因为“发布包”就强行引入复杂 DTO、serializer、插件系统或 middleware 栈。
8. 版本说明、README、示例代码都应重复强调：SDK 不做业务仲裁，不自动 retry 409，不自动修补 payload。
9. 若先做仓内私有包，也应保持之后可平滑抽离的结构，而不是把 repo 内部耦合直接暴露给调用方。
10. packaging 的目标是降低复用成本与维护摩擦，不是制造新的抽象层级。

一句话总结：

> **v1 SDK 包应该像一个边界清晰的小 client，而不是一个提前膨胀的平台框架。**

---

## 4. 推荐最小包结构

推荐目录骨架：

```text
runtime_terminal_sdk/
├── __init__.py
├── client.py
├── models.py
└── errors.py
```

各文件建议职责如下：

### 4.1 `client.py`

负责：
- `RuntimeTerminalClient`
- `_request(...)`
- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`

不负责：
- 复杂业务编排
- 自动 snapshot poller
- claim / heartbeat / retry orchestration
- 大型响应模型体系

### 4.2 `models.py`

负责：
- `RuntimeAttemptContext`
- 少量共享输入/输出辅助结构（如确有必要）

不负责：
- 把所有 API response 都包装成复杂 DTO
- 内嵌业务状态机

### 4.3 `errors.py`

负责：
- `RuntimeTerminalError`
- `RuntimeTerminalNotFoundError`
- `RuntimeTerminalConflictError`
- `RuntimeTerminalValidationError`
- `RuntimeTerminalServerError`
- `RuntimeTerminalTransportError`（可选但推荐）

不负责：
- 错误恢复逻辑
- 自动重试策略
- 面向日志平台的复杂格式编排

### 4.4 `__init__.py`

负责：
- 对外有限导出最小 public surface

不负责：
- 拼接实现细节
- 重新包装入口
- 引入全局单例、隐式配置、环境探测逻辑

---

## 5. 推荐对外导出面

一个克制的 `__init__.py` 示意：

```python
from .client import RuntimeTerminalClient
from .errors import (
    RuntimeTerminalConflictError,
    RuntimeTerminalError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)
from .models import RuntimeAttemptContext

__all__ = [
    "RuntimeAttemptContext",
    "RuntimeTerminalClient",
    "RuntimeTerminalConflictError",
    "RuntimeTerminalError",
    "RuntimeTerminalNotFoundError",
    "RuntimeTerminalServerError",
    "RuntimeTerminalTransportError",
    "RuntimeTerminalValidationError",
]
```

这个导出面的优点是：
- 调用方拿到的都是 v1 真正稳定的概念
- 内部 helper、payload 拼装细节、session 初始化方式仍可重构
- 交接时不容易把内部实现误当成长期 contract

建议不要对外导出：
- `_request(...)`
- 内部 payload builder
- 实验性 serializer / parser
- 与 terminal 无关的通用工具函数

---

## 6. package 命名与边界建议

## 6.1 命名应该贴近 terminal 范围

推荐命名倾向：
- `runtime_terminal_sdk`
- `runtime_terminal_client`
- `runtime_terminal_adapter`

不推荐一开始就命名成过大概念，如：
- `runtime_platform_sdk`
- `worker_orchestration_sdk`
- `runtime_engine`

因为 v1 的真实边界仍然只有：
- terminal complete write
- terminal fail write
- terminal snapshot read

命名过大，往往会诱导后续把本不属于 v1 的能力塞进来。

## 6.2 包边界应与职责边界一致

如果当前只是给 worker / executor 统一 terminal reporter，建议包边界就停在这里。

不要顺手并入：
- claim client
- heartbeat reporter
- retry scheduler
- job dispatcher
- workflow state resolver

如果未来要扩，也应优先新增相邻模块或新包，而不是污染当前 v1 terminal SDK 包。

---

## 7. 版本与发布形态建议

## 7.1 v1 更适合先做仓内稳定包

如果当前工作重点仍是 repo 内部多个调用方复用，建议先采用：
- 仓内明确目录
- 明确导出面
- 明确最小 README / usage note
- 明确与 repo 其他模块的依赖边界

这通常比一开始就追求完整对外发布更稳妥。

## 7.2 若后续要独立发布，应优先保证可抽离性

即使暂时不做 PyPI 或外部分发，也建议提前注意：
- 不要把 repo 内部路径常量硬编码进 public API
- 不要依赖调用方必须感知仓内私有模块结构
- 不要让 SDK 的 import 链深度耦合到业务项目其他子系统
- 尽量让 `client.py / models.py / errors.py` 自身可以独立存在

这会让后续“从 repo 内私有包抽成独立包”更平滑。

## 7.3 不必提前设计复杂版本兼容层

v1 阶段通常不需要：
- 多版本 API 自动探测
- capability negotiation
- 复杂 compatibility matrix

如果 API contract 当前已冻结，SDK 包的职责就是稳定表达它，而不是提前为未知未来建立庞大兼容系统。

---

## 8. 依赖与实现克制度建议

## 8.1 HTTP 客户端依赖保持克制

v1 选择一个主 HTTP 客户端即可，例如：
- `requests`
- 或 `httpx`（若团队统一）

不建议为了“兼容大家偏好”同时支持：
- requests + httpx + aiohttp 多套实现

因为这会立刻把最小 SDK 变成多后端适配层。

## 8.2 数据模型依赖保持克制

如果 `RuntimeAttemptContext` 用 `dataclass(frozen=True)` 已足够，就不需要为了包装而额外引入复杂模型系统。

同理，response 若当前只需 `dict[str, Any]` 或少量轻量结构，也不必强行上完整 DTO 树。

## 8.3 日志 / 追踪增强作为增强项，而不是 v1 必需项

可以预留：
- 注入 logger
- 注入 trace id
- 自定义 headers

但这些更适合作为可选增强，不应改变 SDK 的最小主干结构。

---

## 9. README / 使用说明应明确什么

如果这个 SDK 包要交给其他团队或未来自己复用，建议 README 或同级说明至少写清楚以下几点：

1. **它只覆盖什么**
   - complete
   - fail
   - snapshot

2. **它明确不覆盖什么**
   - claim
   - heartbeat
   - retry orchestration
   - workflow scheduling

3. **它的最小 public surface**
   - `RuntimeAttemptContext`
   - `RuntimeTerminalClient`
   - 最小异常树

4. **它的固定实践建议**
   - 409 不默认自动重试
   - 422 视为 payload 构造错误
   - 成功后可由 caller 追加 snapshot 核验
   - 四元身份字段必须来自同一次真实 attempt

5. **它的非目标**
   - 不做业务仲裁
   - 不做自动 payload 修补
   - 不做自动 claim_token 刷新

如果 README 没写清楚这些边界，后续调用方很容易误把 SDK 当成“智能终态处理器”。

---

## 10. code review 时应重点看什么

review 一个 runtime terminal SDK 包时，建议优先检查以下问题：

### 10.1 包结构是否仍然最小

- 是否仍是 `client.py / models.py / errors.py / __init__.py` 为主
- 是否没有把大量无关能力揉进来

### 10.2 对外导出是否过宽

- 是否只导出稳定概念
- 是否把内部 helper、内部 payload builder、内部 session 工厂也暴露了

### 10.3 文件职责是否清楚

- client 只管请求与 endpoint 方法
- models 只管 context 与少量结构
- errors 只管异常层
- `__init__.py` 只管导出

### 10.4 是否出现过度设计信号

例如：
- sync / async 双栈并存
- 自动插件注册
- middleware 栈
- 泛型资源客户端
- 复杂 serializer 层
- capability negotiation
- 自动 snapshot poller

这些若在 v1 就出现，应默认追问：
- 它是否真的服务于当前 terminal 范围
- 它是否改变了最小骨架目标
- 它是否提高了维护成本而非降低成本

---

## 11. 反模式清单

以下包装方式，默认应视为偏离 v1 packaging 原则：

1. **把 terminal SDK 做成“大一统 runtime 平台 SDK”**
   - 结果：职责失焦，边界不断膨胀。

2. **`__init__.py` 里堆实现逻辑**
   - 结果：导出层和实现层纠缠，重构困难。

3. **内部实现细节大量外露**
   - 结果：public surface 不受控，未来难以演进。

4. **一开始就上 sync / async 双栈**
   - 结果：测试、维护、文档成本翻倍。

5. **为了“专业感”引入复杂 DTO / plugin / middleware 体系**
   - 结果：接入成本上升，但对 v1 价值有限。

6. **把错误恢复、业务判断、调度能力封进包里**
   - 结果：SDK 越权，caller 失去明确控制。

7. **对 repo 内私有依赖耦合过深**
   - 结果：后续难以抽离、复用或独立交付。

---

## 12. 一句话结论

如果一个 runtime terminal SDK 包能把目录结构、导出面、职责边界、依赖选择和说明文档都控制在“最小但稳定”的范围内，不把 terminal client 膨胀成调度框架或平台底座，那么它基本就满足了 v1 packaging 的目标：

> **让 SDK 成为一个可复用、可交接、可渐进演进的小包，而不是一个提前过度设计的大系统。**
