# Fourth Batch Engineering Notes

## 本轮目标

第四批 runnable increment 选择的是组合范围 E：

1. `jobs` / `compiled_runtimes` 状态机细化
2. worker 执行结果回写数据库与 asset 落盘主干

这一批的重点不是接入真实 provider，而是把“compile 后被投递出去的任务”从一次性 stub，推进到具备最小执行态闭环的治理主干：

- job 能看到更细的生命周期
- runtime 能看到 dispatch 与执行层反馈
- worker 具备 DB session 与统一 write-back 骨架
- render / merge 任务具备资产登记落点

## 本轮新增状态字段

### jobs

`Job` 新增了以下执行态字段：

- `attempt_count`
- `max_attempts`
- `external_task_id`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`

这让 job 不再只是 `queued` 的薄记录，而是开始具备：

- 第几次执行
- 外部任务 ID / Celery task id 映射
- 失败原因
- 起止时间

### compiled_runtimes

`CompiledRuntime` 新增了以下治理字段：

- `dispatch_status`
- `dispatch_summary`
- `last_error_code`
- `last_error_message`
- `compile_started_at`
- `compile_finished_at`

这里的设计意图是把 runtime 从“只保存 compile payload 的快照”，升级为“compile 与 dispatch 的控制面观察对象”。

## 新迁移

新增 Alembic 迁移：

- `20260330_0004_expand_runtime_job_states`

它负责为 `jobs` 与 `compiled_runtimes` 增补上述字段，并对既有数据补默认值。

## Compile 侧状态机细化

`app/compilers/orchestrator/compiler_service.py` 已做以下增强：

1. compile 时记录：
   - `compile_started_at`
   - `compile_finished_at`
2. 新 runtime 默认写入：
   - `dispatch_status = not_dispatched`
   - `dispatch_summary = {}`
3. 当 `dispatch_jobs=true` 时：
   - 创建 5 类 job：`compile / render_image / render_video / render_voice / merge`
   - 对每个 job 记录 `external_task_id`
   - 若成功获得 Celery task id，则把 job 状态从 `queued` 更新为 `dispatched`
4. compile 结果会额外写入 `dispatch_summary`，内容包括：
   - runtime version
   - 总 job 数
   - 已成功投递数
   - 未成功投递数
   - 每个 job 的状态与 external task id

因此第四批之后，compile 接口返回的 runtime 已经不再只是“编译成功没”，而是能表达“是否已进入调度层”。

## Worker write-back 主干

`app/workers/tasks.py` 已从纯 stub 演进为带数据库回写的统一任务执行骨架。

### 核心能力

#### 1. SessionLocal 接入

每个 worker task 现在通过 `SessionLocal` 获取数据库会话，具备修改：

- `jobs`
- `compiled_runtimes`
- `assets`

的能力。

#### 2. 统一 job 生命周期写回

任务主流程统一走 `_run_job(...)`：

- 开始执行时：
  - `job.status = running`
  - `attempt_count += 1`
  - `started_at = now`
- 执行成功时：
  - `job.status = succeeded`
  - `finished_at = now`
  - `result_payload` 写入结果摘要
- 执行失败时：
  - `job.status = failed`
  - 写入 `error_code` / `error_message`
  - `finished_at = now`

#### 3. runtime 执行态反馈

worker 在执行阶段会尝试回写对应 runtime：

- 任务开始时把 runtime 标记为 `compile_status = running`
- 若任务异常，写入：
  - `compile_status = failed`
  - `last_error_code`
  - `last_error_message`

当前这还是一个“主干版本”的 runtime 执行反馈，不是最终的精细聚合状态机；但已经打通了 runtime <- worker 的反馈通路。

## 资产落盘主干

本轮在 worker 内新增了 `_register_generated_asset(...)`，用于为生成类任务登记资产记录。

当前接入情况：

- `render.image` -> `generated_image`
- `render.video` -> `generated_video`
- `render.voice` -> `audio`
- `merge.runtime` -> `export`

当前资产写法是第四批的治理骨架实现：

- 先在数据库落 `Asset`
- 写 bucket / object key / filename / content_type / metadata
- 暂不真的上传二进制到 MinIO

### 当前 object key 规则

worker 侧主干当前使用：

`projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`

它与第三批 `AssetService` 的“上传登记 object key”规则并不完全相同，这是有意保留的：

- 第三批规则偏“上传入口治理”
- 第四批规则偏“运行期产物归档”

后续建议统一抽成 runtime asset path policy，避免 object key 规则散落在多个写入点。

## 当前任务定义行为

第四批结束后，worker 中的 5 个任务行为如下：

- `compile.runtime`
  - 更新 job 运行态
  - 不登记资产
- `render.image`
  - 更新 job 运行态
  - 登记图片资产
- `render.video`
  - 更新 job 运行态
  - 登记视频资产
- `render.voice`
  - 更新 job 运行态
  - 登记音频资产
- `merge.runtime`
  - 更新 job 运行态
  - 登记导出视频资产

当前返回仍然是 stub 成功结果，但它们已经不是“无副作用 stub”，而是“有控制面状态回写的 stub”。

## Schema 输出变化

`app/schemas/compile.py` 的 `CompiledRuntimeRead` 已扩展输出：

- `dispatch_status`
- `dispatch_summary`
- `last_error_code`
- `last_error_message`
- `compile_started_at`
- `compile_finished_at`

`app/schemas/job.py` 已扩展输出：

- `attempt_count`
- `max_attempts`
- `external_task_id`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`

这意味着控制面 API 现在可以直接向前端或调试调用者暴露更完整的作业/运行态观测信息。

## 本轮仍然刻意没做的内容

第四批仍未进入以下部分：

- 真实 provider 调用
- MinIO 二进制上传 / put object
- provider 返回物与 asset metadata 对齐
- job retrying / dead-letter / backoff
- runtime 聚合完成态判断（例如所有子 job 成功后自动转 `succeeded`）
- runtime packet 归档到 runtime bucket
- export manifest / QA report / merge report

原因很明确：本轮目标是先打通“worker 可执行 + 可回写 + 可登记资产”的主干，而不是现在就把 provider 逻辑耦死进去。

## 当前形成的新闭环

第四批结束后，最小闭环已经变成：

1. 项目结构通过 validator
2. compile 生成 canonical runtime
3. compile 可创建并投递 jobs
4. job 进入 `queued / dispatched / running / succeeded / failed` 的基础生命周期
5. worker 可把执行结果回写 DB
6. 生成类任务可登记资产记录
7. runtime 可接收来自 worker 的错误与执行态反馈

这标志着系统已经从“compile + dispatch skeleton”，进入“有实际执行治理主干的控制面 MVP”。

## 建议下一批重点

建议下一批优先推进以下 5 件事：

1. **runtime 聚合状态机**  
   基于所有 jobs 的状态推导 runtime 的 `running / partially_failed / succeeded / failed`。

2. **provider adapter 真正接线**  
   把 Veo / image / TTS provider 的调用接进 `_run_job(...)` 的可插拔执行器中。

3. **MinIO 真正落盘**  
   将 worker 生成结果写入 object storage，再把 `assets.status` 从 `registered` 推进到更准确的已落盘状态。

4. **retry / backoff / 幂等保护**  
   让 `attempt_count` / `max_attempts` 真正参与调度治理，而不是只做观测字段。

5. **runtime archive / export manifest**  
   为 compiled payload、merge 输出、QA 输出建立统一 manifest 与 runtime bucket 归档规范。
