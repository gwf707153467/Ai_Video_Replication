# Sixth Batch Engineering Notes

## 本轮目标

第六批 runnable increment 选择的是：

1. 真实 executor 骨架继续收口
2. MinIO materialization 主干接入 worker
3. 最小幂等保护落入 runtime 产物写入路径

这一批不是要把真实 Veo / TTS / merge provider 全部接通，而是把第五批已经完成的：

- provider executor 插槽
- runtime asset policy
- runtime 聚合状态
- worker write-back 主干

继续推进到“worker 不只是登记资产，而是可以把 runtime 产物真实写进对象存储，并把 asset 状态推进到 materialized，同时具备最小 object-store 级幂等短路”。

## 本轮边界约束

### 1. 不新增 migration

本轮明确不引入新的 Alembic migration，而是复用现有 `Asset.status` 字段。

当前状态值按最小集合使用：

- `registered`
- `materialized`
- `failed`

这样可以先固定 worker / storage / asset 的执行主干，再决定后续是否需要把状态枚举进一步结构化。

### 2. 保持既有路径策略不变

本轮严格复用第五批形成的 object key policy：

#### 项目上传注册路径

`projects/{project_id}/{sequence_scope}/{asset_type}/{asset_role}/{filename}`

#### runtime 产物路径

`projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`

这意味着第六批不改资产命名治理，只补“真实落盘”和“状态推进”。

## 本轮新增/强化组件

## 1. StorageService 对象级 API

`app/services/storage_service.py` 已在第六批前半段安全重写，补齐对象级操作：

- `stat_object(bucket_name, object_key)`
- `object_exists(bucket_name, object_key)`
- `put_bytes(bucket_name, object_key, payload, content_type)`

其中 `stat_object(...)` 对以下 MinIO / S3 not-found 场景返回 `None`：

- `NoSuchKey`
- `NoSuchObject`
- `NoSuchBucket`

这样 worker 与 runtime artifact service 可以直接以对象存在性和对象元信息作为幂等判断依据，而不用在任务层直接碰原始 MinIO SDK 异常细节。

## 2. RuntimeArtifactService

新增文件：`app/services/runtime_artifact_service.py`

它把 runtime 产物 materialization 从 worker 任务函数里进一步抽成服务层，当前提供：

- `object_exists(...)`
- `stat_object(...) -> MaterializedObject | None`
- `materialize_bytes(...) -> MaterializedObject`
- `materialize_text(...)`

其中 `MaterializedObject` 统一暴露：

- `bucket_name`
- `object_key`
- `etag`
- `version_id`
- `size`
- `content_type`

这样 worker 在处理成功回写时，不需要直接关心 MinIO SDK 返回结构，而是通过统一 dataclass 获取对象落盘结果。

## 3. Worker materialization 主流程

`app/workers/tasks.py` 在本轮做了核心升级。

### 任务执行主流程

worker 现在仍保留原有的：

- job running / succeeded / failed 写回
- runtime 聚合状态刷新
- provider executor 调用

但在生成类任务上新增了真实 materialization 路径：

1. 根据 `asset_plan` 解析 asset type / role / filename / content_type
2. 按 runtime asset policy 注册或复用对应 `Asset` 记录
3. 通过 `RuntimeArtifactService` 检查对象是否已存在
4. 若对象已存在，则直接 reconciliation / short-circuit
5. 若对象不存在，则把 executor 结果写入 MinIO
6. 写回 asset 的：
   - `status=materialized`
   - `file_size`
   - `content_type`
   - materialization 元信息
7. 把 asset 摘要与 materialization 摘要回写到 job `result_payload`

### 新增 worker 内部辅助能力

当前 `tasks.py` 中形成了几类内部能力：

- runtime asset object key 生成
- 运行期 asset upsert / reuse
- asset payload 构建
- executor 输出转 materialization payload
- object-store 幂等短路
- materialization 成功 / 失败后的资产状态推进

## 4. Asset 状态推进

第六批之前，生成类任务只会登记 runtime asset，默认停留在 `registered`。

第六批之后，worker 在生成类任务成功时会把资产推进到：

- `registered -> materialized`

若执行或 materialization 失败，则会把资产更新为：

- `failed`

这意味着系统第一次具备了“资产登记”和“对象真实存在”之间的区别。

当前 asset metadata 还会额外记录：

- `materialization_status`
- `materialized_etag`
- `materialized_version_id`
- `materialization_error`（失败时）

## 5. 最小幂等保护

本轮没有做完整的调度级幂等，也没有引入分布式锁，但补上了“对象存储存在性短路”这一层最小幂等保护。

### 当前幂等规则

worker 在写 runtime 产物前，按以下优先顺序短路：

#### 场景 A：asset 已是 `materialized`，且对象仍存在

直接复用对象，不再重复上传。

结果摘要中标记：

- `idempotency=asset_already_materialized`

#### 场景 B：asset 不是 `materialized`，但对象已存在

说明 DB 状态与对象存储可能发生漂移，此时做 reconciliation：

- asset 状态修正为 `materialized`
- file size / content type / etag 等重新同步

结果摘要中标记：

- `idempotency=object_store_short_circuit`

#### 场景 C：对象不存在

执行真实写入：

- `idempotency=fresh_write`

这个层级虽然还很轻，但已经能避免最常见的“同一个 runtime object key 被 worker 重复上传”。

## 6. Executor 返回契约收口

`app/workers/executors.py` 在第六批继续收口。

### ProviderExecutionResult 当前字段

- `status`
- `provider`
- `output_filename`
- `provider_payload`
- `binary_payload`
- `text_payload`
- `content_type`

### 当前意义

第五批的 executor 更多只是 provider slot；第六批开始，它还承担“给 materialization 提供可落盘 payload”的职责。

当前 stub executor 对带 `asset_plan` 的任务会返回：

- `output_filename`
- `text_payload`
- `content_type`

因此：

- `render_image`
- `render_video`
- `render_voice`
- `merge`

这些任务虽然仍然是 stub provider，但已经能真实把占位产物写入 MinIO 对应 bucket/object key，而不再停留在“只在 DB 里登记资产”。

## 当前 worker 结果结构增强

worker 成功回写时，`job.result_payload` 除原有 provider 信息外，还会包含：

- `asset`
  - `asset_id`
  - `bucket_name`
  - `object_key`
  - `asset_type`
  - `asset_role`
  - `status`
  - `content_type`
  - `file_size`
- `materialization`
  - `bucket_name`
  - `object_key`
  - `idempotency`
  - `status`
  - `etag`
  - `version_id`
  - `size`

这使 job 不再只是“provider 执行记录”，而开始带有“runtime artifact 物化结果摘要”。

## compile / runtime 聚合关系

第六批没有改动 `CompilerService` 的 job 编排顺序，也没有改动 `RuntimeStateService` 的聚合规则。

当前仍然由 compile 侧创建并投递：

- `compile`
- `render_image`
- `render_video`
- `render_voice`
- `merge`

worker 在每个阶段继续调用 runtime 聚合刷新，因此第六批新增的 materialization 行为，并没有破坏第五批已经固定下来的 runtime aggregate 模型。

## 当前形成的新闭环

第六批结束后，系统主干闭环进一步变成：

1. compile 生成 canonical runtime
2. compile 创建并调度 jobs
3. worker 通过 executor slot 执行 job
4. 生成类任务按统一 asset policy 注册 runtime 资产
5. worker 将产物真实 materialize 到 MinIO
6. asset 从 `registered` 推进到 `materialized` / `failed`
7. job 结果回写 asset + materialization 摘要
8. runtime 继续基于 job 集合刷新聚合状态

这意味着系统已经从“可 dispatch、可 write-back、可 aggregate、可 slot executor”，进一步升级为“可真实落 runtime artifact 到 object store 的治理型 MVP 控制面”。

## 本轮刻意仍未做的内容

第六批依然没有进入以下能力：

- 真实 Veo / 图像 / TTS / merge provider 调用
- provider 结果的二进制真实性校验
- dispatch 层分布式锁与严格幂等键
- retry / backoff / dead-letter 与 materialization 联动
- asset 生命周期更细粒度状态（如 `uploading` / `reconciling`）
- runtime manifest / archive / QA report 归档
- merge/export 结果的完整治理闭环

也就是说，第六批解决的是“object store materialization backbone”，不是“完整生产执行闭环”。

## 代码层交付清单

### 新增文件

- `app/services/runtime_artifact_service.py`
- `docs/sixth_batch_engineering_notes.md`

### 第六批已修改文件

- `app/services/storage_service.py`
- `app/workers/tasks.py`
- `app/workers/executors.py`
- `README.md`

## 最小验证结果

已执行：

`python -m compileall app`

结果通过，至少确认：

- `app/services/runtime_artifact_service.py`
- `app/services/storage_service.py`
- `app/workers/executors.py`
- `app/workers/tasks.py`

在当前代码树中可成功编译导入。

## 建议下一批重点

建议第七批优先考虑以下方向之一：

1. 真实 provider executor 接入（哪怕先只打通一个 render_image 或 render_voice provider）
2. 以 runtime packet / provider output / merge manifest 为核心的 runtime archive 治理
3. 把 retry / backoff / idempotency 从 object-store 层进一步推进到 dispatch / worker 调度层
4. 引入 QA / export manifest，把 merge/export 从“任务”提升到“可治理对象”

如果继续按“治理骨架优先”的节奏推进，第七批最稳妥的落点应是：

- 一个真实 provider executor
- 一个 runtime manifest / archive 主干
- 一个更明确的 retry/idempotency 协议
