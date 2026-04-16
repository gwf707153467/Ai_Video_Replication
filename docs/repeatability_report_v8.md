# Repeatability Verification Report — Runtime v8

## 1. 文档目的

本报告用于固化当前冻结主链路的一次 repeatability 验证结果，证明已知成功锚点 `v7` 之后，当前沙箱环境仍可再次跑通 compile → dispatch → worker → asset materialization → runtime aggregation 的最小生产基线路径。

本报告严格遵守当前边界：

- 不改 provider 主逻辑
- 不回退 compose 基线
- 不重开 provider 排障
- 仅验证当前冻结成功路径在现状下是否可重复成立

---

## 2. 验证范围与冻结前提

本次验证基于以下冻结前提执行：

- repo root：`/mnt/user-data/workspace/Ai_Videos_Replication`
- compose 命令仅使用 `docker-compose`
- 保持当前已修复 `docker-compose.yml`：
  - `app` / `worker` 不恢复 `.:/workspace` bind mount
  - `app` command 保持 `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  - `worker` command 保持 `celery -A app.workers.celery_app worker --loglevel=INFO`
- startup 不自动跑 migration
- DB 查询固定使用：
  - user：`postgres`
  - database：`ai_videos_replication`
- provider 主逻辑不变
- image model 继续冻结为：`imagen-4.0-fast-generate-001`

---

## 3. 验证对象

### 3.1 Smoke project

- `project_id = 656ac6b1-ecb8-4f45-9f45-556be5915168`
- `sequence_id = 7226dad0-a05f-411b-9acf-ac15a3128f4c`
- `spu_id = 31431873-86b2-4adb-aeaf-78f6067335d8`
- `name = eighth-batch-render-image-smoke`

### 3.2 本轮 runtime

- `runtime_id = 9489a79a-6c84-455a-8699-94f3a5eb487c`
- `runtime_version = v8`
- `compile_reason = manual_runtime_validation`
- `compile_options = {"mode": "manual_runtime_validation"}`

### 3.3 对照锚点

- 冻结成功锚点：`v7`
- 本轮验证目标：确认当前环境仍具备再次生成一个完整成功 runtime 的能力，而不是复现相同 runtime id。

---

## 4. 执行摘要

本轮 repeatability probe 已成功创建并完成 `v8`，结论如下：

- `POST /api/v1/compile` 成功创建 `v8`
- `dispatch_jobs=true` 成功创建并派发 5 个标准 jobs
- 5 个 jobs 最终全部 `succeeded`
- `compiled_runtimes` 中 `v8` 最终聚合为：
  - `compile_status = succeeded`
  - `dispatch_status = fully_dispatched`
- `assets` 中已形成 4 类 materialized 产物：
  - `generated_image`
  - `generated_video`
  - `audio`
  - `export`
- MinIO 对象存储中已验证对应对象存在

因此，当前冻结基线已从单点成功锚点 `v7`，推进到至少两次成功样本：`v7` 与 `v8`，可支持把现状认定为“可重复的最小生产基线”。

---

## 5. 运行面证据

### 5.1 服务基线

本轮执行前已确认以下服务处于运行状态：

- `avr_app`
- `avr_worker`
- `avr_postgres`
- `avr_redis`
- `avr_minio`

### 5.2 健康检查

`/health` 已成功返回 200，且返回结构满足当前契约：

```json
{
  "status": "ok",
  "app_env": "development",
  "target_market": "US",
  "target_language": "en-US"
}
```

### 5.3 migration 基线

当前 Alembic 版本仍为：

- `20260330_0004`

---

## 6. Compile / Dispatch 证据

### 6.1 compile probe 请求

本轮仍使用冻结 smoke payload：

```json
{
  "project_id": "656ac6b1-ecb8-4f45-9f45-556be5915168",
  "compile_reason": "manual_runtime_validation",
  "compile_options": {
    "mode": "manual_runtime_validation"
  },
  "auto_version": true,
  "dispatch_jobs": true
}
```

### 6.2 runtime 创建结果

DB 查询确认 `v8` 最终状态为：

- `id = 9489a79a-6c84-455a-8699-94f3a5eb487c`
- `runtime_version = v8`
- `compile_status = succeeded`
- `dispatch_status = fully_dispatched`
- `last_error_code = null`

### 6.3 dispatch summary 聚合结果

`compiled_runtimes.dispatch_summary` 已聚合到成功终态：

- `runtime_version = v8`
- `job_count = 5`
- `queued_job_count = 0`
- `running_job_count = 0`
- `failed_job_count = 0`
- `succeeded_job_count = 5`

注意：本轮直接读取到的 `dispatch_summary.dispatched_job_count = 0`，而初始 compile 返回中的 dispatch 摘要曾为 `5`。这与当前 `RuntimeStateService.build_summary()` 的实现口径一致：

- 聚合摘要中的 `dispatched_job_count` 统计的是“当前仍处于 dispatched 状态的 job 数”
- 当全部 job 已推进到 `succeeded` 后，该字段回落为 `0`

因此，这不是失败信号，也不影响 `dispatch_status = fully_dispatched` 的最终验收结论。

---

## 7. Job 面证据

本轮 `v8` 共创建并完成 5 个标准 jobs：

| job_type | job_id | status | external_task_id |
|---|---|---|---|
| compile | `7de9273a-770d-4ebe-adea-13560aec9dc3` | `succeeded` | `ecfd965d-9ad5-4877-b70b-98e9b0c441af` |
| render_image | `3607c6c1-ff4b-428b-b9a1-ebaf6ef22e36` | `succeeded` | `b480bde2-eb27-4180-8dd0-bdedc5d088ff` |
| render_video | `5eb9398c-47f1-4107-bb3d-e3e15137ad91` | `succeeded` | `d84e8310-e173-449a-a03c-4232c5c2ac72` |
| render_voice | `5a07a1be-aec9-4ec1-8e3e-92e1a127481d` | `succeeded` | `4339cec8-e573-4b54-a65f-8ca9fe857b6e` |
| merge | `1c0e0b7b-a93c-4ac2-bb4f-21d860141d0e` | `succeeded` | `3d3b255e-25c8-4d77-858b-9746f1470e34` |

验收结论：

- 5 个标准 job 均已成功完成
- 无 `failed` job
- 无 `error_code`
- 每个 job 都拿到了 `external_task_id`

这说明 compile endpoint → dispatch → worker 执行主链路在当前冻结环境下再次成功闭环。

---

## 8. Asset 面证据

DB 中已查询到 4 条与 `runtime_version = v8` 关联的 materialized assets：

| asset_type | status | bucket_name | object_key | content_type |
|---|---|---|---|---|
| export | `materialized` | `exports` | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/merge/v8-1c0e0b7b-a93c-4ac2-bb4f-21d860141d0e.mp4` | `video/mp4` |
| generated_video | `materialized` | `generated-videos` | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_video/5eb9398c-47f1-4107-bb3d-e3e15137ad91.mp4` | `video/mp4` |
| audio | `materialized` | `audio-assets` | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_voice/5a07a1be-aec9-4ec1-8e3e-92e1a127481d.wav` | `audio/wav` |
| generated_image | `materialized` | `generated-images` | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_image/3607c6c1-ff4b-428b-b9a1-ebaf6ef22e36.png` | `image/png` |

同时，资产字段也满足当前物化 backbone 约束：

- `notes = sixth_batch_materialization_backbone`
- `asset_metadata.runtime_version = v8`
- `asset_metadata.generated_by = worker_provider_executor`

验收结论：

- DB 中 asset 注册与 materialization 状态一致
- 产物类型、bucket、object_key、content_type 均符合当前 contract

---

## 9. Object Store 面证据

### 9.1 有效 bucket 配置

容器内实际生效的 MinIO bucket 命名为：

- `reference-assets`
- `generated-images`
- `generated-videos`
- `audio-assets`
- `exports`
- `runtime-packets`

其中与本轮 `v8` 直接相关的是：

- `generated-images`
- `generated-videos`
- `audio-assets`
- `exports`

### 9.2 对象存在性验证

通过容器内 MinIO client probe，已确认以下对象存在：

| bucket | object_key | size | content_type | result |
|---|---|---:|---|---|
| exports | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/merge/v8-1c0e0b7b-a93c-4ac2-bb4f-21d860141d0e.mp4` | 196 | `video/mp4` | exists |
| generated-videos | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_video/5eb9398c-47f1-4107-bb3d-e3e15137ad91.mp4` | 202 | `video/mp4` | exists |
| audio-assets | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_voice/5a07a1be-aec9-4ec1-8e3e-92e1a127481d.wav` | 202 | `audio/wav` | exists |
| generated-images | `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_image/3607c6c1-ff4b-428b-b9a1-ebaf6ef22e36.png` | 480106 | `image/png` | exists |

### 9.3 说明：一次无效对象探测的纠偏

本轮中曾出现一次“对象不存在”的假阴性探测，根因不是物化失败，而是探测口径错误：

1. 初始尝试直接在 `avr_minio` 容器中用 `mc stat local/...` 验证对象
2. 该容器内 `local` alias 未携带访问凭据，返回了 access denied / object does not exist
3. 随后又用错误 bucket 名 `audio` 做了一次 probe，得到 `NoSuchBucket`
4. 最终改为严格按应用当前实际配置执行容器内 probe：
   - endpoint：`minio:9000`
   - audio bucket：`audio-assets`
5. 纠偏后 4 个对象全部验证存在

该事件说明：

- object-store 验证必须以应用实际生效配置为准
- 不能把 `mc` 默认 alias 或历史 bucket 记忆，当作正式验收依据
- 也再次证明 DB asset 记录与 MinIO 实物状态在 `v8` 上是闭环一致的

---

## 10. 与 production-baseline checklist 的对照结论

本轮 `v8` 已满足当前 checklist 所要求的四层验收口径：

1. **Runtime 层成功**
   - `compile_status = succeeded`
   - `dispatch_status = fully_dispatched`

2. **Job 层成功**
   - 标准 5 类 jobs 全部 `succeeded`
   - 无 failed / error_code

3. **Asset 层成功**
   - `generated_image / generated_video / audio / export` 全部 materialized
   - 路径、bucket、content_type 与 contract 一致

4. **Object Store 层成功**
   - 上述 4 类对象均在 MinIO 中可 stat 到

因此，本轮 repeatability 验证通过。

---

## 11. 最终结论

### 11.1 核心结论

当前沙箱仓库已经不再只有单点成功锚点 `v7`，而是至少具备两次独立成功样本：

- `v7`：冻结成功锚点
- `v8`：repeatability probe 成功样本

这意味着：

- 当前 image-generation 主链路在冻结基线下具备可重复执行能力
- `imagen-4.0-fast-generate-001` 作为当前最小可行 image model 的结论得到了再次支持
- compile/runtime/job/asset/object-store 多平面验收口径已能够形成稳定闭环

### 11.2 当前可接受的工程判断

可以把当前仓库状态认定为：

**已具备“可重复的最小生产基线（repeatable production baseline）”**

但仍不应夸大为长期稳定性、容量稳定性或多项目泛化稳定性证明；当前结论仍限定于：

- 当前沙箱
- 当前 smoke project
- 当前冻结 provider / compose / schema / worker 主线

---

## 12. 建议的下一步

建议下一步按以下顺序推进，而不是回头重开 provider 排障：

1. **固化验收门禁**
   - 把本报告中的四层验收标准（runtime / jobs / assets / object store）整理成可重复执行的 gate
   - 明确 compile 200 或 runtime 创建成功，不等于 baseline 通过

2. **沉淀自动化验证脚本**
   - 把当前健康检查、compile probe、DB 查询、MinIO stat 统一收敛成一个单入口验证脚本
   - 输出结构化 verdict：PASS / FAIL / DRIFT

3. **把 bucket 生效配置纳入 runbook**
   - 明确当前实际 bucket 名为 `reference-assets / generated-images / generated-videos / audio-assets / exports / runtime-packets`
   - 避免后续再出现用历史 bucket 名或 `mc` alias 造成的假阴性

4. **进入更高阶 repeatability**
   - 后续若继续扩展，可再做：
     - 多轮连续重复验证
     - 异常恢复/幂等短路验证
     - 更严格的 runtime 状态回归验证

---

## 13. 本轮产出结论一句话版本

`v8` 已在当前冻结沙箱基线下完成从 compile 到对象存储物化的全链路成功复跑，说明当前仓库已经具备可重复的最小生产基线能力。
