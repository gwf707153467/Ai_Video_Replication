# `baseline_gate.py` 首次执行前检查记录模板

## 1. 文档信息

| 字段 | 内容 |
|---|---|
| 文档名称 | `baseline_gate.py` 首次执行前检查记录 |
| 仓库路径 | `/mnt/user-data/workspace/Ai_Videos_Replication` |
| 脚本路径 | `scripts/baseline_gate.py` |
| 检查日期 | `____-__-__` |
| 检查人 | `__________` |
| 复核人 | `__________` |
| 目标 smoke project_id | `__________` |
| 目标环境 | `sandbox / docker-compose / linux` |
| 检查性质 | 首次真实执行前只读核验 |

## 2. 适用范围与边界

本记录模板仅用于 `scripts/baseline_gate.py` 的**首次真实执行前准备**，不替代脚本执行本身，也不替代执行后的结果判定。

### 2.1 固定边界

- 仅针对 `scripts/baseline_gate.py` 做执行前检查记录。
- 以当前 sandbox 仓库与容器状态为准，不以外部 Windows 环境覆盖实际现状。
- 不执行 `baseline_gate.py`。
- 不在本记录过程中改写脚本逻辑。
- 不主动做 DB refresh / commit 来“帮脚本成功”。
- 不把 Stage 5 的 asset-runtime 关联误表述为强契约。

### 2.2 本次既定真实契约摘要

#### compile API

- 路由文件：`app/api/v1/routes/compile_routes.py`
- `POST /api/v1/compile` -> `CompiledRuntimeRead`
- `GET /api/v1/compile/validate/{project_id}` -> `CompileValidationRead`
- `CompileRequest.project_id` 为 `UUID`
- `project_not_found -> 404`
- `project_invalid -> 422`

#### CompilerService 行为

- `compile_project(request)`：项目不存在 -> `project_not_found`
- validate 失败 -> `project_invalid`
- `auto_version=True` 时使用版本服务生成新版本
- `dispatch_jobs=True` 时创建固定 5 类 jobs：
  - `compile`
  - `render_image`
  - `render_video`
  - `render_voice`
  - `merge`

#### Stage 4 / 5 关键契约

- Stage 4 只读观察，不 refresh / commit。
- Stage 4 jobs 查询条件必须为：
  - `Job.project_id == runtime.project_id`
  - `Job.payload["runtime_version"].astext == runtime.runtime_version`
- Stage 4 成功门槛：
  - `derived_compile_status == "succeeded"`
  - `derived_dispatch_status == "fully_dispatched"`
- Stage 5 仅依赖 ORM：`CompiledRuntime`、`Job`、`Asset`
- Stage 5 的 asset-runtime 关联当前仍为：
  - `project_id + required_asset_types + asset_metadata.runtime_version`
- 该关联为 **tentative metadata-backed**，不是 DB 强约束。

---

## 3. 总门槛确认

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| 当前目标仍是“首次真实执行前准备”而非继续改脚本 | 是 |  |  |  |
| 本次仍坚持 `docker-compose` 而非 `docker compose` | 是 |  |  |  |
| `app` 无 `.:/workspace` bind mount | 是 |  |  |  |
| `worker` 无 `.:/workspace` bind mount | 是 |  |  |  |
| `app` command 仍为 `uvicorn app.main:app --host 0.0.0.0 --port 8000` | 是 |  |  |  |
| `worker` command 仍为 `celery -A app.workers.celery_app worker --loglevel=INFO` | 是 |  |  |  |
| 已接受 Stage 5 asset association 为 tentative 而非强契约 | 是 |  |  |  |
| 本轮不再扩写 `baseline_gate.py` 逻辑 | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 4. 仓库与 compose 基线检查

### 4.1 仓库定位

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| 仓库根路径仍为 `/mnt/user-data/workspace/Ai_Videos_Replication` | 是 |  |  |  |
| `scripts/baseline_gate.py` 路径未变 | 是 |  |  |  |
| `docker-compose.yml` 路径未变 | 是 |  |  |  |
| `app/`、`scripts/`、`docs/`、`app/workers/`、`app/services/` 结构无明显漂移 | 是 |  |  |  |

### 4.2 compose 工具与服务块

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| 环境中存在 `docker-compose` 命令 | 是 |  |  |  |
| `docker-compose.yml` 当前仍为标准两空格缩进风格 | 是 |  |  |  |
| `postgres` 容器名仍为 `avr_postgres` | 是 |  |  |  |
| `redis` 容器名仍为 `avr_redis` | 是 |  |  |  |
| `minio` 容器名仍为 `avr_minio` | 是 |  |  |  |
| `app` 容器名仍为 `avr_app` | 是 |  |  |  |
| `worker` 容器名仍为 `avr_worker` | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 5. Settings / Migration / 基础服务检查

### 5.1 Settings 锁定项

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| `google_image_model` 未偏离 baseline | 是 |  |  |  |
| MinIO endpoint 配置未损坏 | 是 |  |  |  |
| MinIO secure 配置未损坏 | 是 |  |  |  |
| `minio_bucket_reference` 存在且配置正确 | 是 |  |  |  |
| `minio_bucket_generated_images` 存在且配置正确 | 是 |  |  |  |
| `minio_bucket_generated_videos` 存在且配置正确 | 是 |  |  |  |
| `minio_bucket_audio` 存在且配置正确 | 是 |  |  |  |
| `minio_bucket_exports` 存在且配置正确 | 是 |  |  |  |
| `minio_bucket_runtime` 存在且配置正确 | 是 |  |  |  |

### 5.2 Migration 与服务状态

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| Alembic revision 已在 head | 是 |  |  |  |
| 无未应用迁移 | 是 |  |  |  |
| postgres 可用 | 是 |  |  |  |
| redis 可用 | 是 |  |  |  |
| minio 可用 | 是 |  |  |  |
| app 可用 | 是 |  |  |  |
| worker 可用 | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 6. Stage 1 健康探针契约检查

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| app 容器内可访问 `127.0.0.1:8000` | 是 |  |  |  |
| `/health` 路由存在 | 是 |  |  |  |
| `/health` 返回 HTTP 200 | 是 |  |  |  |
| 返回体为 JSON object | 是 |  |  |  |
| health required keys 未变更 | 是 |  |  |  |
| 当前 probe 输出模式仍兼容“单行 `json.dumps({...})`”假设 | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 7. Stage 2 Compile Validate 契约检查

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| 路由仍为 `GET /api/v1/compile/validate/{project_id}` | 是 |  |  |  |
| 返回体仍至少含 `project_id` | 是 |  |  |  |
| 返回体仍至少含 `is_valid` | 是 |  |  |  |
| 返回体仍至少含 `errors` | 是 |  |  |  |
| 返回体仍至少含 `warnings` | 是 |  |  |  |
| 返回体仍至少含 `counts` | 是 |  |  |  |
| `is_valid=False` 语义未改变 | 是 |  |  |  |
| `errors` 非空仍视为 fail | 是 |  |  |  |
| `warnings` 非空仍仅为 warning-aware | 是 |  |  |  |
| smoke project 在 DB 中真实存在 | 是 |  |  |  |
| smoke project 理论上 validate 可通过 | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 8. Stage 3 Compile Dispatch 契约检查

### 8.1 Request 契约

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| POST 路由仍为 `/api/v1/compile` | 是 |  |  |  |
| `CompileRequest.project_id` 仍为 UUID | 是 |  |  |  |
| `runtime_version` 仍为可选字段 | 是 |  |  |  |
| `compile_reason` 仍为可传字段 | 是 |  |  |  |
| `compile_options` 仍为可传 dict 字段 | 是 |  |  |  |
| `auto_version` 仍为可传 bool 字段 | 是 |  |  |  |
| `dispatch_jobs` 仍为可传 bool 字段 | 是 |  |  |  |
| 脚本当前 payload 为 `project_id + compile_reason + compile_options + auto_version + dispatch_jobs` | 是 |  |  |  |
| `compile_options={"mode": "<ctx.mode>"}` 仍被服务接受 | 是 |  |  |  |
| `auto_version=True` 仍会生成新 runtime_version | 是 |  |  |  |
| `dispatch_jobs=True` 仍触发 jobs 创建与调度 | 是 |  |  |  |

### 8.2 Response 与错误语义

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| 返回体仍为 `CompiledRuntimeRead` | 是 |  |  |  |
| 返回体含 `id` | 是 |  |  |  |
| 返回体含 `runtime_version` | 是 |  |  |  |
| 返回体含 `dispatch_summary` | 是 |  |  |  |
| `project_not_found -> 404` | 是 |  |  |  |
| `project_invalid -> 422` | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 9. Stage 4 Runtime Polling 契约检查

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| Stage 4 只读观察，不 refresh/commit | 是 |  |  |  |
| jobs 查询条件仍为 `project_id + payload.runtime_version` | 是 |  |  |  |
| summary 含 `runtime_version` | 是 |  |  |  |
| summary 含 `job_count` | 是 |  |  |  |
| summary 含 `queued_job_count` | 是 |  |  |  |
| summary 含 `dispatched_job_count` | 是 |  |  |  |
| summary 含 `running_job_count` | 是 |  |  |  |
| summary 含 `succeeded_job_count` | 是 |  |  |  |
| summary 含 `failed_job_count` | 是 |  |  |  |
| summary 含 `jobs` | 是 |  |  |  |
| jobs evidence 至少含 `job_id/job_type/status/external_task_id/error_code` | 是 |  |  |  |
| `derive_compile_status` 语义仍未漂移 | 是 |  |  |  |
| `derive_dispatch_status` 语义仍未漂移 | 是 |  |  |  |
| Stage 4 成功门槛仍为 `succeeded + fully_dispatched` | 是 |  |  |  |
| stored/derived 状态不一致仍只记 warning | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 10. Stage 5 DB Evidence 与 Asset 契约检查

### 10.1 ORM / Job / Asset

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| Stage 5 仅依赖 `CompiledRuntime` / `Job` / `Asset` | 是 |  |  |  |
| `CompiledRuntime` 字段未发生破坏性漂移 | 是 |  |  |  |
| `Job` 字段未发生破坏性漂移 | 是 |  |  |  |
| `Asset` 字段未发生破坏性漂移 | 是 |  |  |  |
| jobs 查询条件仍为 `project_id + payload.runtime_version` | 是 |  |  |  |

### 10.2 Job types / Asset types / 关联口径

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| required job types 仍为 5 类固定值 | 是 |  |  |  |
| `compile` 不产出资产 | 是 |  |  |  |
| `render_image -> generated_image` | 是 |  |  |  |
| `render_video -> generated_video` | 是 |  |  |  |
| `render_voice -> audio` | 是 |  |  |  |
| `merge -> export` | 是 |  |  |  |
| required asset types 仍为 `generated_image/generated_video/audio/export` | 是 |  |  |  |
| 当前 runtime-asset 关联仍只基于 `project_id + required_asset_types + asset_metadata.runtime_version` | 是 |  |  |  |
| 已明确接受该关联是 tentative 而非强契约 | 是 |  |  |  |

### 10.3 Metadata 支撑信号

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| worker 仍写入 `asset_metadata.runtime_version` | 是 |  |  |  |
| worker 仍写入 `asset_metadata.job_id` | 是 |  |  |  |
| worker 仍写入 `asset_metadata.job_type` | 是 |  |  |  |
| worker 仍写入 `asset_metadata.external_task_id` | 是 |  |  |  |
| worker 仍写入 `generated_by="worker_provider_executor"` | 是 |  |  |  |
| 成功物化后资产仍为 `status="materialized"` | 是 |  |  |  |
| `asset_metadata.materialization_status` 仍可能出现成功/对账态枚举 | 是 |  |  |  |
| 失败物化时仍可能留下 `status="failed"` 的资产 | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 11. Stage 6 Object Store Probe 契约检查

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| `RuntimeArtifactService` 仍无按 runtime_version 反查对象能力 | 是 |  |  |  |
| Stage 6 必须依赖 DB 已选 `(bucket_name, object_key)` 做 object probe | 是 |  |  |  |
| app 容器内 MinIO probe 路径仍可用 | 是 |  |  |  |
| object probe 返回结构仍包含 `objects: list` | 是 |  |  |  |
| 任一目标对象 `exists != True` 仍应视为 fail | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 12. Verdict 口径确认

| 检查项 | 预期 | 结果（√/×） | 证据 | 备注 |
|---|---|---:|---|---|
| 最终优先级仍为 `INCONCLUSIVE > DRIFT > FAIL > PASS` | 是 |  |  |  |
| 团队接受 `INCONCLUSIVE` 表示证据链断裂或响应不可判定 | 是 |  |  |  |
| 团队接受 `DRIFT` 表示环境基线漂移 | 是 |  |  |  |
| 团队接受 `FAIL` 表示业务证据充分失败 | 是 |  |  |  |
| 团队接受 `PASS` 仅在各层均满足要求时成立 | 是 |  |  |  |

**本段结论**：
- [ ] 通过
- [ ] 不通过
- 说明：`____________________________________________`

---

## 13. 风险接受记录

### 13.1 已知非阻塞风险

| 风险项 | 当前结论 | 是否接受（Y/N） | 备注 |
|---|---|---:|---|
| Stage 5 runtime asset association 仍依赖 `asset_metadata.runtime_version` | tentative metadata-backed，非强契约 |  |  |
| `_extract_probe_json_from_stdout()` 不支持从混杂日志中重组 pretty-printed 多行 JSON | 当前 probes 均为单行 JSON object，风险可接受 |  |  |
| `_extract_service_block()` 泛化稳健性一般 | 对当前 `docker-compose.yml` 结构匹配正常 |  |  |

### 13.2 禁止误判项

- 不得把 tentative asset association 误判为强外键约束。
- 不得把 warning-aware 项直接升级为 fail。
- 不得因 stored / derived 状态短暂不一致而直接判定 Stage 4 失败。
- 不得在首次执行前以“方便”为由引入脚本外 DB 修补动作。

---

## 14. 最终准入结论

### 14.1 总体判断

- [ ] 可进入首次真实执行
- [ ] 暂不建议执行
- [ ] 需先修复环境/契约漂移问题
- [ ] 需重新做一次静态契约复核

### 14.2 阻塞项列表

1. `____________________________________________`
2. `____________________________________________`
3. `____________________________________________`

### 14.3 非阻塞风险列表

1. `____________________________________________`
2. `____________________________________________`
3. `____________________________________________`

### 14.4 审核签字

- 检查人：`__________`
- 复核人：`__________`
- 结论日期：`____-__-__`

---

## 15. 推荐使用方式

建议本模板与以下文档配套使用：

- `docs/checklists/` 下既有只读检查清单
- `docs/runbooks/baseline_gate_first_real_execution_playbook.md`

推荐顺序：

1. 先完成本记录模板。
2. 记录所有 must-pass 与 warning-aware 项。
3. 结论为“可进入首次真实执行”后，再进入首次真实执行作战手册。
