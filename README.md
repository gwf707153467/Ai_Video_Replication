# AI Videos Replication

治理型控制面 / 状态机内核 / 编译器驱动的 TikTok / TK 带货视频 AI 复刻系统 MVP 工程骨架。

当前实现继续沿着方案 A 落地：以 canonical runtime 为执行真相源，以 validator / versioning / dispatch / worker write-back / runtime aggregation / provider executor slot / storage policy 为 runnable increment 的主干，而不是直接把业务逻辑散落到工作流节点里。

## 当前骨架范围

- FastAPI 控制面骨架
- PostgreSQL + SQLAlchemy + Alembic 初版
- Redis + Celery worker 初版
- MinIO 对象存储接入骨架
- Google provider adapter（`render_image -> google / imagen-3.0-generate-002` 最小真实接入）
- Compiler / Validator / Runtime registry 目录骨架
- app 与 worker 镜像内置 FFmpeg
- runtime 聚合状态主干
- provider executor 插槽主干
- 统一 asset policy 主干
- runtime artifact materialization 主干
- 最小 object-store 幂等保护

## 本地启动

1. 复制环境变量文件：`.env.example` 到 `.env`
2. 按需调整 PostgreSQL / Redis / MinIO / Google provider 配置
3. 执行：`docker compose up --build`
4. 首次启动时应用会在 startup 阶段尝试自动创建 MinIO buckets
5. 访问：
   - 健康检查：`GET /health`
   - OpenAPI：`/docs`

## 关键环境变量

### MinIO

- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_SECURE`
- `MINIO_BUCKET_REFERENCE`
- `MINIO_BUCKET_GENERATED_IMAGES`
- `MINIO_BUCKET_GENERATED_VIDEOS`
- `MINIO_BUCKET_AUDIO`
- `MINIO_BUCKET_EXPORTS`
- `MINIO_BUCKET_RUNTIME`

`.env.example` 当前默认值：

- `MINIO_BUCKET_REFERENCE=reference-assets`
- `MINIO_BUCKET_GENERATED_IMAGES=generated-images`
- `MINIO_BUCKET_GENERATED_VIDEOS=generated-videos`
- `MINIO_BUCKET_AUDIO=audio-assets`
- `MINIO_BUCKET_EXPORTS=exports`
- `MINIO_BUCKET_RUNTIME=runtime-packets`

注意：`app/core/config.py` 中也存在默认 bucket 名；实际运行以环境变量覆盖为准。

## 当前 API

### Health

- `GET /health`

### Project Domain

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/sequences`
- `POST /api/v1/sequences`
- `GET /api/v1/spus`
- `POST /api/v1/spus`
- `GET /api/v1/vbus`
- `POST /api/v1/vbus`
- `GET /api/v1/bridges`
- `POST /api/v1/bridges`

### Compile Runtime

- `POST /api/v1/compile`
- `GET /api/v1/compile/validate/{project_id}`

`POST /api/v1/compile` 当前行为：

1. 校验项目是否存在
2. 调用 compile validator 检查 sequences / spus / vbus / bridges 基础完整性
3. 根据请求参数决定 runtime version：
   - `runtime_version` 已传且 `auto_version=false`：使用显式版本
   - 其他情况：自动分配下一版本，如 `v1` / `v2`
4. 组装 canonical runtime packet 并落表 `compiled_runtimes`
5. 若 `dispatch_jobs=true`，额外创建并投递以下 job：
   - `compile`
   - `render_image`
   - `render_video`
   - `render_voice`
   - `merge`
6. runtime 会在 worker 执行阶段基于 jobs 聚合刷新：
   - `dispatch_status`
   - `dispatch_summary`
   - `compile_status`
   - `last_error_code`

当前 compile validator 规则：

- errors
  - `missing_sequences`
  - `missing_spus`
  - `spu_sequence_missing:{spu_code}`
  - `vbu_sequence_missing:{vbu_code}`
  - `bridge_sequence_missing:{bridge_code}`
- warnings
  - `missing_vbus`
  - `missing_bridges`

当存在 error 时，compile 接口返回 `422 project_invalid`。

### Assets / Storage / Export

- `POST /api/v1/assets`
- `POST /api/v1/assets/register`
- `GET /api/v1/assets/project/{project_id}`
- `POST /api/v1/storage/bootstrap`
- `POST /api/v1/exports`

当前行为说明：

- `assets/register` 会生成 bucket + object key + upload path，并在数据库中登记 `registered` 资产记录
- 项目域 object key 规则：`projects/{project_id}/{sequence_scope}/{asset_type}/{asset_role}/{filename}`
- worker runtime 产物 object key 规则：`projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`
- `storage/bootstrap` 会确保 reference / generated_images / generated_videos / audio / exports / runtime buckets 存在
- `exports` 会登记 export job，并尝试关联指定 runtime 或项目最新 runtime

## 当前数据层增量

### Alembic 迁移

- `20260330_0001_init_schema`
- `20260330_0002_add_spus_vbus_bridges`
- `20260330_0003_add_assets`
- `20260330_0004_expand_runtime_job_states`

### 关键表

- `projects`
- `sequences`
- `spus`
- `vbus`
- `bridges`
- `compiled_runtimes`
- `jobs`
- `assets`

## 当前 Celery / Worker 主干

当前 worker 已注册以下任务：

- `compile.runtime`
- `render.image`
- `render.video`
- `render.voice`
- `merge.runtime`

其中 `render_image` 已接入 `google / imagen-3.0-generate-002` 的最小真实 provider executor；`compile / render_video / render_voice / merge` 仍保持 stub executor。当前整体已具备以下治理主干：

- job 生命周期写回：`queued / dispatched / running / succeeded / failed`
- runtime 聚合状态刷新
- 运行期 asset 登记与状态推进（`registered / materialized / failed`）
- runtime 产物真实 materialization 到 MinIO
- 最小 object-store 幂等短路与 DB/object reconciliation
- provider executor registry 插槽

## 第三至第六批 runnable increment 已覆盖内容

### 第三批

- assets ORM / schema / API
- export schema / service / API
- MinIO bucket bootstrap service
- app startup bucket ensure
- compile validator service
- runtime auto versioning service
- compile route validate endpoint
- compile 后可选 job 创建与 Celery dispatch skeleton
- assets Alembic migration

### 第四批

- `jobs` / `compiled_runtimes` 状态字段扩展
- worker 执行结果回写数据库主干
- runtime 错误反馈主干
- 生成类任务资产登记主干

### 第五批

- `AssetPolicyService` 统一 bucket / object key policy
- `RuntimeStateService` 基于 jobs 聚合 runtime 状态
- worker 接入 provider executor registry / executor slot
- runtime 产物路径固定为 runtime-oriented object key policy

### 第六批

- `RuntimeArtifactService` 封装 runtime object materialization
- `StorageService` 补齐 `stat_object / object_exists / put_bytes`
- worker 生成类任务可真实写入 MinIO 对象存储
- asset 状态可从 `registered` 推进到 `materialized / failed`
- 引入最小 object-store 幂等短路与 DB/object reconciliation
- executor 结果契约显式支持 `binary_payload / text_payload / content_type`

## 当前系统能力边界

当前交付已经具备：

- canonical runtime compile
- compile validator
- runtime versioning
- job dispatch backbone
- worker write-back backbone
- runtime aggregation backbone
- asset policy unification
- provider executor slot backbone
- runtime artifact materialization backbone
- 最小 object-store 幂等保护

但仍未具备：

- 真实 provider 调用
- provider 输出真实性校验与内容级验证
- retry / backoff / dead-letter 闭环
- QA / merge / export manifest 完整治理
- runtime archive 完整归档

## 下一步建议

1. 扩展第二个真实 provider executor（优先 `render_voice` 或后续 `render_video`），但保持批次边界清晰
2. 为 runtime 引入更细粒度聚合状态（如 `partially_failed / retrying / qa_failed`）
3. 让 retry / backoff / 幂等保护从 object-store 层进一步接入调度层
4. 增加 runtime bucket archive、merge manifest、QA report 与 export manifest
5. 为 provider output 增加真实性校验、内容类型校验与失败分类

## 说明

当前交付仍然是 MVP 控制面增量，不是完整生产闭环。重点是继续固定：

- 控制面实体边界
- canonical compiled runtime 作为执行真相源
- validator / versioning / dispatch / write-back / aggregation / asset policy / provider slot 的治理主干
- 后续 worker / provider / merge / QA / retry 的可挂接编排骨架
