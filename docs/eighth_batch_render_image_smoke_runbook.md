# 第八批：`render_image` repo 可执行 smoke-test runbook / checklist

## 1. 文档定位

本文档是 `docs/eighth_batch_implementation_preparation.md` 的落地执行版，仅服务于第八批已锁定范围：

- `render_image` 单路径 smoke test
- real-run 前人工核对 checklist
- failure classification 记录与归因

**明确不包含：**

- 第二家 provider / executor 接入
- `render_video` / `render_voice` / `merge.runtime` 真执行扩展
- 新代码逻辑改造
- 大范围运行时架构调整

本文目标不是继续开发，而是让仓库当前基线可以被**按步骤验证**，并且让第一次真实联调具备一致的记录口径。

---

## 2. 适用基线

执行本文前，默认以下事实成立：

- Batch 5 / 6 / 7 已关闭
- 当前唯一真实接通 provider 的任务是：`render_image -> google -> imagen-3.0-generate-002`
- worker 已具备 runtime/job 状态推进、asset 注册/upsert、产物 materialization、失败产物登记能力
- 运行时产物路径固定为：
  - `projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`
- 项目上传资产路径固定为：
  - `projects/{project_id}/{sequence_scope}/{asset_type}/{asset_role}/{filename}`
- `StorageService` / `RuntimeArtifactService` / `AssetPolicyService` / `RuntimeStateService` 已存在且应直接复用
- 本批仅允许文档落地；不得借执行 runbook 名义扩大代码范围

---

## 3. smoke-test 目标

本 runbook 验证的是：

1. API / DB / Redis / MinIO / worker 基础链路可启动
2. 项目、sequence、SPU 可通过现有 API 建立最小编译输入
3. compile 可生成包含 `render_image` job 的 runtime
4. dispatch 后 worker 能实际取到 job 并调用 Google provider
5. 成功时可在存储层与资产表看到 `generated_image` 结果
6. 失败时能够按本文定义进入可归类、可追踪、可复盘状态

**通过标准：** 至少完成一次 `render_image` 成功闭环，或在失败时拿到足够归因信息，能明确落入既定 failure domain。

---

## 4. 预备条件 checklist

执行前人工勾选：

- [ ] 仓库根目录为：`/mnt/user-data/workspace/Ai_Videos_Replication`
- [ ] 本次执行严格使用当前仓库代码，不混入未记录的本地临时修改
- [ ] `.env` 已存在，且与 `.env.example` 对齐
- [ ] `GOOGLE_API_KEY` 已填入有效值
- [ ] `GOOGLE_IMAGE_MODEL` 明确为 `imagen-3.0-generate-002`
- [ ] 本机 / 容器网络允许访问 Google 相关接口
- [ ] Docker / Docker Compose 可正常运行
- [ ] 不对仓库代码做顺手修复；发现问题先记录，再决定是否进入后续 batch

**建议额外记录：**

- 执行人
- 执行时间
- 分支名 / commit hash
- `.env` 关键变量是否已核对

---

## 5. 最小 smoke 数据模型

建议使用**单项目 / 单 sequence / 单 SPU** 最小样本，避免噪音。

### 5.1 Project

接口：`POST /api/v1/projects`

最小请求体：

```json
{
  "name": "batch8-render-image-smoke",
  "status": "draft",
  "source_market": "US",
  "source_language": "en-US",
  "notes": "batch8 smoke test only"
}
```

### 5.2 Sequence

接口：`POST /api/v1/sequences`

最小请求体：

```json
{
  "project_id": "<PROJECT_ID>",
  "sequence_index": 1,
  "sequence_type": "hook",
  "persuasive_goal": "introduce product visual anchor",
  "status": "draft"
}
```

### 5.3 SPU

接口：`POST /api/v1/spus`

最小请求体：

```json
{
  "project_id": "<PROJECT_ID>",
  "sequence_id": "<SEQUENCE_ID>",
  "spu_code": "SPU-001",
  "display_name": "Primary product hero frame",
  "asset_role": "primary_visual",
  "duration_ms": 5000,
  "generation_mode": "veo_segment",
  "prompt_text": "Create a premium beauty product hero image for a vertical commerce ad. Keep the composition clean, product-forward, realistic, and conversion-oriented.",
  "negative_prompt_text": "blurry, distorted, extra objects, messy background, broken packaging, unreadable label",
  "visual_constraints": {
    "aspect_ratio": "9:16",
    "style": "clean_commerce",
    "background": "studio"
  },
  "status": "draft"
}
```

说明：

- 此处不追求 prompt 最优，只追求最小可执行
- `CompilerService` 会基于项目 / sequence / SPU 组装 `render_image` 最小 provider 输入
- 当前 smoke 目标是闭环，而不是美术质量评估

---

## 6. 启动步骤

以下命令均在 repo root 执行：

```bash
docker compose up -d postgres redis minio
```

```bash
docker compose up -d app worker
```

### 6.1 基础健康检查

```bash
curl http://localhost:8000/health
```

期望：返回 `status=ok`。

### 6.2 存储 bootstrap 校验

应用启动时会自动尝试 bucket bootstrap；如需显式复核，可执行：

```bash
curl -X POST http://localhost:8000/api/v1/storage/bootstrap
```

期望：返回 bucket 初始化结果，而不是 500。

### 6.3 日志观察建议

建议同时打开两个观察窗口：

```bash
docker logs -f avr_app
```

```bash
docker logs -f avr_worker
```

如果需要追加 DB 侧观察，可进入 postgres 容器查询。

---

## 7. API 执行顺序

## 7.1 创建 project

```bash
curl -s -X POST http://localhost:8000/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "batch8-render-image-smoke",
    "status": "draft",
    "source_market": "US",
    "source_language": "en-US",
    "notes": "batch8 smoke test only"
  }'
```

记录返回中的 `id` 为 `PROJECT_ID`。

## 7.2 创建 sequence

```bash
curl -s -X POST http://localhost:8000/api/v1/sequences \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "<PROJECT_ID>",
    "sequence_index": 1,
    "sequence_type": "hook",
    "persuasive_goal": "introduce product visual anchor",
    "status": "draft"
  }'
```

记录返回中的 `id` 为 `SEQUENCE_ID`。

## 7.3 创建 SPU

```bash
curl -s -X POST http://localhost:8000/api/v1/spus \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "<PROJECT_ID>",
    "sequence_id": "<SEQUENCE_ID>",
    "spu_code": "SPU-001",
    "display_name": "Primary product hero frame",
    "asset_role": "primary_visual",
    "duration_ms": 5000,
    "generation_mode": "veo_segment",
    "prompt_text": "Create a premium beauty product hero image for a vertical commerce ad. Keep the composition clean, product-forward, realistic, and conversion-oriented.",
    "negative_prompt_text": "blurry, distorted, extra objects, messy background, broken packaging, unreadable label",
    "visual_constraints": {
      "aspect_ratio": "9:16",
      "style": "clean_commerce",
      "background": "studio"
    },
    "status": "draft"
  }'
```

记录返回中的 `id` 为 `SPU_ID`。

## 7.4 编译前校验

接口：`GET /api/v1/compile/validate/{project_id}`

```bash
curl -s http://localhost:8000/api/v1/compile/validate/<PROJECT_ID>
```

期望：

- `is_valid = true`，或
- 至少错误信息足以解释为什么当前项目不能编译

如果 `is_valid = false`，此次 smoke 停在此处并进入 failure classification。

## 7.5 仅编译，不 dispatch

先做一次 compile-only，确认 runtime 结构正确。

```bash
curl -s -X POST http://localhost:8000/api/v1/compile \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "<PROJECT_ID>",
    "compile_reason": "batch8_smoke_compile_only",
    "compile_options": {},
    "auto_version": true,
    "dispatch_jobs": false
  }'
```

核对返回：

- `compile_status` 已完成
- `runtime_version` 已生成
- `runtime_payload` 内存在 sequence / spu 相关内容
- `dispatch_status` 仍为未派发或等价状态

记录本次 `runtime_version`。

## 7.6 编译并 dispatch

```bash
curl -s -X POST http://localhost:8000/api/v1/compile \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "<PROJECT_ID>",
    "compile_reason": "batch8_smoke_dispatch",
    "compile_options": {},
    "auto_version": true,
    "dispatch_jobs": true
  }'
```

核对返回：

- 新的 `runtime_version` 已生成
- `dispatch_status` 进入已派发或处理中
- `dispatch_summary` 存在 job 统计信息

随后转到 worker / DB / asset 结果核查。

---

## 8. 结果核查顺序

## 8.1 Worker 日志核查

重点观察 `avr_worker` 日志是否出现以下信号：

- job 被领取
- `render_image` executor 被路由到 Google
- prompt 从 `job.payload` / `provider_inputs` 成功解析
- provider 成功返回图片 bytes
- runtime artifact materialization 成功
- asset 注册或 upsert 成功

失败时重点抓取：

- provider error 原始文本
- job error code / message
- traceback 关键片段
- 是否已经完成失败资产登记

## 8.2 资产接口核查

接口：`GET /api/v1/assets/project/{project_id}`

```bash
curl -s http://localhost:8000/api/v1/assets/project/<PROJECT_ID>
```

成功期望：

- 至少出现一条 `asset_type = generated_image`
- `asset_role = render_output`
- `content_type = image/png`
- `status` 为可接受终态（如已注册 / 已生成 / 项目内约定状态）
- `object_key` 满足运行时固定路径规则

建议重点核对 `object_key`：

```text
projects/<PROJECT_ID>/runtime/<RUNTIME_VERSION>/render_image/<JOB_ID>.png
```

如果路径不符合该规则，应记录为实现偏差。

## 8.3 MinIO 对象核查

如果已知 bucket 与 object key，应进一步确认对象真实存在。

核对点：

- 对象可在 MinIO 中看到
- MIME 类型应为 `image/png`
- 文件大小大于 0
- 如果重复执行相同链路，不应因 materialization 重试导致明显异常的重复脏写

## 8.4 数据库状态核查

建议检查以下实体：

- `compiled_runtimes`
- `jobs`
- `assets`

核对重点：

### CompiledRuntime

- `runtime_version` 已生成
- `compile_status` 合理
- `dispatch_status` 合理
- `last_error_code` / `last_error_message` 在成功场景为空或未设置

### Job

- `job_type = render_image`
- attempt / time / error / payload / result 字段有一致更新
- 成功时有结果摘要
- 失败时有明确错误归因

### Asset

- 存在对应 runtime 产物记录
- `(bucket_name, object_key)` 未违反唯一约束
- 初始注册 / upsert 行为与既有实现一致

---

## 9. smoke 通过判定

满足以下全部条件，可判定本次 smoke 通过：

- [ ] `app` 与 `worker` 容器均正常启动
- [ ] `GET /health` 正常
- [ ] `compile/validate` 对最小项目返回可接受结果
- [ ] compile-only 成功生成 runtime
- [ ] compile+dispatch 成功触发 `render_image` job
- [ ] worker 未在基础链路处崩溃
- [ ] 资产表中可看到 `generated_image/render_output`
- [ ] MinIO 中可确认对应对象存在
- [ ] 对象路径符合 `projects/{project_id}/runtime/{runtime_version}/{job_type}/{filename}`
- [ ] 失败字段在成功场景下未出现异常污染

如果最后一步是失败但已明确落入既定 failure domain，也算**smoke 已完成但结果为 fail**，可以进入下一轮问题整治，而不是重新定义范围。

---

## 10. failure classification

沿用第八批准备文档，执行时统一按以下 domain 归类：

### F1. 配置 / 环境失败

示例：

- `GOOGLE_API_KEY` 缺失或错误
- `.env` 与代码配置不一致
- 容器环境变量未注入

观察信号：

- provider 调用前即失败
- health 正常但真实生成失败
- 日志出现认证、缺参、配置读取异常

### F2. Provider 调用失败

示例：

- Google 返回 4xx / 5xx
- 模型名错误
- 配额 / 权限 / region / safety 阻断

观察信号：

- `GoogleProviderError`
- 返回体含明确 provider 侧错误码或错误消息

### F3. 编译输入失败

示例：

- 项目结构不满足 compile 条件
- sequence / SPU 缺失
- prompt 或上下文组装为空

观察信号：

- `compile/validate` 不通过
- compile 阶段抛出 `project_invalid`
- runtime_payload 不含可执行 `render_image` job

### F4. Worker / 调度失败

示例：

- dispatch 后 worker 未消费
- celery / redis 链路异常
- executor registry 路由失败

观察信号：

- dispatch_summary 有 job，但 worker 无处理痕迹
- job 状态停滞在 queued / dispatched 类状态
- 日志缺少 executor 进入记录

### F5. 存储 / 物化失败

示例：

- MinIO bucket/object 写入失败
- materialize_bytes 失败
- 资产登记成功但对象实际不存在

观察信号：

- provider 已返回图片 bytes，但后续 asset/object 缺失
- `stat_object` / `object_exists` 与 DB 状态不一致

### F6. 状态收敛失败

示例：

- job 成功但 runtime/job/asset 状态未同步
- 失败已发生，但错误码 / 错误消息未落库
- 重试后留下不一致脏状态

观察信号：

- 业务结果与 DB 字段矛盾
- 成功对象存在，但状态仍停在失败或处理中
- 失败后未形成可复盘记录

---

## 11. failure record 模板

每次失败必须至少记录一次，避免口头结论。

```md
## Batch 8 render_image smoke failure record

- Execution time:
- Executor:
- Branch / commit:
- Project ID:
- Runtime version:
- Job ID:
- Failure domain: F1 | F2 | F3 | F4 | F5 | F6
- Symptom summary:
- API step reached:
- Worker log excerpt:
- App log excerpt:
- DB evidence:
- Storage evidence:
- Provider raw error (if any):
- First suspected root cause:
- Whether reproducible:
- Recommended next action:
```

---

## 12. 推荐执行节奏

为降低定位成本，建议按下列节奏执行：

1. 只起容器并过 `health` / `storage/bootstrap`
2. 创建 project / sequence / SPU
3. 先跑 `compile/validate`
4. 先跑 compile-only
5. 再跑 compile+dispatch
6. 最后核对 worker / asset / storage / DB

不要一上来混合多个变量；每一步都保留输出。

---

## 13. 执行后结论模板

### 13.1 成功结论模板

```md
Batch 8 render_image smoke test passed.

- Project ID:
- Runtime version:
- Generated asset object key:
- Bucket name:
- Validation result:
- Worker result summary:
- Remaining non-blocking observations:
```

### 13.2 失败结论模板

```md
Batch 8 render_image smoke test completed with failure.

- Project ID:
- Runtime version:
- Failed step:
- Failure domain:
- Primary evidence:
- Scope impact:
- Whether code change is required:
- Proposed next batch entry point:
```

---

## 14. Definition of Done（文档落地版）

本文档完成后，第八批当前子任务的 DoD 为：

- 仓库内存在一份**可直接跟着执行**的 `render_image` smoke runbook
- runbook 中的接口、路径、字段名与当前 repo 实际实现一致
- runbook 明确了通过标准、失败域、记录模板
- runbook 明确声明**不扩 scope**
- 后续执行真实 smoke 时，无需先补写流程说明文档

---

## 15. 与范围锁定的一致性声明

本文仅是 Batch 8 option 2 的 repo 文档落地，不代表：

- 已完成 Google 真实在线 smoke
- 已新增任何执行器
- 已进入第九批
- 已批准修改现有代码逻辑

如果真实执行过程中暴露问题，应先按本文完成证据采集与 failure classification，再决定是否进入新的实现批次。
