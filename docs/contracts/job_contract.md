# Job Contract

## 1. 文档目的

本文件定义当前实现中 `jobs` 表、compile 派发、worker 生命周期、runtime 关联与产物物化的事实契约。

本 contract 只描述当前仓库已实现的 job 行为，不扩展重试编排、不引入未来态调度器设计，也不重开 provider 主链路讨论。

---

## 2. 适用范围

本 contract 覆盖以下对象与流程：

- `jobs` 表字段与默认值
- compile 阶段的 job 创建与 dispatch 规则
- worker 执行期间的 job 状态流转
- job 与 runtime 的关联方式
- job 成功 / 失败时的 `result_payload` 约定
- 带 `asset_plan` 的 job 如何注册与物化 asset

核心实现位置：

- `app/db/models/job.py`
- `app/compilers/orchestrator/compiler_service.py`
- `app/workers/tasks.py`
- `app/services/runtime_state_service.py`
- `app/services/asset_policy_service.py`

---

## 3. 数据模型字段契约

`jobs` 表当前字段如下：

- `id`
- `project_id`
- `job_type`
- `status`
- `provider_name`
- `payload`
- `result_payload`
- `attempt_count`
- `max_attempts`
- `external_task_id`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`

当前 schema 与代码事实中，**不存在** 以下列：

- `last_error_code`
- `runtime_version`

其中 `runtime_version` 不是 jobs 表列，而是写在 `payload.runtime_version` 中。

### 3.1 默认值

模型层默认值：

- `status = "queued"`
- `attempt_count = 0`
- `max_attempts = 3`
- `payload = {}`

### 3.2 字段语义

#### `job_type`

当前 compile 主链路固定创建 5 类 job：

- `compile`
- `render_image`
- `render_video`
- `render_voice`
- `merge`

#### `status`

当前实现中出现的关键状态：

- `queued`
- `dispatched`
- `running`
- `succeeded`
- `failed`

语义：

- `queued`：job 已创建，但 dispatch 未拿到 task id
- `dispatched`：已拿到 Celery task id，等待 worker 执行
- `running`：worker 已接单并开始执行
- `succeeded`：worker 执行成功并已提交结果
- `failed`：worker 执行失败，且错误信息已落库

#### `provider_name`

- 可空
- 当前 compile 创建 job 时不主动写入
- 运行结果中的 provider 细节主要体现在 `result_payload` 内，而不是此字段的强约束

#### `payload`

- 类型：`JSONB`
- 是 job 的事实输入载体
- runtime 聚合依赖其内的 `runtime_version`

当前 compile 阶段所有 job 的基础 payload 至少包含：

- `runtime_version`
- `dispatch_source = "compile_endpoint"`

其中 `render_image` 额外包含：

- `prompt`
- `negative_prompt`
- `provider_inputs`

`provider_inputs` 当前固定至少含：

- `prompt`
- `negative_prompt`
- `sample_count = 1`
- `aspect_ratio = "9:16"`
- `source = "compiler_minimal_render_image_prompt_v1"`
- `runtime_version`

#### `result_payload`

- 类型：可空 `JSONB`
- 生命周期中会被多次改写
- 典型阶段：
  - dispatch 后写入 `{ "celery_task_id": task_id }`
  - running 时补充 `task` 与 `worker_started_at`
  - succeeded 时整体替换为最终成功 payload
  - failed 时在现有基础上补充错误字段

#### `external_task_id`

- 保存 dispatch 成功返回的 task id
- 若为空，表示未成功派发至异步执行队列

#### `error_code` / `error_message`

- 仅在失败路径下有值
- 当前 worker 执行失败的固定错误码为：`worker_execution_failed`

#### `started_at` / `finished_at`

- `started_at` 在 `_mark_job_running()` 写入
- `finished_at` 在 `_mark_job_succeeded()` / `_mark_job_failed()` 写入

---

## 4. Job 与 runtime 的关联契约

当前实现中，job 不通过外键直接挂到 runtime，而是通过以下双键关联：

- `Job.project_id`
- `Job.payload.runtime_version`

runtime summary 查询条件为：

- `Job.project_id == runtime.project_id`
- `Job.payload["runtime_version"].astext == runtime.runtime_version`

因此以下规则成立：

1. `payload.runtime_version` 是必需的业务关联键
2. 如果 payload 中 runtime_version 缺失或错误，runtime 聚合将失真
3. 同一 `project_id + runtime_version` 下的所有 job 会被视为同一 runtime 的执行集合

---

## 5. Compile 阶段的 job 创建契约

当 `POST /api/v1/compile` 使用 `dispatch_jobs=true` 时，`CompilerService._create_and_dispatch_jobs()` 会执行以下逻辑。

### 5.1 固定创建顺序

当前固定 job types 顺序：

1. `compile`
2. `render_image`
3. `render_video`
4. `render_voice`
5. `merge`

### 5.2 初始状态

每条 job 创建时：

- `status = "queued"`
- `payload` 写入基础字段
- `external_task_id = null`
- `result_payload = null`

### 5.3 dispatch 成功时

`JobDispatchService.dispatch(job, runtime_version)` 若返回 task id：

- `job.external_task_id = task_id`
- `job.result_payload = {"celery_task_id": task_id}`
- `job.status = "dispatched"`

### 5.4 dispatch 失败 / 未返回 task id 时

若没有拿到 task id：

- `external_task_id` 保持空
- `status` 保持 `queued`
- 该 job 会被计入 `queued_job_count`

### 5.5 compile 阶段 dispatch summary

compile 创建 / 派发完成后，摘要至少包含：

```json
{
  "runtime_version": "v7",
  "job_count": 5,
  "queued_job_count": 0,
  "dispatched_job_count": 5,
  "undispatched_job_count": 0,
  "dispatch_status": "fully_dispatched",
  "jobs": [
    {
      "job_id": "...",
      "job_type": "render_image",
      "status": "dispatched",
      "external_task_id": "..."
    }
  ]
}
```

其中：

- `queued_job_count`：未成功拿到 task id 的 job 数
- `dispatched_job_count`：存在 `external_task_id` 的 job 数
- `dispatch_status`：
  - 全部成功派发 → `fully_dispatched`
  - 否则 → `partially_dispatched`

---

## 6. Worker 生命周期契约

worker 主执行函数为：

- `_run_job(job_id, project_id, runtime_version, task_name, asset_plan=None)`

### 6.1 job 加载失败

若 `db.get(Job, job_id)` 返回空：

- 直接抛出 `ValueError("job_not_found")`

### 6.2 running 阶段

`_mark_job_running()` 会执行：

- `status = "running"`
- `attempt_count += 1`
- `started_at = datetime.utcnow()`
- 清空 `error_code`
- 清空 `error_message`
- `result_payload["task"] = task_name`
- `result_payload["worker_started_at"] = started_at.isoformat()`

随后 `_run_job()` 会：

- 将 runtime `compile_status = "running"`
- 清空 runtime 级错误
- 立即刷新 runtime aggregate 并提交

### 6.3 succeeded 阶段

provider executor 执行成功后：

- 若含 `asset_plan`，先进行 asset 注册与物化
- 然后构造成功 payload
- `_mark_job_succeeded()` 将：
  - `status = "succeeded"`
  - `finished_at = datetime.utcnow()`
  - `result_payload = <最终成功 payload>`

随后刷新 runtime aggregate 并提交。

### 6.4 failed 阶段

worker 任意异常时：

- 回滚当前事务
- 若存在 `asset_plan`，会注册 `status = "failed"` 的 asset 记录
- job 会被 `_mark_job_failed()` 置为：
  - `status = "failed"`
  - `finished_at = datetime.utcnow()`
  - `error_code = "worker_execution_failed"`
  - `error_message = str(exc)`
- `result_payload` 补充：
  - `error_code`
  - `error_message`
  - `worker_finished_at`

随后 runtime 会被置为：

- `compile_status = "failed"`
- `last_error_code = "worker_execution_failed"`
- `last_error_message = str(exc)`

再执行 runtime aggregate refresh，最后重新抛错。

---

## 7. 成功 payload 契约

当前 `_run_job()` 成功完成时，result payload 至少包含：

- `job_id`
- `project_id`
- `runtime_version`
- `status`
- `task`
- `provider`
- `worker_finished_at`
- `provider_payload`

若本次 job 生成了 asset，还会额外补充：

- `asset`
- `materialization`

其中 `asset` 为轻量 asset 摘要，至少包括：

- `asset_id`
- `bucket_name`
- `object_key`
- `asset_type`
- `asset_role`
- `status`
- `content_type`
- `file_size`

`materialization` 至少包括：

- `bucket_name`
- `object_key`
- `idempotency`
- `status`
- `etag`
- `version_id`
- `size`

---

## 8. 失败 payload 契约

当前 `_mark_job_failed()` 会在现有 `result_payload` 基础上补充：

```json
{
  "error_code": "worker_execution_failed",
  "error_message": "...",
  "worker_finished_at": "2026-03-30T..."
}
```

注意：

- 失败路径不会保留完整成功 payload 结构
- 失败时的 `result_payload` 更接近错误上下文容器
- 对于已在 running 阶段写入的 `task` / `worker_started_at`，通常仍会保留

---

## 9. Asset plan 与物化契约

只有携带 `asset_plan` 的 job 会触发资产注册与对象存储物化。

### 9.1 当前 task 名称与 asset plan 映射

- `render.image` → `generated_image`, `render_output`, `{job_id}.png`, `image/png`
- `render.video` → `generated_video`, `render_output`, `{job_id}.mp4`
- `render.voice` → `audio`, `voice_output`, `{job_id}.wav`
- `merge.runtime` → `export`, `merged_output`, `{runtime_version}-{job_id}.mp4`

### 9.2 bucket 解析

资产桶由 `AssetPolicyService.resolve_bucket(asset_type)` 决定：

- `generated_image` → `generated_images`
- `generated_video` → `generated_videos`
- `audio` → `audio`
- `export` → `exports`

实际 DB 中保存的是 bucket map 解析后的桶名；当前冻结样本中 `generated_image.bucket_name = generated-images`。

### 9.3 object key 规则

runtime 生成资产 object key 规则：

```text
projects/{project_id}/runtime/{runtime_version}/{job_type}/{safe_filename}
```

例如：

```text
projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v7/render_image/e836ac89-f00b-4431-bdd0-f2a78c0f6b4b.png
```

### 9.4 成功物化后的 asset 状态

成功后 asset 至少满足：

- `status = "materialized"`
- `notes = "sixth_batch_materialization_backbone"`
- `asset_metadata` 常含：
  - `runtime_version`
  - `job_id`
  - `job_type`
  - `external_task_id`
  - `generated_by = "worker_provider_executor"`
  - `materialization_status`
  - `materialized_etag`
  - `materialized_version_id`

### 9.5 失败物化时的 asset 记录

若执行失败且存在 `asset_plan`：

- 会注册 `status = "failed"` 的 asset
- `asset_metadata.materialization_status = "failed"`
- `asset_metadata.materialization_error = str(exc)`

这保证失败任务仍可在资产层保留审计痕迹。

---

## 10. 物化幂等语义

当前物化链路支持以下幂等分支：

- `fresh_write`
- `asset_already_materialized`
- `object_store_short_circuit`

### 10.1 `fresh_write`

- 对象存储中不存在目标对象
- worker 实际上传 payload
- asset 最终 `status = materialized`

### 10.2 `asset_already_materialized`

- asset 已是 `materialized`
- 且对象存储中对象仍存在
- 直接返回已存在对象信息，不重复上传

### 10.3 `object_store_short_circuit`

- 对象已经在存储中存在
- 但 DB asset 还未完全对齐到 materialized 状态
- 系统通过对象存储现状反向对账并短路完成

---

## 11. Runtime summary 对 job 状态的消费方式

`RuntimeStateService.build_summary()` 会按状态聚合：

- `queued_job_count`
- `dispatched_job_count`
- `running_job_count`
- `succeeded_job_count`
- `failed_job_count`

并输出轻量 `jobs[]`，每项包括：

- `job_id`
- `job_type`
- `status`
- `attempt_count`
- `max_attempts`
- `external_task_id`
- `error_code`

因此对 runtime 来说，job contract 的最小稳定字段集是：

- `project_id`
- `payload.runtime_version`
- `job_type`
- `status`
- `attempt_count`
- `max_attempts`
- `external_task_id`
- `error_code`

---

## 12. 当前冻结成功样本

已确认成功样本：runtime `v7` 下 5 条 jobs 全部 `succeeded`。

具体 job：

- `compile` `b01abe36-b851-4156-9ad7-b24ca4acbdb9`
- `render_image` `e836ac89-f00b-4431-bdd0-f2a78c0f6b4b`
- `render_video` `22a06c79-f911-47e5-b209-d750ab155fec`
- `render_voice` `5b62f0d4-4535-4e8b-aff1-c754737b8a94`
- `merge` `e7212dc2-88de-4926-9ff1-426d37e5303f`

验收结论：

- 5 条 job 均 `succeeded`
- runtime `compile_status = succeeded`
- runtime `dispatch_status = fully_dispatched`
- 对应生成 asset 已 materialized

该样本是当前 job contract 的可执行成功锚点。

---

## 13. 对外使用建议

对控制平面、审计面板、repeatability report 或脚本探针，建议按以下方式消费 job 数据：

1. 先按 `project_id + payload.runtime_version` 过滤 job 集合
2. 以 `status` 作为主状态信号
3. 以 `external_task_id` 判断是否 dispatch 成功
4. 以 `attempt_count / max_attempts` 观察重试消耗
5. 失败时优先读取：
   - `error_code`
   - `error_message`
   - `result_payload.error_message`
6. 需要产物追踪时，读取 `result_payload.asset` 与 `assets` 表做交叉核对

该 contract 冻结于当前实现；若后续新增 job 表列、引入显式 runtime 外键、修改状态机或调整 result payload 结构，必须同步更新本文件。
