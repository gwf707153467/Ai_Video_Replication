# Production Baseline Verification Checklist

## 1. 文档目的

本 checklist 用于把当前已经冻结的 smoke 成功基线，进一步收敛为一套可重复、可审计、可交接的 production-baseline 验证清单。

这里的“production baseline”不是指已经进入真实生产放量，而是指：

- 当前仓库主链路在沙箱内具备稳定复核入口
- compose / API / worker / DB / Redis / MinIO / provider 基线已经被明确冻结
- compile → dispatch → worker → asset materialization → runtime aggregation 这条主链路有统一验收口径
- 文档、运行事实、数据库事实、对象存储事实之间可以闭环
- 后续所有增量改动，都可以先对照本清单进行回归核验

本 checklist 明确服务于当前主线：

- 不重开 provider 排障
- 不回退 compose 基线
- 不把一次 smoke 成功误判为长期稳定性证明
- 先验证“可重复的最小生产基线”，再进入更高阶 repeatability / governance 扩展

---

## 2. 适用边界

本清单仅适用于当前冻结实现范围：

- repo root：`/mnt/user-data/workspace/Ai_Videos_Replication`
- compose 命令：仅使用 `docker-compose`
- app command：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
- worker command：`celery -A app.workers.celery_app worker --loglevel=INFO`
- 不允许恢复 `app` / `worker` 的 `.:/workspace` bind mount
- startup 不自动跑 Alembic migration
- DB 查询固定使用：
  - user：`postgres`
  - database：`ai_videos_replication`
- provider 主逻辑保持不变
- image model 冻结为：`imagen-4.0-fast-generate-001`

若执行时发现环境偏离以上前提，应先恢复基线，再继续验证；不要把基线漂移与功能缺陷混为一谈。

---

## 3. 基线锚点

### 3.1 冻结成功锚点

当前正式冻结的成功锚点为 runtime `v7`：

- `runtime_id = 9c5a8e97-924a-475e-91a1-c3db0a60571b`
- `compile_status = succeeded`
- `dispatch_status = fully_dispatched`
- `job_count = 5`
- `succeeded_job_count = 5`
- `failed_job_count = 0`

对应 smoke project：

- `project_id = 656ac6b1-ecb8-4f45-9f45-556be5915168`
- `sequence_id = 7226dad0-a05f-411b-9acf-ac15a3128f4c`
- `spu_id = 31431873-86b2-4adb-aeaf-78f6067335d8`
- `name = eighth-batch-render-image-smoke`

### 3.2 成功锚点的用途

后续验证时，`v7` 不是要求每次重复使用的 runtime_version，而是用于确认以下事实已经在当前仓库实现中成立过：

- compile API 可成功创建 runtime
- dispatch 逻辑可成功生成并派发 5 类 jobs
- worker 可跑通 render_image / render_video / render_voice / merge
- runtime 最终可聚合到 `succeeded`
- 生成产物可落到 MinIO，并在 `assets` 中形成 materialized 记录

因此，本清单的目标不是“复现同一个 v7”，而是“验证当前环境仍具备复现 v7 成功条件的能力”。

---

## 4. 验收总原则

在执行本 checklist 时，统一采用以下验收原则：

1. **运行时事实优先于文档假设**
   - 以当前容器、DB、API 返回、MinIO 对象状态为准。

2. **冻结基线优先于历史笔记**
   - 若旧文档与当前实现冲突，以当前已验证 runbook / contracts / 源码为准。

3. **最小闭环优先于扩展覆盖**
   - 先验证主链路闭环，再谈增强项。

4. **记录偏差，不临场扩修**
   - 本清单主要用于验证，不用于现场扩展实现。

5. **成功必须是多平面一致成功**
   - API 成功、job 成功、runtime 聚合成功、asset 成功、对象存在，缺一不可。

---

## 5. 文档面核对项

在执行实际 probe 之前，先确认以下文档面基线已经就位：

- [ ] `docs/runbooks/baseline_smoke_runbook.md` 已存在
- [ ] `docs/contracts/runtime_state_contract.md` 已存在
- [ ] `docs/contracts/job_contract.md` 已存在
- [ ] `docs/contracts/compile_api_contract.md` 已存在
- [ ] 以上文档内容与当前源码主线一致，没有继续引用 `imagen-3.0-generate-002` 作为现行基线
- [ ] 文档已明确 `v7` 为冻结成功锚点
- [ ] 文档已明确 compile API 只覆盖提交时刻语义，不等于最终 runtime 聚合结果

通过标准：四份文档齐备，且可作为 smoke / 验证 / 审计统一入口。

---

## 6. 环境冻结核对项

### 6.1 仓库与命令约束

- [ ] 当前工作目录为 `/mnt/user-data/workspace/Ai_Videos_Replication`
- [ ] 后续 compose 操作仅使用 `docker-compose`
- [ ] 未在执行计划中使用 `docker compose`
- [ ] 已知 `docker exec` 默认 cwd 为 `/workspace`
- [ ] 容器内 HTTP 探测优先使用 `cat tmp_*.py | docker exec -i avr_app python -`

### 6.2 compose 基线约束

- [ ] `docker-compose.yml` 未恢复 `app` / `worker` 的 `.:/workspace` bind mount
- [ ] `app` command 仍为 `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- [ ] `worker` command 仍为 `celery -A app.workers.celery_app worker --loglevel=INFO`

### 6.3 provider / env 约束

- [ ] `.env` 已生效
- [ ] `GOOGLE_API_KEY` 已配置
- [ ] `GOOGLE_IMAGE_MODEL=imagen-4.0-fast-generate-001`
- [ ] 未擅自修改 `app/providers/google/client.py` 主逻辑
- [ ] 未把本轮验证重新转为 provider 排障任务

通过标准：环境前提与冻结约束没有漂移。

---

## 7. 服务面核对项

### 7.1 compose 服务状态

- [ ] `avr_app` 运行中
- [ ] `avr_worker` 运行中
- [ ] `avr_postgres` 运行中
- [ ] `avr_redis` 运行中
- [ ] `avr_minio` 运行中

### 7.2 健康检查

- [ ] `/health` 返回 HTTP 200
- [ ] `/health` 返回字段包含：
  - [ ] `status`
  - [ ] `app_env`
  - [ ] `target_market`
  - [ ] `target_language`

### 7.3 migration 状态

- [ ] startup 未假定自动执行 migration
- [ ] 当前 DB migration 已显式执行到 head
- [ ] `alembic_version.version_num = 20260330_0004`

通过标准：应用、worker、基础依赖与 schema 状态均可支撑 smoke 执行。

---

## 8. 数据面核对项

### 8.1 schema 存在性

- [ ] public schema 中存在以下表：
  - [ ] `alembic_version`
  - [ ] `assets`
  - [ ] `bridges`
  - [ ] `compiled_runtimes`
  - [ ] `jobs`
  - [ ] `projects`
  - [ ] `sequences`
  - [ ] `spus`
  - [ ] `vbus`

### 8.2 schema / 代码差异已被显式认知

- [ ] `jobs` 表中不存在 `last_error_code`
- [ ] `jobs` 表中不存在 `runtime_version` 列
- [ ] `assets` 表中不存在 `storage_bucket`
- [ ] runtime 与 jobs 的关联键理解为：`project_id + payload.runtime_version`

### 8.3 smoke 项目存在性

- [ ] project `656ac6b1-ecb8-4f45-9f45-556be5915168` 存在
- [ ] sequence `7226dad0-a05f-411b-9acf-ac15a3128f4c` 存在
- [ ] SPU `31431873-86b2-4adb-aeaf-78f6067335d8` 存在
- [ ] smoke project 至少满足 compile validator 的最小通过条件

通过标准：DB 结构与 smoke 数据能够支撑 compile / dispatch / asset 闭环。

---

## 9. API 合约核对项

### 9.1 compile validate

- [ ] `GET /api/v1/compile/validate/{project_id}` 可访问
- [ ] project 存在时可返回：
  - [ ] `project_id`
  - [ ] `is_valid`
  - [ ] `errors[]`
  - [ ] `warnings[]`
  - [ ] `counts{}`
- [ ] 若 errors 为空，则 `is_valid=true`
- [ ] warning 不阻断 compile

### 9.2 compile 请求模型

- [ ] `POST /api/v1/compile` 接受如下字段：
  - [ ] `project_id`
  - [ ] `runtime_version | null`
  - [ ] `compile_reason`
  - [ ] `compile_options`
  - [ ] `auto_version`
  - [ ] `dispatch_jobs`

### 9.3 runtime version 解析

- [ ] 仅当 `runtime_version` 非空且 `auto_version=false` 时，才直接采用传入版本
- [ ] 默认路径为自动生成下一个版本号

### 9.4 错误语义

- [ ] `project_not_found -> 404`
- [ ] `project_invalid -> 422`

通过标准：API 契约与文档、源码、探针脚本三者一致。

---

## 10. Compile 执行核对项

### 10.1 推荐 smoke 请求

建议使用当前冻结 smoke payload：

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

### 10.2 创建期验收项

- [ ] compile 请求返回 200
- [ ] 返回体可解析为 `CompiledRuntimeRead`
- [ ] 返回 `project_id` 与 smoke project 一致
- [ ] `runtime_version` 已自动递增
- [ ] `runtime_payload` 非空
- [ ] `dispatch_summary` 非空

### 10.3 runtime_payload 最小验收项

- [ ] 包含 `project_id`
- [ ] 包含 `runtime_version`
- [ ] 包含 `compile_reason`
- [ ] 包含 `compile_options`
- [ ] 包含 `visual_track_count`
- [ ] 包含 `audio_track_count`
- [ ] 包含 `bridge_count`
- [ ] 包含 `sequences[]`

通过标准：compile API 可稳定创建新的 runtime 快照，且返回结构完整。

---

## 11. Dispatch 核对项

### 11.1 job 创建与类型

- [ ] `dispatch_jobs=true` 后创建 5 条 jobs
- [ ] 5 类 job 必须齐全：
  - [ ] `compile`
  - [ ] `render_image`
  - [ ] `render_video`
  - [ ] `render_voice`
  - [ ] `merge`

### 11.2 payload 最小字段

- [ ] 每条 job payload 均含 `runtime_version`
- [ ] 每条 job payload 均含 `dispatch_source="compile_endpoint"`
- [ ] `render_image` payload 额外包含：
  - [ ] `prompt`
  - [ ] `negative_prompt`
  - [ ] `provider_inputs`

### 11.3 dispatch 成功条件

- [ ] 成功 dispatch 的 job 已写入 `external_task_id`
- [ ] 成功 dispatch 的 job 已写入 `result_payload.celery_task_id`
- [ ] 成功 dispatch 的 job 状态为 `dispatched`
- [ ] `dispatch_summary.job_count = 5`
- [ ] `dispatch_summary.dispatched_job_count` 与实际 dispatched 数量一致

### 11.4 dispatch 状态语义

- [ ] 全部派发成功时 `dispatch_status = fully_dispatched`
- [ ] 若仅部分派发成功，则 `dispatch_status = partially_dispatched`
- [ ] 当前实现中 dispatch 状态不扩展为更多枚举值

通过标准：compile 后的异步执行入口完整且可审计。

---

## 12. Worker 生命周期核对项

### 12.1 状态流转

- [ ] job 生命周期可观察到：`queued/dispatched -> running -> succeeded|failed`
- [ ] `_mark_job_running()` 会：
  - [ ] `attempt_count += 1`
  - [ ] 写 `started_at`
  - [ ] 清空 `error_code/error_message`
- [ ] `_mark_job_succeeded()` 会写 `finished_at`
- [ ] `_mark_job_failed()` 会写 `finished_at`

### 12.2 成功结果最小字段

- [ ] 成功 `result_payload` 至少包含：
  - [ ] `job_id`
  - [ ] `project_id`
  - [ ] `runtime_version`
  - [ ] `status`
  - [ ] `task`
  - [ ] `provider`
  - [ ] `worker_finished_at`
  - [ ] `provider_payload`

### 12.3 失败结果语义

- [ ] worker 执行失败时 job 状态为 `failed`
- [ ] 失败错误码固定为 `worker_execution_failed`
- [ ] `result_payload` 补入：
  - [ ] `error_code`
  - [ ] `error_message`
  - [ ] `worker_finished_at`

通过标准：worker job 生命周期、结果结构、错误落库口径一致。

---

## 13. Runtime 聚合核对项

### 13.1 聚合关联键

- [ ] runtime summary 按 `project_id + payload.runtime_version` 聚合 jobs
- [ ] 当前核查的 jobs 全部命中同一 runtime_version

### 13.2 summary 最小字段

- [ ] `dispatch_summary` 包含：
  - [ ] `runtime_version`
  - [ ] `job_count`
  - [ ] `queued_job_count`
  - [ ] `dispatched_job_count`
  - [ ] `running_job_count`
  - [ ] `succeeded_job_count`
  - [ ] `failed_job_count`
  - [ ] `jobs[]`

### 13.3 compile_status 推导

- [ ] `job_count == 0` 时保持当前值
- [ ] `failed_job_count > 0` 时为 `failed`
- [ ] `succeeded_job_count == job_count` 时为 `succeeded`
- [ ] 存在 active jobs（`queued|dispatched|running`）时为 `running`

### 13.4 dispatch_status 推导

- [ ] `job_count == 0` 时保持当前值
- [ ] `dispatched_or_beyond == 0` 时为 `not_dispatched`
- [ ] `< job_count` 时为 `partially_dispatched`
- [ ] `== job_count` 时为 `fully_dispatched`

### 13.5 runtime 错误字段

- [ ] 若存在 failed jobs，`last_error_code` 取最后一个 failed job 的 `error_code`
- [ ] runtime 非 failed 时会清空 `last_error_code/last_error_message`

通过标准：runtime 聚合状态与 jobs 实际状态一致，不出现文档与数据库口径冲突。

---

## 14. Asset / 对象存储核对项

### 14.1 asset 类型与 bucket 映射

- [ ] `generated_image -> generated_images`
- [ ] `generated_video -> generated_videos`
- [ ] `audio -> audio`
- [ ] `export -> exports`

### 14.2 成功产物最小覆盖

当本轮 runtime 成功时，`assets` 中应至少看到以下 materialized 产物类型：

- [ ] `generated_image`
- [ ] `generated_video`
- [ ] `audio`
- [ ] `export`

### 14.3 materialization 状态

- [ ] 成功 asset 状态为 `materialized`
- [ ] `notes = "sixth_batch_materialization_backbone"`
- [ ] `asset_metadata` 至少可包含：
  - [ ] `runtime_version`
  - [ ] `job_id`
  - [ ] `job_type`
  - [ ] `external_task_id`
  - [ ] `generated_by = "worker_provider_executor"`

### 14.4 对象路径验收

- [ ] runtime 产物 object key 服从：`projects/{project_id}/runtime/{runtime_version}/{job_type}/{safe_filename}`
- [ ] `render_image` 默认文件名为 `{job_id}.png`
- [ ] `render_video` 默认文件名为 `{job_id}.mp4`
- [ ] `render_voice` 默认文件名为 `{job_id}.wav`
- [ ] `merge` 默认文件名为 `{runtime_version}-{job_id}.mp4`

### 14.5 对象存在性

- [ ] MinIO 中对应对象实际存在
- [ ] 数据库 asset 记录与对象路径一致
- [ ] 未发生 DB 记录成功但对象缺失的断裂

通过标准：数据库记录、对象存储、runtime/job 语义形成完整闭环。

---

## 15. 成功判定标准

只有同时满足以下条件，才能判定“当前 production baseline 验证通过”：

- [ ] 环境冻结项全部通过
- [ ] 服务面全部通过
- [ ] 数据面全部通过
- [ ] compile API 合约全部通过
- [ ] 新 runtime 已成功创建
- [ ] 5 条 jobs 已创建并完成期望派发
- [ ] runtime 最终聚合为：
  - [ ] `compile_status = succeeded`
  - [ ] `dispatch_status = fully_dispatched`
  - [ ] `succeeded_job_count = 5`
  - [ ] `failed_job_count = 0`
- [ ] `assets` 中存在至少 4 类 materialized 产物
- [ ] MinIO 对象路径与 DB 记录一致
- [ ] 本轮结果与 `v7` 冻结锚点不存在方向性冲突

注意：

- 若 compile 请求返回 200，但 runtime 最终未聚合到成功，不算通过。
- 若 jobs 全成功，但 asset 未 materialize，不算通过。
- 若 asset 存在，但聚合状态或关联键错误，也不算通过。

---

## 16. 失败分类与处理原则

当验证未通过时，只做分类与记录，不在本 checklist 内直接扩修。

### 16.1 基线漂移

示例：

- compose 命令被换成 `docker compose`
- bind mount 被恢复
- provider 主逻辑被改动
- `.env` 中 image model 被替换

处理原则：先恢复冻结基线，再重新验证。

### 16.2 环境未就绪

示例：

- compose 服务未启动
- migration 未到 head
- smoke project 缺失

处理原则：先补环境就绪项，再重新验证。

### 16.3 API / compile 不一致

示例：

- 返回模型字段缺失
- validate/compile 错误码与 contract 不一致

处理原则：记录 contract 偏差，进入后续 contract 修订或实现修复流程。

### 16.4 worker / provider / materialization 失败

示例：

- job failed
- runtime failed
- asset 注册成功但对象不存在

处理原则：记录失败 runtime、job_id、asset/object_key、错误码，不在本清单中继续扩链排障。

---

## 17. Repeatability 记录模板

每次执行本 checklist，建议至少记录以下字段：

| 字段 | 示例 | 说明 |
|---|---|---|
| verification_date | 2026-03-30 | 执行日期 |
| operator | sandbox-agent | 执行者 |
| repo_root | /mnt/user-data/workspace/Ai_Videos_Replication | 仓库路径 |
| compose_mode | docker-compose | compose 命令口径 |
| migration_version | 20260330_0004 | schema 版本 |
| smoke_project_id | 656ac6b1-ecb8-4f45-9f45-556be5915168 | smoke 项目 |
| runtime_version | v8 | 本次新生成版本 |
| compile_status | succeeded | runtime 最终编译状态 |
| dispatch_status | fully_dispatched | runtime 最终派发状态 |
| job_count | 5 | job 总数 |
| succeeded_job_count | 5 | 成功 job 数 |
| failed_job_count | 0 | 失败 job 数 |
| generated_asset_types | generated_image,generated_video,audio,export | 成功产物类型 |
| anchor_comparison | consistent_with_v7 | 与冻结锚点比对结论 |
| notes | no baseline drift detected | 备注 |

---

## 18. 与现有文档的关系

本 checklist 与其他文档的关系如下：

- `docs/runbooks/baseline_smoke_runbook.md`
  - 负责说明如何执行 smoke
- `docs/contracts/compile_api_contract.md`
  - 负责定义 compile API 请求/响应/错误语义
- `docs/contracts/job_contract.md`
  - 负责定义 job 生命周期、payload、result_payload、materialization 契约
- `docs/contracts/runtime_state_contract.md`
  - 负责定义 runtime summary、compile_status、dispatch_status 聚合口径

使用顺序建议：

1. 先看本 checklist，明确要验什么
2. 再看 runbook，明确怎么跑
3. 若发现偏差，再对照 contract 判断是实现问题还是认知问题

---

## 19. 当前结论

截至当前冻结节点，可以把本仓库的最小 production baseline 暂定为：

- compose 基线已修复并冻结
- compile / dispatch / worker / runtime aggregation / asset materialization 主链路已存在成功锚点
- `imagen-4.0-fast-generate-001` 是当前有效 image model 基线
- `v7` 是已验证成功的参考锚点
- 本 checklist 可作为后续 repeatability report、回归门禁和主线增量开发前的统一验收入口

若未来继续推进，推荐所有新增工程动作都先回答两个问题：

1. 是否破坏了本 checklist 的冻结前提？
2. 是否仍能通过本 checklist 的闭环验收？
