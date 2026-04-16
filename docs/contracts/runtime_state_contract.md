# Runtime State Contract

## 1. 文档目的

本文件定义 `compiled_runtimes` 与 runtime 聚合状态的当前实现契约，作为 smoke、repeatability、审计与后续扩展的统一依据。

本 contract 只描述仓库当前实现事实，不引入未来态设计，不覆盖 provider 细节，不替代 job contract。

---

## 2. 对象范围

runtime contract 主要覆盖以下内容：

- `compiled_runtimes` 表的字段语义
- compile 时 runtime 的创建口径
- dispatch summary 的结构与来源
- runtime 聚合状态如何从 jobs 推导
- runtime 级错误字段的回写规则
- 与 `jobs.payload.runtime_version` 的关联约束

核心实现位置：

- `app/db/models/compiled_runtime.py`
- `app/schemas/compile.py`
- `app/services/runtime_state_service.py`
- `app/compilers/orchestrator/compiler_service.py`
- `app/workers/tasks.py`

---

## 3. Runtime 身份与关联键

### 3.1 主身份

`compiled_runtimes` 的主键是：

- `id`

但在运行态聚合与追踪中，真正的业务关联键是：

- `project_id`
- `runtime_version`

### 3.2 与 jobs 的关联方式

当前实现中，runtime 与 jobs 的关联不是通过外键，而是通过以下条件匹配：

- `Job.project_id == runtime.project_id`
- `Job.payload["runtime_version"].astext == runtime.runtime_version`

这意味着：

1. `jobs.payload.runtime_version` 是 runtime 聚合的事实锚点
2. 若 job payload 未正确写入 `runtime_version`，runtime summary 将失真
3. runtime 级统计默认聚合同一 `project_id + runtime_version` 下的所有 job

---

## 4. 数据模型字段契约

`compiled_runtimes` 当前字段如下：

- `id`
- `project_id`
- `runtime_version`
- `compile_status`
- `runtime_payload`
- `dispatch_status`
- `dispatch_summary`
- `last_error_code`
- `last_error_message`
- `compile_started_at`
- `compile_finished_at`
- `created_at`

字段语义如下。

### 4.1 `runtime_version`

- 类型：`str`
- 作用：同一 project 下的运行版本标识
- 典型值：`v1`、`v2`、`v7`
- 来源：
  - 若 `request.runtime_version` 存在且 `auto_version=False`，使用调用方传入值
  - 否则使用 `RuntimeVersionService.next_version(project_id)` 自动生成

### 4.2 `compile_status`

- 类型：`str`
- 默认模型层初始值：`draft`
- 真实运行中常见值：
  - `compiled`
  - `dispatched`
  - `running`
  - `succeeded`
  - `failed`

语义：

- `compiled`：compile 已完成，但未必派发 job
- `dispatched`：compile 阶段已创建并派发 job（由 compiler service 直接设置）
- `running`：runtime 下存在 active jobs（`queued|dispatched|running`）
- `succeeded`：runtime 下全部 job succeeded
- `failed`：runtime 下任一 job failed

### 4.3 `runtime_payload`

- 类型：`dict / JSONB`
- 作用：存储编译后的 runtime 结构化快照
- 来源：`CompilerService.compile_project()`

当前至少包含：

- `project_id`
- `runtime_version`
- `compile_reason`
- `compile_options`
- `visual_track_count`
- `audio_track_count`
- `bridge_count`
- `sequences`

其中 `sequences[]` 每项至少包含：

- `sequence_id`
- `sequence_index`
- `sequence_type`
- `persuasive_goal`
- `spus[]`
- `vbus[]`
- `bridges[]`

### 4.4 `dispatch_status`

- 类型：`str`
- 默认模型层初始值：`not_dispatched`
- 常见值：
  - `not_dispatched`
  - `partially_dispatched`
  - `fully_dispatched`

语义：

- `not_dispatched`：没有任何 job 到达 dispatched-or-beyond
- `partially_dispatched`：仅部分 job 到达 dispatched-or-beyond
- `fully_dispatched`：全部 job 到达 dispatched-or-beyond

### 4.5 `dispatch_summary`

- 类型：`dict / JSONB`
- 作用：存储 runtime 当前 job 聚合摘要
- 来源：
  - compile 阶段首次写入
  - worker / refresh 阶段由 `RuntimeStateService.build_summary()` 重建并回写

### 4.6 `last_error_code` 与 `last_error_message`

- 类型：可空字符串
- 作用：存储 runtime 级最新失败信号
- 来源：
  - worker 失败路径会先直接写 runtime 错误
  - `refresh_runtime_status()` 会根据 failed jobs 回写 / 清空

### 4.7 `compile_started_at` / `compile_finished_at`

- 由 `CompilerService.compile_project()` 在 runtime 创建时写入
- 当前实现中两者都在 compile 完成当下写入 `datetime.utcnow()`
- 它们表示 compile 记录写入时间窗，不表示整条 runtime 工作流最终结束时间

---

## 5. Runtime 创建契约

当调用 `POST /api/v1/compile` 且校验通过时，会创建一条 runtime。

### 5.1 前置失败条件

- project 不存在：`ValueError("project_not_found")`
- validate 不通过：`ValueError("project_invalid")`

### 5.2 初始写入口径

runtime 创建时，至少写入：

- `project_id`
- `runtime_version`
- `compile_status = "compiled"`
- `runtime_payload = {...}`
- `dispatch_status = "not_dispatched"`
- `dispatch_summary = {}`
- `compile_started_at = datetime.utcnow()`
- `compile_finished_at = datetime.utcnow()`

### 5.3 `dispatch_jobs=false` 情况

若 compile 请求不派发 job：

- runtime 维持 `compile_status = compiled`
- runtime 维持 `dispatch_status = not_dispatched`
- `dispatch_summary` 会写入零计数摘要

该零计数摘要按当前实现至少包含：

- `runtime_version`
- `job_count`
- `queued_job_count`
- `dispatched_job_count`
- `undispatched_job_count`
- `dispatch_status`
- `jobs`

### 5.4 `dispatch_jobs=true` 情况

若 compile 请求派发 job：

- 系统创建 5 条 job
- 派发完成后 runtime 会被直接设置为：
  - `compile_status = dispatched`
  - `dispatch_status = <dispatch summary status>`
  - `dispatch_summary = <创建/派发摘要>`

注意：这里的 `compile_status = dispatched` 不是 `RuntimeStateService.derive_compile_status()` 的返回值，而是 compiler service 在 dispatch 阶段直接写入的中间状态。

---

## 6. Runtime summary 结构契约

`RuntimeStateService.build_summary(db, runtime)` 当前返回结构为：

```json
{
  "runtime_version": "v7",
  "job_count": 5,
  "queued_job_count": 0,
  "dispatched_job_count": 0,
  "running_job_count": 0,
  "succeeded_job_count": 5,
  "failed_job_count": 0,
  "jobs": [
    {
      "job_id": "...",
      "job_type": "render_image",
      "status": "succeeded",
      "attempt_count": 1,
      "max_attempts": 3,
      "external_task_id": "...",
      "error_code": null
    }
  ]
}
```

其中：

- `job_count`：匹配到的 job 总数
- `queued_job_count`：状态为 `queued` 的 job 数
- `dispatched_job_count`：状态为 `dispatched` 的 job 数
- `running_job_count`：状态为 `running` 的 job 数
- `succeeded_job_count`：状态为 `succeeded` 的 job 数
- `failed_job_count`：状态为 `failed` 的 job 数
- `jobs[]`：按 `created_at asc` 排序后的轻量 job 摘要

当前 summary 不包含：

- `undispatched_job_count`
- `last_error_message`
- asset 统计
- provider 维度统计

因此 compile 阶段生成的初始 dispatch summary 与 runtime refresh 阶段生成的聚合 summary，在字段集合上可能并不完全一致。审计时必须区分“compiler 初始摘要”和“runtime 聚合摘要”。

---

## 7. 状态推导规则

### 7.1 `derive_compile_status(summary, current_status)`

当前规则：

1. `job_count == 0` → 保持 `current_status`
2. `failed_job_count > 0` → `failed`
3. `succeeded_job_count == job_count` → `succeeded`
4. 存在 active jobs（`queued + dispatched + running > 0`）→ `running`
5. 否则保持 `current_status`

### 7.2 `derive_dispatch_status(summary, current_status)`

当前规则：

1. `job_count == 0` → 保持 `current_status`
2. `dispatched_or_beyond == 0` → `not_dispatched`
3. `dispatched_or_beyond < job_count` → `partially_dispatched`
4. `dispatched_or_beyond == job_count` → `fully_dispatched`

其中 `dispatched_or_beyond` 定义为：

- `dispatched_job_count`
- `running_job_count`
- `succeeded_job_count`
- `failed_job_count`

之和。

### 7.3 语义重点

这意味着：

- 只要 job 已进入 `failed`，也被视作“已 dispatch”
- `dispatch_status` 只衡量派发覆盖度，不衡量执行成功率
- `compile_status` 才反映 runtime 成败

---

## 8. refresh 回写契约

`RuntimeStateService.refresh_runtime_status(db, runtime)` 当前回写逻辑：

1. 根据 `project_id + runtime_version` 重建 summary
2. 用该 summary 覆盖 `runtime.dispatch_summary`
3. 推导并回写 `runtime.dispatch_status`
4. 推导并回写 `runtime.compile_status`
5. 若存在 failed jobs：
   - 取 summary 中最后一个 failed job
   - 用其 `error_code` 回写 `runtime.last_error_code`
6. 若不存在 failed jobs 且 runtime 非 `failed`：
   - 清空 `runtime.last_error_code`
   - 清空 `runtime.last_error_message`

注意：

- `refresh_runtime_status()` 只直接同步 `last_error_code`
- `last_error_message` 的清空规则存在，但失败时不会从 failed job 自动补写 message
- runtime message 往往来自 worker 失败路径先行写入，而不是 summary 聚合结果

---

## 9. Worker 对 runtime 的影响

### 9.1 运行开始时

`_run_job(...)` 在 job 真正执行前会：

- 将 job 标记为 `running`
- 将 runtime `compile_status` 直接置为 `running`
- 清空 runtime 级错误字段

### 9.2 运行成功时

worker 成功后会：

- job 标记为 `succeeded`
- 调 `refresh_runtime_status()`
- runtime 由 summary 推导到：
  - 仍是 `running`，或
  - 最终成为 `succeeded`

### 9.3 运行失败时

worker 失败路径会：

- job 标记为 `failed`
- job `error_code = worker_execution_failed`
- runtime 直接写：
  - `compile_status = failed`
  - `last_error_code = worker_execution_failed`
  - `last_error_message = str(exc)`
- 然后再调 `refresh_runtime_status()`

因此失败态是“双写入”机制：

- 先由 worker 显式写 runtime 失败
- 再由 runtime summary 聚合完成最终状态归整

---

## 10. 稳定性与审计注意事项

### 10.1 contract 依赖 JSON payload 关联

因为 runtime 聚合依赖 `jobs.payload.runtime_version`，所以以下情况会破坏 contract：

- job payload 缺少 `runtime_version`
- payload 中 runtime_version 值写错
- 后续手工更改 payload JSON

### 10.2 `dispatch_status` 不代表成功

以下状态组合是合法的：

- `dispatch_status = fully_dispatched`
- `compile_status = failed`

这表示所有 job 都被成功派发，但至少一个执行失败。

### 10.3 初始 dispatch summary 与刷新后 summary 结构不同

compile 时写入的 dispatch summary 偏创建/派发表达；
refresh 后写入的 dispatch summary 偏运行聚合表达。

因此外部调用方若要做长期兼容，应优先依赖以下稳定键：

- `runtime_version`
- `job_count`
- `queued_job_count`
- `dispatched_job_count`
- `running_job_count`
- `succeeded_job_count`
- `failed_job_count`
- `jobs`

---

## 11. 当前冻结成功样本

已验证成功样本：

- `project_id = 656ac6b1-ecb8-4f45-9f45-556be5915168`
- `runtime_version = v7`
- `runtime_id = 9c5a8e97-924a-475e-91a1-c3db0a60571b`

最终状态：

- `compile_status = succeeded`
- `dispatch_status = fully_dispatched`
- `dispatch_summary.job_count = 5`
- `dispatch_summary.succeeded_job_count = 5`
- `dispatch_summary.failed_job_count = 0`

该样本可作为 smoke / repeatability 的 runtime contract 验收锚点。

---

## 12. 对外使用建议

若后续要在控制平面、审计面板或 repeatability report 中消费 runtime 数据，建议按以下优先级读取：

1. 先读 `compile_status` 判断成败
2. 再读 `dispatch_status` 判断派发覆盖度
3. 再读 `dispatch_summary` 获取 job 分布
4. 若 `compile_status = failed`，优先读：
   - `last_error_code`
   - `last_error_message`
5. 需要 drill-down 时，再到 `jobs` / `assets` 表做明细追踪

该 contract 冻结于当前仓库实现；如后续修改 summary 字段集、runtime-job 关联方式或错误回写策略，必须同步更新本文件。
