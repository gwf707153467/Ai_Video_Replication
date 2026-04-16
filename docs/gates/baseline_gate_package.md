# Baseline Gate Package

## 1. 文档目的

本规范包用于把现有两类材料正式收敛为一个可执行的 baseline gate：

- `docs/checklists/production_baseline_verification_checklist.md`
- `docs/repeatability_report_v8.md`

收敛目标不是再写一份重复报告，而是把当前已经验证过的最小生产基线，转为后续每次都可重复执行、可审计、可判定 PASS / FAIL / DRIFT 的统一门禁。

本规范包只覆盖当前冻结边界，不扩展新功能、不改 provider 主逻辑、不回退 compose 基线、不重开主链路排障。

---

## 2. 规范包组成

本 baseline gate package 由三部分组成：

1. **主门禁文档**
   - `docs/gates/baseline_gate_package.md`
   - 定义门禁目标、适用边界、分层验收、判定原则、执行顺序。

2. **执行与脚本规范**
   - `docs/gates/baseline_gate_execution_spec.md`
   - 定义未来单入口 probe / verifier 脚本应如何运行、采集哪些证据、如何避免误判。

3. **结构化判定输出契约**
   - `docs/gates/baseline_gate_verdict_schema.md`
   - 定义 gate 输出 JSON / Markdown verdict 的字段语义，便于后续脚本化与审计。

---

## 3. 收敛来源

本规范包基于以下已验证事实收敛：

### 3.1 Checklist 提供的内容

`production_baseline_verification_checklist.md` 提供的是：

- 冻结边界
- 核对项全集
- 运行前置条件
- runtime / jobs / assets / object store 的多平面验收框架

它的优点是覆盖全，但偏人工检查视角。

### 3.2 v8 Report 提供的内容

`repeatability_report_v8.md` 提供的是：

- 一次完整 repeatability 成功样本
- `v8` 的 runtime / job / asset / object-store 实证数据
- 一个重要误判纠偏：`dispatch_summary.dispatched_job_count` 在 succeeded 终态回落为 `0` 不应被视为失败
- 一个重要探测纠偏：不得把 `avr_minio` 容器中的 `mc stat local/...` 作为主验收依据

它的优点是证据强，但偏一次样本报告视角。

### 3.3 本次收敛的结果

本规范包把两者合并为：

- **Checklist 的完整性**
- 加上 **v8 report 的实证口径与误判纠偏**
- 最终形成 **可执行 gate**

---

## 4. Baseline Gate 的正式目标

本 gate 的目标只有一个：

**判定当前冻结沙箱环境是否仍具备“可重复的最小生产基线能力”。**

这里的“通过”不等于：

- 长期稳定性证明
- 多项目泛化证明
- 压测证明
- provider 长期 SLA 证明

这里的“通过”仅表示：

- 当前固定仓库
- 当前固定 compose 基线
- 当前固定 provider 主逻辑
- 当前固定 smoke project
- 当前固定 image model `imagen-4.0-fast-generate-001`

在这些前提下，系统仍可再次跑通：

`compile -> dispatch -> worker execution -> asset materialization -> runtime aggregation -> object-store verification`

---

## 5. 适用边界

本 gate 仅适用于以下冻结边界：

- repo root：`/mnt/user-data/workspace/Ai_Videos_Replication`
- compose 操作：仅使用 `docker-compose`
- 禁止恢复 `app` / `worker` 的 `.:/workspace` bind mount
- `app` command：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
- `worker` command：`celery -A app.workers.celery_app worker --loglevel=INFO`
- startup 不自动跑 migration
- DB 查询固定使用：
  - user=`postgres`
  - db=`ai_videos_replication`
- provider 主逻辑保持不变
- image model 固定为：`imagen-4.0-fast-generate-001`
- 对象存储验证优先使用：
  - app 容器内
  - 基于 `app.core.config.settings`
  - MinIO Python probe

如果执行时发现边界漂移，gate 不应直接给 PASS，而应先进入 DRIFT 判定。

---

## 6. 成功锚点与最小证据要求

### 6.1 锚点作用

当前已存在两个成功样本：

- `v7`：冻结成功锚点
- `v8`：repeatability 成功样本

这两个样本的作用不是要求未来重复使用相同 runtime id，而是证明当前仓库已经满足过至少两次完整闭环成功。

### 6.2 后续 gate 的最小证据要求

未来每次 baseline gate 执行时，至少要生成并验证一轮新的 runtime，并完成以下四层闭环：

1. runtime 层
2. jobs 层
3. assets 层
4. object store 层

若只停留在 compile 200、runtime 创建成功、或部分 jobs 成功，均不得判定 baseline gate 通过。

---

## 7. 四层门禁模型

### 7.1 Layer A — Baseline Freeze Gate

用于确认环境没有漂移。

必检项：

- compose 基线未回退
- 容器服务齐全且在运行
- migration 已到 `20260330_0004`
- `.env` 生效
- `GOOGLE_IMAGE_MODEL=imagen-4.0-fast-generate-001`
- smoke project 仍存在

若此层失败，结论优先为 `DRIFT` 或 `FAIL_PRECONDITION`，而不是直接进入主链路故障分析。

### 7.2 Layer B — Compile / Dispatch Gate

用于确认新 runtime 可被创建并正确派发。

通过条件：

- compile 请求成功
- runtime_version 成功递增
- 创建 5 类标准 jobs
- 每个 job payload 带 `runtime_version`
- 成功派发的 job 拿到 `external_task_id`
- 初始 `dispatch_status=fully_dispatched` 或明确记录部分派发失败

### 7.3 Layer C — Runtime / Job Completion Gate

用于确认 worker 主链路闭环成功。

通过条件：

- 5 个标准 jobs 最终全部 `succeeded`
- `failed_job_count = 0`
- runtime 最终 `compile_status = succeeded`
- runtime 最终 `dispatch_status = fully_dispatched`
- runtime 非 failed 时 `last_error_code = null`

### 7.4 Layer D — Asset / Object Store Materialization Gate

用于确认结果不只是数据库成功，而是真正物化成功。

通过条件：

- DB 中存在 4 类核心 asset：
  - `generated_image`
  - `generated_video`
  - `audio`
  - `export`
- 4 类 assets 均为 `materialized`
- `bucket_name` / `object_key` / `content_type` 与 contract 一致
- MinIO 中对应对象可被实际 probe 到

只有四层都通过，baseline gate 才能给出 `PASS`。

---

## 8. 正式判定枚举

本 gate 统一只输出以下四类高层 verdict：

- `PASS`
  - 四层全部通过，当前环境仍具备可重复的最小生产基线能力。

- `FAIL`
  - 环境前提基本成立，但 runtime / jobs / assets / object store 中至少一层未满足通过条件。

- `DRIFT`
  - 环境已偏离冻结边界，例如 compose 基线漂移、image model 漂移、服务缺失、migration 未到位、错误 bucket 配置等。

- `INCONCLUSIVE`
  - 证据采集不完整或探针本身失效，暂不能作出可靠结论。

---

## 9. 明确的非通过情形

以下情况均不得判定 `PASS`：

1. 只有 `/health` 成功
2. 只有 compile API 返回 200
3. 只有 runtime 被创建
4. 只有 job 被 dispatch，但未全部完成
5. jobs 已成功，但缺少 asset materialization
6. DB 中 asset 成功，但对象存储未验证
7. object-store probe 使用错误 bucket、错误 alias 或错误凭据，导致证据不可靠
8. 依赖 `compiled_runtimes.dispatch_summary.dispatched_job_count == 0` 就误判 repeatability 失败

---

## 10. 明确的纠偏规则

### 10.1 关于 `dispatched_job_count`

`compiled_runtimes.dispatch_summary.dispatched_job_count` 在 compile 初始写入与 runtime 终态聚合中的语义不同：

- compile 阶段：更接近“已拿到 external_task_id 的 job 数”
- runtime 聚合终态：更接近“当前仍处于 dispatched 状态的 job 数”

因此：

- 在 runtime 进入 `succeeded` 后，该字段可合法回落为 `0`
- 不能以该字段单独作为 repeatability 失败证据
- dispatch 通过与否，应结合：
  - job 是否存在
  - job 是否有 `external_task_id`
  - `dispatch_status`
  - 最终 `succeeded_job_count`

### 10.2 关于对象存储验证

对象存储验证必须遵守以下顺序：

1. 从 DB asset 记录读取 `bucket_name + object_key`
2. 使用 app 容器内、基于运行时 settings 的 MinIO probe
3. 以对象实际可访问 / 可 stat 为主证据

不得优先使用：

- `avr_minio` 容器内未校验 alias 的 `mc stat local/...`
- 历史 bucket 名猜测
- 与当前 settings 不一致的 probe 方式

---

## 11. 推荐执行顺序

建议每次 gate 按以下顺序执行：

1. 预检冻结边界
2. 健康检查与服务检查
3. compile validate
4. compile-dispatch probe
5. 轮询 runtime / jobs 至终态
6. 查询 assets
7. 逐项执行 object store probe
8. 生成 verdict JSON
9. 生成审计 Markdown 摘要

---

## 12. 与现有文档的关系

本 package 不替代下列文档，而是把它们提升为门禁输入材料：

- runbook：负责操作步骤
- contracts：负责字段语义与实现口径
- checklist：负责核对全集
- v8 report：负责提供已验证成功样本和纠偏经验

关系可概括为：

- runbook / contracts / checklist / report = 事实来源
- gate package = 门禁执行规范

---

## 13. 下一步自动化落地方向

本规范包已把人工验收口径收敛完成。后续若进入脚本化，建议只做两件事：

1. 实现单入口 verifier 脚本
   - 输入：project_id、可选 timeout、可选 poll interval
   - 输出：结构化 verdict JSON + Markdown 摘要

2. 实现 gate shell 包装器
   - 固定在 repo root 下运行
   - 固定使用 `docker-compose`
   - 固定通过 app 容器内 probe 完成 HTTP / MinIO / DB 相关校验

这两步完成后，当前 baseline gate 就可以从“人工可执行”提升到“半自动可执行”。
