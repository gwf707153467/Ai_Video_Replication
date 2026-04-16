# Fifth Batch Engineering Notes

## 本轮目标

第五批 runnable increment 选择的是组合范围 F：

1. runtime 基于 jobs 的聚合状态更新主干
2. 统一 asset bucket / object key policy
3. provider executor 插槽接入 worker 主流程

这一批的重点仍然不是接入真实 Veo / TTS / 图像 provider，而是把第四批已经打通的“worker 可执行 + 可回写 + 可登记资产”骨架，继续升级成更稳定的治理主干：

- asset 命名与 bucket 选择不再散落在多个写入点
- runtime 不再只靠 worker 局部写死状态，而是开始基于 jobs 聚合推导
- worker 主流程不再把 provider 逻辑写死在任务函数里，而是切到可插拔 executor 入口

## 本轮新增组件

### 1. AssetPolicyService

新增文件：`app/services/asset_policy_service.py`

它把资产策略从 `AssetService` 与 worker 内部逻辑中抽出来，形成统一策略层，当前提供三类能力：

- `safe_name(filename)`
- `resolve_bucket(asset_type)`
- `build_project_asset_object_key(...)`
- `build_runtime_asset_object_key(...)`

其中两类 object key 规则被明确区分：

#### 项目上传 / 注册路径

用于项目域资产登记：

`projects/{project_id}/{sequence_scope}/{asset_type}/{asset_role}/{filename}`

其中 `sequence_scope` 为：

- `sequences/{sequence_id}`，或
- `project`

#### runtime 运行期产物路径

用于 worker 产物登记：

`projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`

这个区分非常关键：

- 上传入口路径服务于“项目侧素材治理”
- runtime 路径服务于“执行期产物归档”

第五批没有把它们强行合并成一条规则，而是把两条规则都收敛到统一 policy service 中管理，避免 bucket 名和 object key 格式继续散落。

## 统一 bucket policy 落地

`AssetService` 已重构为复用 `AssetPolicyService`：

- `_safe_name()` -> `AssetPolicyService.safe_name`
- `_resolve_bucket()` -> `AssetPolicyService.resolve_bucket`
- `_build_object_key()` -> `AssetPolicyService.build_project_asset_object_key`

这一步解决了此前的一个真实风险：worker 或 service 若继续手写 bucket 名，容易与 `.env.example` 和 `settings` 漂移。

当前 bucket 选择统一通过 `StorageService.bucket_map()` 间接生效，因此：

- `reference_video` / `reference_image` -> `reference-assets`（或环境变量覆盖值）
- `generated_image` -> `generated-images`
- `generated_video` -> `generated-videos`
- `audio` -> `audio-assets`
- `export` -> `exports`
- `runtime` -> `runtime-packets`

## Runtime 聚合状态机主干

新增文件：`app/services/runtime_state_service.py`

### 当前职责

`RuntimeStateService.refresh_runtime_status(db, runtime)` 会：

1. 查出同一 `project_id + runtime_version` 下的所有 jobs
2. 统计 `queued / dispatched / running / succeeded / failed`
3. 生成统一 `dispatch_summary`
4. 推导 `dispatch_status`
5. 推导 `compile_status`
6. 在失败场景下同步 `last_error_code`

### 当前 dispatch_summary 结构

当前 summary 至少包含：

- `runtime_version`
- `job_count`
- `queued_job_count`
- `dispatched_job_count`
- `running_job_count`
- `succeeded_job_count`
- `failed_job_count`
- `jobs[]`

其中每个 job 摘要包含：

- `job_id`
- `job_type`
- `status`
- `attempt_count`
- `max_attempts`
- `external_task_id`
- `error_code`

### 当前状态推导规则

#### compile_status

- 若 `failed_job_count > 0` -> `failed`
- 若全部 job 都 `succeeded` -> `succeeded`
- 若存在 `queued / dispatched / running` -> `running`
- 若 runtime 下没有 job，则保持当前状态

#### dispatch_status

- 若无 job -> 保持当前状态
- 若尚无任何 job 进入 `dispatched / running / succeeded / failed` -> `not_dispatched`
- 若只有部分 job 进入上述集合 -> `partially_dispatched`
- 若全部 job 都至少被成功投递过一次 -> `fully_dispatched`

这意味着第五批之后，runtime 的状态不再主要依赖 worker 手工设置，而开始具备“基于 job 集合聚合”的控制面含义。

## Worker 主流程升级

`app/workers/tasks.py` 已接入两类第五批能力：

### 1. runtime 聚合刷新

worker 在以下关键节点调用：

- 任务开始后
- 任务成功后
- 任务失败后

统一通过：

- `_refresh_runtime_aggregate(...)`
- `RuntimeStateService.refresh_runtime_status(...)`

完成 runtime 聚合状态刷新。

这让 runtime 开始成为“job 集合执行态”的观察结果，而不是单次任务函数的局部副作用。

### 2. provider executor 插槽

新增文件：`app/workers/executors.py`

当前包含：

- `ProviderExecutionResult`
- `BaseProviderExecutor`
- `StubProviderExecutor`
- `ProviderExecutorRegistry`

worker 主流程 `_run_job(...)` 现在通过：

`ProviderExecutorRegistry.resolve(job.job_type)`

拿到执行器，再统一调用：

`executor.execute(...)`

当前仍是 stub executor，但已把 provider 调用点从 Celery task 函数里抽出，形成独立插槽。

## 当前 provider executor 设计意图

第五批没有实现真实 provider 调用，只实现了“接线位”：

- 每种 `job_type` 可映射到不同 executor
- executor 返回统一结果结构：
  - `status`
  - `provider`
  - `output_filename`
  - `provider_payload`
- worker 再决定是否登记 asset 以及如何回写 job/result

这样后续接 Veo、图片生成、TTS、merge provider 时，不需要继续改 Celery 任务边界，只需要替换 registry 映射与具体 executor 实现。

## Worker 资产登记行为

worker 当前继续只做“DB 资产登记主干”，尚未上传二进制到 MinIO。

但第五批后，worker 写回路径已经统一经过 `AssetPolicyService.build_runtime_asset_object_key(...)`，因此 runtime 产物的 object key 规则被固定为：

`projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`

并且 bucket 也不再硬编码，而是通过 asset type -> policy -> storage bucket map 解析。

## 当前形成的新闭环

第五批结束后，系统最小治理闭环进一步升级为：

1. compile 生成 canonical runtime
2. compile 可创建并调度 jobs
3. worker 可推进 job 生命周期
4. worker 可登记 runtime 产物资产
5. runtime 可基于 job 集合自动刷新聚合状态
6. provider 调用位已被 registry + executor 插槽抽象出来
7. asset bucket / object key policy 已在 service 与 worker 两侧统一

这标志着系统从“有 worker write-back 的控制面 MVP”，进入“开始具备 runtime 聚合状态机与 provider 插槽的可扩展控制面 MVP”。

## 本轮刻意仍未做的内容

第五批仍然没有进入以下部分：

- 真实 provider adapter / API 调用
- MinIO 二进制上传与对象存在性确认
- asset 状态从 `registered` 推进到 `uploaded` / `materialized`
- retry / backoff / dead-letter 真正参与调度
- runtime 的 `partially_failed` 等更精细中间态
- runtime packet / provider output / QA report 的 runtime bucket 归档
- executor 级配置装配、provider 选择策略、熔断与限流

原因是本轮目标依旧是“先固定治理边界”，而不是过早把 provider 细节耦进主干。

## 代码层交付清单

### 新增文件

- `app/services/asset_policy_service.py`
- `app/services/runtime_state_service.py`
- `app/workers/executors.py`
- `docs/fifth_batch_engineering_notes.md`

### 已修改文件

- `app/services/asset_service.py`
- `app/workers/tasks.py`
- `README.md`

## 最小验证结果

已对以下模块做 `python -m py_compile` 静态编译校验：

- `app/services/asset_policy_service.py`
- `app/services/runtime_state_service.py`
- `app/workers/executors.py`
- `app/workers/tasks.py`
- `app/services/asset_service.py`

结果：通过。

这至少确认：

- 缺失模块依赖已补齐
- 第五批主干当前处于可导入、可解释的状态

## 建议下一批重点

建议第六批优先进入以下方向：

1. **真实 provider executor 实现**  
   为 `render_image / render_video / render_voice / merge` 分别接入真正 provider executor。

2. **对象存储真实落盘**  
   将 executor 输出与 MinIO `put_object` / 上传确认接通，补齐 asset materialization。

3. **更细 runtime 状态机**  
   引入 `partially_failed / retrying / blocked / merged / qa_failed` 等更符合生产治理的 runtime 状态。

4. **retry / backoff / 幂等**  
   让 `attempt_count` / `max_attempts` 与调度策略真正闭环。

5. **runtime archive / manifest**  
   将 runtime packet、provider 输出、merge manifest、QA 报告统一归档到 runtime bucket。