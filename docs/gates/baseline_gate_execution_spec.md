# Baseline Gate Execution Spec

## 1. 文档目的

本文件定义 baseline gate 的执行规范，目标是为后续单入口验证脚本提供清晰约束，避免脚本作者再次踩入已知误区。

重点不是脚本实现细节，而是：

- 脚本必须检查什么
- 证据如何采集
- 哪些探测方式不可作为正式依据
- 最终如何输出 PASS / FAIL / DRIFT / INCONCLUSIVE

---

## 2. 脚本角色定义

建议未来实现两个脚本角色：

### 2.1 Orchestrator Script

负责串联全流程，例如：

- 环境预检
- health probe
- compile validate
- compile-dispatch 调用
- runtime 轮询
- DB evidence 汇总
- object-store probe
- verdict 输出

建议命名方向：

- `scripts/baseline_gate.py`
- 或 `scripts/verify_production_baseline.py`

### 2.2 Probe Helpers

负责可复用的低耦合探针逻辑，例如：

- HTTP probe helper
- DB query helper
- MinIO probe helper
- verdict formatter

---

## 3. 输入参数规范

未来 gate 脚本建议支持以下输入：

- `--project-id`
  - 默认值：`656ac6b1-ecb8-4f45-9f45-556be5915168`
- `--compile-reason`
  - 默认值：`manual_runtime_validation`
- `--mode`
  - 默认值：`manual_runtime_validation`
- `--timeout-seconds`
  - 默认值建议：`300`
- `--poll-interval-seconds`
  - 默认值建议：`5`
- `--output-json`
  - verdict JSON 输出路径
- `--output-md`
  - Markdown 摘要输出路径

脚本不得要求用户手输与当前基线冲突的 compose / DB / MinIO 参数；这些应尽量从当前受控环境中读取或固定。

---

## 4. 执行阶段规范

### Stage 0 — Baseline Freeze Precheck

必检项：

- repo root 正确
- `docker-compose` 可用
- 服务 `avr_app / avr_worker / avr_postgres / avr_redis / avr_minio` 均在运行
- migration 版本为 `20260330_0004`
- app 实际 settings 中 `google_image_model=imagen-4.0-fast-generate-001`
- smoke project 存在

输出：

- 若前提不成立，直接给 `DRIFT` 或 `FAIL`
- 不应继续进行 compile probe

### Stage 1 — Health Probe

推荐方式：

- 优先通过 app 容器内 Python probe 访问 `/health`
- 保留当前已验证方式：`cat tmp_*.py | docker exec -i avr_app python -`

通过条件：

- HTTP 200
- JSON 含 `status / app_env / target_market / target_language`

### Stage 2 — Compile Validate

必做：

- 请求 `GET /api/v1/compile/validate/{project_id}`
- 确认 `is_valid=true`
- 若有 warnings，可记录但不阻断
- 若 errors 非空，应给 `FAIL`

### Stage 3 — Compile Dispatch Probe

使用冻结 payload：

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

通过条件：

- compile 返回成功
- 取得新的 `runtime_id`
- 取得新的 `runtime_version`
- 返回体具备 `dispatch_summary`

### Stage 4 — Runtime Polling

脚本应轮询以下数据直到终态或超时：

- `compiled_runtimes`
- `jobs`
- `assets`

终态优先定义为：

- runtime `compile_status in {succeeded, failed}`
- 或 timeout

轮询过程中应记录：

- 当前 job 分布
- 是否出现 failed job
- runtime `last_error_code`
- asset 物化进度

### Stage 5 — DB Evidence Collection

终态后，应采集：

- runtime 记录
- 5 条 job 明细
- 4 类核心 asset 明细
- runtime 聚合摘要

这里必须注意：

- 不得假定 jobs 表存在 `runtime_version` 列
- 应使用 `payload.runtime_version` 做匹配

### Stage 6 — Object Store Probe

必须以 DB assets 作为对象探测来源：

- 从 asset 读取 `bucket_name`
- 从 asset 读取 `object_key`
- 用 app 容器内 MinIO Python probe 验证对象存在

不得使用以下方式作为正式判据：

- 未校验 alias / 凭据的 `mc stat local/...`
- 与 `settings` 不一致的 bucket 名
- 仅凭 DB 记录就判定对象存在

### Stage 7 — Verdict Rendering

最终必须产出：

- 一个结构化 JSON verdict
- 一个供人类审阅的 Markdown 摘要

---

## 5. 通过判定规范

脚本必须同时满足以下条件才可返回 `PASS`：

### 5.1 Precondition Pass

- baseline 未漂移
- 服务正常
- smoke project 合法
- compile validate 通过

### 5.2 Runtime Pass

- `compile_status = succeeded`
- `dispatch_status = fully_dispatched`
- `last_error_code = null`

### 5.3 Job Pass

- 总 job 数 = 5
- 标准 5 类 job 齐全
- 5 条均 `succeeded`
- 0 条 `failed`
- 每条 job 都有 `external_task_id`

### 5.4 Asset Pass

- 4 类核心 assets 齐全
- 4 条均 `materialized`
- bucket / object key / content type 合法

### 5.5 Object Store Pass

- 上述 4 个对象全部 probe 成功

---

## 6. 失败分类规范

### 6.1 `DRIFT`

适用场景：

- compose 基线被改动
- image model 不是 `imagen-4.0-fast-generate-001`
- 服务未齐
- migration 版本不符
- bucket 配置与实际约定不符

### 6.2 `FAIL`

适用场景：

- compile validate 不通过
- compile 请求失败
- 5 类 jobs 未全部创建
- 任意 job 最终 failed
- runtime 最终 failed
- assets 未全部 materialized
- object-store probe 不全通过

### 6.3 `INCONCLUSIVE`

适用场景：

- 探针脚本异常退出
- DB / HTTP / MinIO 其中一类证据未完成采集
- timeout 导致无法得出可靠终态
- 探测方法本身不可信

---

## 7. 特殊规则

### 7.1 不得误用 `dispatched_job_count`

脚本不得把以下条件作为 FAIL 依据：

- `runtime.compile_status = succeeded`
- 且 `dispatch_summary.dispatched_job_count = 0`

这是允许出现的终态，因为当前 runtime 聚合统计的是“当前仍处于 dispatched 状态的 job 数”，而不是“历史上曾被成功 dispatch 的 job 数”。

### 7.2 不得只看 compile 接口返回

compile API 返回中的 `compile_status` / `dispatch_status` 只能代表提交时刻或早期派发时刻状态，不能替代最终 runtime verdict。

### 7.3 不得绕过 object-store 核验

若没有对象存在性验证，就只能得到“部分证据成立”，不能给出 `PASS`。

---

## 8. 建议的输出文件

每次 gate 执行建议落地两个文件：

1. `outputs/baseline_gate_<timestamp>.json`
   - 机器可读 verdict

2. `outputs/baseline_gate_<timestamp>.md`
   - 人类可读审计摘要

若将来需要归档到 repo，可再把摘要复制到：

- `docs/gates/archive/`

---

## 9. 最小实现建议

为了降低首轮自动化风险，建议先做“半自动脚本”，而不是一次性全自动重构：

### 第一阶段

- 沿用现有 probe 方法
- 统一封装成单脚本
- 输出 verdict JSON + Markdown

### 第二阶段

- 抽离 helper 模块
- 做更稳健的 timeout / retry
- 引入更清晰的异常分类

### 第三阶段

- 再考虑接 CI 或 nightly gate

当前最重要的是：

**先保证 gate 口径一致，再追求自动化复杂度。**
