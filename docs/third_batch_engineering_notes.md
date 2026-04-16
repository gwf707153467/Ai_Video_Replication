# Third Batch Engineering Notes

## 本轮新增范围

本轮把第二批的控制面骨架继续推进到第一个更接近 runnable 的治理主干，重点补的是四类能力：

- 资产登记与对象存储分层
- MinIO bucket bootstrap
- compile validator + runtime versioning
- compile 后 job dispatch / export 挂接

目标不是直接完成完整视频生产，而是把 canonical runtime 周围的治理支架固定下来，让后续 provider、merge、QA、retry 有稳定接入点。

## 新增领域对象与职责

### Asset

`Asset` 是统一资产清单表，用来登记：

- 项目级或 sequence 级资产归属
- 资产类型与角色
- bucket / object key
- 原始文件名与 MIME
- 文件大小与扩展 metadata
- 当前资产状态

当前 object key 规则：

`projects/{project_id}/{sequence_scope}/{asset_type}/{asset_role}/{filename}`

其中：

- `sequence_scope = sequences/{sequence_id}` 或 `project`
- bucket 由 `asset_type` 决定

### StorageService

`StorageService` 负责：

- 读取 bucket 配置
- 判断 bucket 是否存在
- 缺失时自动创建
- 返回 bootstrap 结果摘要

这让应用 startup 和显式 API bootstrap 都能复用同一逻辑。

### CompileValidatorService

compile validator 当前是 compile 前的轻量结构校验层，保证：

- 至少存在 sequences
- 至少存在 spus
- spu / vbu / bridge 指向的 sequence 合法
- vbus / bridges 缺失先记 warning，不阻塞 compile

这使 compile 不再只是“机械拼包”，而变成“校验后再出 canonical runtime”。

### RuntimeVersionService

`RuntimeVersionService` 当前采用最简单的项目内顺序版本策略：

- 按项目现有 runtime 数量递增
- 生成 `v1` / `v2` / `v3` ...

这样先保证 runtime 版本可稳定外显，后续再演进为更严格的版本治理或幂等策略。

### JobDispatchService

`JobDispatchService` 提供 compile 后的任务映射层：

- `compile` -> `compile.runtime`
- `render_image` -> `render.image`
- `render_video` -> `render.video`
- `render_voice` -> `render.voice`
- `merge` -> `merge.runtime`

当前 worker 仍是 stub，但路由已经从 API -> DB Job -> Celery 投递打通。

## 新增与更新的 API

### Compile

- `POST /api/v1/compile`
- `GET /api/v1/compile/validate/{project_id}`

`POST /api/v1/compile` 新行为：

1. 检查项目存在
2. 执行 validator
3. 自动或显式确定 runtime version
4. 生成 canonical runtime packet
5. 写入 `compiled_runtimes`
6. 可选创建并投递 compile/render/merge jobs

### Assets

- `POST /api/v1/assets`
- `POST /api/v1/assets/register`
- `GET /api/v1/assets/project/{project_id}`

其中 `register` 接口用于“先登记，再上传”的模式，返回 upload target，便于后续接 presign 或直传策略。

### Storage

- `POST /api/v1/storage/bootstrap`

同时，应用在 startup 时也会尝试自动 ensure buckets。

### Exports

- `POST /api/v1/exports`

当前 export 侧重点是：

- 绑定 runtime
- 创建 export 类型 job
- 为后续最终封装/导出留出治理入口

## 数据库变更

### 新迁移

- `20260330_0003_add_assets`

新增：

- `assets` 表
- bucket/object 唯一约束：`uq_assets_bucket_object_key`
- `project_id` / `sequence_id` / `asset_type` 索引

## 工程实现边界

本轮故意没有做的内容：

- 真正的文件上传二进制接收
- presigned URL
- runtime packet 同步归档到 MinIO runtime bucket
- worker 实际调用 Google/Veo/TTS provider
- QA / validator / retry 的执行态回写
- export 文件真实合成与下载链接

原因是本轮目标是先完成治理骨架，而不是过早进入 provider 细节耦合。

## 当前已形成的治理闭环

已经具备的最小闭环：

1. 控制面录入项目结构
2. 调用 validator 检查 compile 前结构合法性
3. compile 输出 canonical runtime
4. runtime 获得稳定 version
5. compile 后可创建 jobs 并投递到 Celery
6. 资产与对象存储已有统一登记和 bucket 分层
7. export 已具备 runtime 绑定入口

这意味着第三批结束后，系统已经从“纯骨架”进入“可围绕 runtime 持续长肉”的阶段。

## 建议下一批重点

1. Job 状态机细化：queued / running / succeeded / failed / retrying
2. 真实 worker 执行器：provider 调用、结果回写、资产落盘
3. runtime bucket 归档：compiled payload + manifests
4. export 下载物：最终视频、字幕、封面、manifest
5. compile validator 升级为多级 validator：schema / policy / asset / provider compatibility
