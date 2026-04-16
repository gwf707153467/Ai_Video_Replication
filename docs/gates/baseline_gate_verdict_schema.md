# Baseline Gate Verdict Schema

## 1. 文档目的

本文件定义 baseline gate 的标准输出结构，用于统一后续脚本、报告、审计记录与人工复核口径。

目标是让 gate 的最终结论不再停留在口头描述，而是能够稳定输出一份结构化 verdict。

---

## 2. 顶层字段

建议 verdict JSON 顶层结构如下：

```json
{
  "gate_name": "production_baseline_gate",
  "gate_version": "v1",
  "executed_at": "2026-03-30T19:30:00Z",
  "repo_root": "/mnt/user-data/workspace/Ai_Videos_Replication",
  "project_id": "656ac6b1-ecb8-4f45-9f45-556be5915168",
  "runtime_id": "9489a79a-6c84-455a-8699-94f3a5eb487c",
  "runtime_version": "v8",
  "verdict": "PASS",
  "summary": "Current frozen sandbox baseline remains repeatable.",
  "baseline_freeze": {},
  "compile_dispatch": {},
  "runtime_completion": {},
  "asset_materialization": {},
  "object_store": {},
  "evidence": {},
  "warnings": [],
  "drifts": [],
  "failures": []
}
```

---

## 3. 字段语义

### 3.1 基本身份字段

- `gate_name`
  - 固定建议值：`production_baseline_gate`

- `gate_version`
  - gate 规范版本，不等于 runtime version
  - 首版建议：`v1`

- `executed_at`
  - gate 执行完成时间，UTC ISO8601

- `repo_root`
  - 当前 gate 面向的仓库根目录

- `project_id`
  - 本轮 smoke project id

- `runtime_id`
  - 本轮新创建 runtime id；若 compile 前失败可为空

- `runtime_version`
  - 本轮新创建 runtime version；若 compile 前失败可为空

### 3.2 最终结论字段

- `verdict`
  - 枚举值：`PASS | FAIL | DRIFT | INCONCLUSIVE`

- `summary`
  - 一句摘要，说明本轮结论

---

## 4. 分层结果对象

### 4.1 `baseline_freeze`

建议结构：

```json
{
  "status": "pass",
  "checks": {
    "compose_command_locked": true,
    "compose_baseline_locked": true,
    "services_running": true,
    "migration_at_head": true,
    "google_image_model_locked": true,
    "smoke_project_exists": true
  }
}
```

语义：

- 描述冻结边界是否仍成立
- 对应 Layer A

### 4.2 `compile_dispatch`

建议结构：

```json
{
  "status": "pass",
  "compile_validate_passed": true,
  "compile_request_passed": true,
  "job_count": 5,
  "job_types": ["compile", "render_image", "render_video", "render_voice", "merge"],
  "initial_dispatch_status": "fully_dispatched"
}
```

语义：

- 描述 compile 与 dispatch 阶段是否成立
- 对应 Layer B

### 4.3 `runtime_completion`

建议结构：

```json
{
  "status": "pass",
  "compile_status": "succeeded",
  "dispatch_status": "fully_dispatched",
  "job_count": 5,
  "succeeded_job_count": 5,
  "failed_job_count": 0,
  "last_error_code": null
}
```

语义：

- 描述 runtime 与 jobs 的终态
- 对应 Layer C

### 4.4 `asset_materialization`

建议结构：

```json
{
  "status": "pass",
  "required_asset_types": ["generated_image", "generated_video", "audio", "export"],
  "materialized_asset_count": 4,
  "assets": [
    {
      "asset_type": "generated_image",
      "bucket_name": "generated-images",
      "object_key": "projects/...png",
      "content_type": "image/png",
      "status": "materialized"
    }
  ]
}
```

语义：

- 描述 DB asset 层是否完整
- 对应 Layer D 的前半段

### 4.5 `object_store`

建议结构：

```json
{
  "status": "pass",
  "probe_method": "app_container_minio_python_probe",
  "checked_object_count": 4,
  "existing_object_count": 4,
  "objects": [
    {
      "bucket_name": "generated-images",
      "object_key": "projects/...png",
      "exists": true,
      "size": 480106,
      "content_type": "image/png"
    }
  ]
}
```

语义：

- 描述对象存储实物核验结果
- 对应 Layer D 的后半段

---

## 5. 证据区字段

建议 `evidence` 字段至少包含：

```json
{
  "health_response": {
    "status": "ok",
    "app_env": "development",
    "target_market": "US",
    "target_language": "en-US"
  },
  "alembic_version": "20260330_0004",
  "settings_snapshot": {
    "google_image_model": "imagen-4.0-fast-generate-001"
  },
  "runtime_dispatch_summary": {},
  "jobs": [],
  "assets": []
}
```

说明：

- `health_response`：记录 `/health` 实际返回
- `alembic_version`：记录 schema 基线
- `settings_snapshot`：记录关键冻结配置
- `runtime_dispatch_summary`：记录 runtime 聚合摘要
- `jobs`：保留本轮 5 条 jobs 明细
- `assets`：保留本轮 4 类核心 assets 明细

---

## 6. 警告 / 漂移 / 失败数组

### 6.1 `warnings`

用于记录不阻断 PASS 的信息，例如：

- compile validate warnings
- 非关键字段缺失但不影响主结论
- `dispatch_summary.dispatched_job_count = 0` 的终态说明

### 6.2 `drifts`

用于记录环境漂移，例如：

- image model 发生变化
- compose 命令不符合约束
- 服务名或 bucket 配置发生偏移

若 `drifts` 非空且影响冻结边界，推荐最终 verdict 为 `DRIFT`。

### 6.3 `failures`

用于记录实际失败项，例如：

- compile validate failed
- runtime failed
- missing required asset type
- object does not exist

若 `failures` 非空且非单纯证据不足，推荐最终 verdict 为 `FAIL`。

---

## 7. Verdict 决策规则

建议脚本按以下优先级决策：

1. 若证据缺失严重或探针异常 -> `INCONCLUSIVE`
2. 若冻结边界漂移 -> `DRIFT`
3. 若边界成立但任一关键层失败 -> `FAIL`
4. 四层全部通过 -> `PASS`

---

## 8. Markdown 摘要最低要求

除 JSON verdict 外，建议始终生成一份 Markdown 摘要，最低应包含：

1. 本轮 runtime 身份
2. 最终 verdict
3. 四层 gate 结果
4. 5 条 jobs 摘要表
5. 4 类 assets 摘要表
6. object store probe 摘要表
7. warnings / drifts / failures
8. 一句话结论

---

## 9. 首版实践建议

首版脚本实现时，不必追求复杂 schema 校验器；只要确保：

- 字段稳定
- 语义一致
- 可复用
- 可审计

就已经足够支撑当前仓库的 baseline governance。
