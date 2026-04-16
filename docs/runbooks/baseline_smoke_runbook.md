# Baseline Smoke Runbook

## 1. 目的

本 runbook 用于把当前已冻结的 image-generation 成功基线，转成可重复执行、可审计、可交接的 smoke 操作说明。

当前主线目标不是继续排障，而是验证以下事实在仓库现状下可以重复成立：

- compose 基线保持不变
- API / worker / DB / Redis / MinIO 处于已知健康状态
- `POST /api/v1/compile` 可以为最小 smoke 项目生成 runtime
- 当 `dispatch_jobs=true` 时，系统会创建并派发 5 类 job：`compile`、`render_image`、`render_video`、`render_voice`、`merge`
- runtime 聚合状态可以从 `compiled/dispatched/running` 推进到 `succeeded`
- `render_image` 在当前有效模型 `imagen-4.0-fast-generate-001` 下已被验证可成功物化
- 成功后 `jobs` / `assets` / MinIO 对象路径能够形成闭环

本 runbook 以仓库当前实现事实为准，不以旧文档或外部环境假设为准。

---

## 2. 冻结前提与禁止回退项

执行本 runbook 时，必须保持以下约束不变：

### 2.1 仓库与命令约束

- repo root：`/mnt/user-data/workspace/Ai_Videos_Replication`
- 只能使用 `docker-compose`
- 不要使用 `docker compose`
- `docker exec` 默认工作目录按容器内 `/workspace` 处理
- 需要容器内 HTTP 探测时，优先使用：
  - `cat tmp_*.py | docker exec -i avr_app python -`
- DB 查询必须使用：
  - user：`postgres`
  - database：`ai_videos_replication`

### 2.2 compose 基线约束

`docker-compose.yml` 必须保留下述已验证修复：

- 删除 `app` / `worker` 的 `volumes: - .:/workspace`
- `app` command 固定为：
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- `worker` command 固定为：
  - `celery -A app.workers.celery_app worker --loglevel=INFO`

### 2.3 provider 基线约束

本 runbook 不允许修改 provider 主逻辑。

当前冻结的最小可行 provider 基线为：

- Developer API 通道保持不变
- SDK 保持 `google-genai`
- image model 固定为：`imagen-4.0-fast-generate-001`
- 不重开 `imagen-3.0-generate-002` 主链路排障

---

## 3. 当前已知有效环境事实

执行前应默认以下事实已经成立，若不成立需先恢复到该状态：

- Alembic 迁移不会在 startup 自动执行
- 迁移已手工执行：`alembic -c alembic.runtime.ini upgrade head`
- Alembic 版本：`20260330_0004`
- compose 服务已验证存在：
  - `avr_app`
  - `avr_worker`
  - `avr_postgres`
  - `avr_redis`
  - `avr_minio`
- `.env` 已生效，且包含：
  - `GOOGLE_API_KEY=...`
  - `GOOGLE_IMAGE_MODEL=imagen-4.0-fast-generate-001`
- `/health` 已验证可返回 200

---

## 4. Smoke 对象与成功样本

当前冻结的 smoke 项目：

- `project_id = 656ac6b1-ecb8-4f45-9f45-556be5915168`
- `sequence_id = 7226dad0-a05f-411b-9acf-ac15a3128f4c`
- `spu_id = 31431873-86b2-4adb-aeaf-78f6067335d8`
- `name = eighth-batch-render-image-smoke`

当前已确认成功的 runtime：

- `runtime_version = v7`
- `runtime_id = 9c5a8e97-924a-475e-91a1-c3db0a60571b`
- `compile_status = succeeded`
- `dispatch_status = fully_dispatched`
- `succeeded_job_count = 5`
- `failed_job_count = 0`

`v7` 对应成功 job：

- `compile`：`b01abe36-b851-4156-9ad7-b24ca4acbdb9`
- `render_image`：`e836ac89-f00b-4431-bdd0-f2a78c0f6b4b`
- `render_video`：`22a06c79-f911-47e5-b209-d750ab155fec`
- `render_voice`：`5b62f0d4-4535-4e8b-aff1-c754737b8a94`
- `merge`：`e7212dc2-88de-4926-9ff1-426d37e5303f`

成功生成的 `generated_image` 样本：

- `bucket_name = generated-images`
- `object_key = projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v7/render_image/e836ac89-f00b-4431-bdd0-f2a78c0f6b4b.png`
- `content_type = image/png`

---

## 5. 执行前 checklist

在真正触发 probe 前，逐项确认：

- [ ] 当前目录是 `/mnt/user-data/workspace/Ai_Videos_Replication`
- [ ] 未修改 compose 冻结基线
- [ ] 未修改 provider 主逻辑
- [ ] `.env` 中 `GOOGLE_IMAGE_MODEL=imagen-4.0-fast-generate-001`
- [ ] `docker-compose ps` 中核心服务均已启动
- [ ] 迁移版本已到 `20260330_0004`
- [ ] smoke project `656ac6b1-ecb8-4f45-9f45-556be5915168` 仍存在
- [ ] 不把本 runbook 当成新的故障定位入口；若偏离主线，仅记录现象

---

## 6. 启动与基础探测

### 6.1 服务状态确认

建议先检查 compose 服务：

```bash
docker-compose ps
```

预期：至少看到 `avr_app`、`avr_worker`、`avr_postgres`、`avr_redis`、`avr_minio` 为运行状态。

### 6.2 健康检查

优先使用容器内 HTTP 探测，而不是依赖宿主机网络假设。

临时脚本示例：

```python
# tmp_health_probe.py
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8000/health") as resp:
    print(resp.status)
    print(json.dumps(json.loads(resp.read().decode()), ensure_ascii=False, indent=2))
```

执行方式：

```bash
cat tmp_health_probe.py | docker exec -i avr_app python -
```

预期：HTTP 200，且返回字段至少包含：

- `status`
- `app_env`
- `target_market`
- `target_language`

### 6.3 迁移版本确认

```bash
docker exec avr_postgres psql -U postgres -d ai_videos_replication -c "select version_num from alembic_version;"
```

预期：`20260330_0004`

---

## 7. 编译与派发 probe

### 7.1 请求目标

使用当前冻结 smoke 项目，向：

- `POST http://127.0.0.1:8000/api/v1/compile`

发送以下 payload：

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

### 7.2 临时 probe 脚本

```python
# tmp_compile_dispatch_probe.py
import json
import urllib.request

url = "http://127.0.0.1:8000/api/v1/compile"
payload = {
    "project_id": "656ac6b1-ecb8-4f45-9f45-556be5915168",
    "compile_reason": "manual_runtime_validation",
    "compile_options": {"mode": "manual_runtime_validation"},
    "auto_version": True,
    "dispatch_jobs": True,
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    print(resp.status)
    print(json.dumps(json.loads(resp.read().decode()), ensure_ascii=False, indent=2))
```

执行方式：

```bash
cat tmp_compile_dispatch_probe.py | docker exec -i avr_app python -
```

### 7.3 预期响应特征

若请求成功，应返回 `CompiledRuntimeRead`，其关键字段应满足：

- `project_id` 为 smoke project
- `runtime_version` 自动递增
- `compile_status` 初始可能已是 `dispatched`
- `dispatch_status` 为 `fully_dispatched` 或 `partially_dispatched`
- `dispatch_summary.job_count = 5`
- `dispatch_summary.jobs[]` 中存在五类 job

---

## 8. worker 侧预期行为

当 compile 成功且 `dispatch_jobs=true` 后，系统应：

1. 创建 5 条 job：
   - `compile`
   - `render_image`
   - `render_video`
   - `render_voice`
   - `merge`
2. job 初始状态写为 `queued`
3. dispatch 成功的 job：
   - `external_task_id` 被写入
   - `result_payload = {"celery_task_id": task_id}`
   - `status = dispatched`
4. worker 执行时：
   - 先把 job 标记为 `running`
   - `attempt_count += 1`
   - 回填 `started_at`
5. provider 执行成功后：
   - job 标记为 `succeeded`
   - 回填 `finished_at`
   - `result_payload` 写入执行结果
6. 若返回包含 `asset_plan`：
   - 生成产物被 materialize 到 MinIO
   - 对应 asset 记录入库并置为 `materialized`
7. runtime 聚合状态最终由 `RuntimeStateService` 回写

---

## 9. 成功判定

一次 smoke 通过，至少需要满足以下全部条件：

### 9.1 runtime 级

在 `compiled_runtimes` 中，目标 runtime 满足：

- `compile_status = succeeded`
- `dispatch_status = fully_dispatched`
- `dispatch_summary.job_count = 5`
- `dispatch_summary.succeeded_job_count = 5`
- `dispatch_summary.failed_job_count = 0`
- `last_error_code is null`
- `last_error_message is null`

### 9.2 job 级

`jobs` 表中按 `project_id + payload.runtime_version` 查询，结果应为 5 条，且全部：

- `status = succeeded`

### 9.3 资产级

`assets` 表中应至少存在以下 materialized 结果：

- `generated_image`
- `generated_video`
- `audio`
- `export`

其中 `generated_image` 应满足：

- `status = materialized`
- `bucket_name = generated-images`
- `content_type = image/png`
- `object_key` 路径符合：
  - `projects/{project_id}/runtime/{runtime_version}/render_image/{job_id}.png`

---

## 10. 建议核对 SQL

### 10.1 查看 runtime

```sql
select
  id,
  project_id,
  runtime_version,
  compile_status,
  dispatch_status,
  dispatch_summary,
  last_error_code,
  last_error_message,
  compile_started_at,
  compile_finished_at,
  created_at
from compiled_runtimes
where project_id = '656ac6b1-ecb8-4f45-9f45-556be5915168'
order by created_at desc;
```

### 10.2 查看 job 状态

```sql
select
  id,
  job_type,
  status,
  provider_name,
  attempt_count,
  max_attempts,
  external_task_id,
  error_code,
  error_message,
  started_at,
  finished_at,
  payload,
  result_payload
from jobs
where project_id = '656ac6b1-ecb8-4f45-9f45-556be5915168'
  and payload->>'runtime_version' = '<RUNTIME_VERSION>'
order by created_at asc;
```

### 10.3 查看 materialized assets

```sql
select
  id,
  asset_type,
  asset_role,
  bucket_name,
  object_key,
  content_type,
  status,
  asset_metadata,
  notes,
  created_at
from assets
where project_id = '656ac6b1-ecb8-4f45-9f45-556be5915168'
order by created_at desc;
```

执行示例：

```bash
docker exec avr_postgres psql -U postgres -d ai_videos_replication -c "<SQL>"
```

---

## 11. 失败分类口径

本阶段只做可审计分类，不重开主链路排障。

### 11.1 compile 请求失败

- `404 project_not_found`
  - 说明 smoke project 不存在或 project_id 错误
- `422 project_invalid`
  - 说明 compile validator 未通过
  - 优先检查 sequence / spu 是否缺失

### 11.2 dispatch 不完整

现象：

- `dispatch_status = partially_dispatched`
- `dispatch_summary.queued_job_count > 0`

含义：

- 至少有 job 未拿到 `external_task_id`
- 此时属于派发层异常，不等同于 provider 失败

### 11.3 worker 执行失败

现象：

- 某 job `status = failed`
- `error_code = worker_execution_failed`
- runtime `compile_status = failed`
- runtime `last_error_code = worker_execution_failed`

含义：

- 失败统一收口到 worker 执行失败
- 若执行过程中已经进入 asset 物化分支，可能会留下 `status = failed` 的 asset 记录

### 11.4 资产物化短路/幂等

可能出现：

- `asset_already_materialized`
- `object_store_short_circuit`
- `fresh_write`

这些属于 asset materialization 的幂等或短路语义，不应直接被解读为主链路失败。

---

## 12. v7 作为验收锚点

若需确认系统仍与冻结成功基线一致，可用 `v7` 作为锚点复核：

- runtime id：`9c5a8e97-924a-475e-91a1-c3db0a60571b`
- runtime version：`v7`
- `compile_status = succeeded`
- `dispatch_status = fully_dispatched`
- 5 个 job 全部 succeeded
- `generated_image` 已 materialized 到 `generated-images`

只要后续 repeatability probe 的结果在状态推进与产物路径上与该锚点一致，即可视为当前基线未漂移。

---

## 13. 执行产出要求

每次执行 runbook，建议至少沉淀以下记录：

- 执行时间
- 执行人
- git commit 或工作树状态
- 本次 runtime_version
- compile 返回 JSON
- runtime SQL 摘要
- job SQL 摘要
- asset SQL 摘要
- 是否达到通过标准
- 若失败，失败分类归口

---

## 14. 本 runbook 的边界

本文件只服务于“从 smoke 成功样本过渡到 reusable production baseline 验证”的第一层操作规范。

它不承担以下职责：

- provider 深度排障
- prompt 优化
- compose 重构
- worker 调度策略重构
- 新模型接入试验

若后续需要做 repeatability report，应基于本 runbook 的固定步骤与固定口径输出，而不是临场变更验证方法。
