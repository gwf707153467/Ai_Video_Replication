# `baseline_gate.py` 首次真实执行作战手册

## 1. 文档目的

本手册用于指导 `scripts/baseline_gate.py` 的**首次真实执行**前、中、后的组织方式、观察口径与结果解释方法。

本手册的目标不是替代实际执行，也不是扩写脚本逻辑，而是确保首次执行时：

- 执行边界不漂移
- 观察重点不失焦
- `PASS / FAIL / DRIFT / INCONCLUSIVE` 的解释口径一致
- 不把环境问题、契约问题、证据链问题混为一谈

---

## 2. 适用范围与固定边界

### 2.1 适用范围

- 适用于 `scripts/baseline_gate.py` 的首次真实执行。
- 适用于当前 sandbox / docker-compose / Linux 环境。
- 适用于当前已确认的 compile API、CompilerService、Stage 4/5 ORM 与 runtime-evidence 契约。

### 2.2 固定边界

- 不在执行过程中改写 `baseline_gate.py`。
- 不在执行过程中主动 refresh runtime 聚合状态。
- 不把 Stage 4 的观察逻辑替换成脚本外人工 DB 操作。
- 不把 Stage 5 的 tentative metadata 关联升级为强契约。
- 不从对象存储按 runtime_version 反查对象；Stage 6 必须继续基于 DB 已选对象做 probe。

### 2.3 当前已确认真实契约摘要

#### compile API

- `POST /api/v1/compile` -> `CompiledRuntimeRead`
- `GET /api/v1/compile/validate/{project_id}` -> `CompileValidationRead`
- `project_not_found -> 404`
- `project_invalid -> 422`
- `CompileRequest.project_id` 为 `UUID`

#### CompilerService

- `dispatch_jobs=True` 时创建固定 5 类 jobs：
  - `compile`
  - `render_image`
  - `render_video`
  - `render_voice`
  - `merge`
- 所有 jobs 初始为 `queued`
- `dispatch_service.dispatch(...)` 成功返回 `task_id` 时，job 进入 `dispatched`
- 所有 job 均拿到 `task_id` 时，dispatch summary 为 `fully_dispatched`

#### Stage 4 成功条件

- `derived_compile_status == "succeeded"`
- `derived_dispatch_status == "fully_dispatched"`

#### Stage 5 资产口径

- `compile` 不创建资产
- `render_image -> generated_image`
- `render_video -> generated_video`
- `render_voice -> audio`
- `merge -> export`
- required asset types：
  - `generated_image`
  - `generated_video`
  - `audio`
  - `export`

---

## 3. 执行总原则

### 3.1 原则一：先冻结，再执行

只有当环境、契约、配置、服务状态都确认稳定后，才进入首次真实执行。

### 3.2 原则二：先解释契约，再解释结果

出现异常时，优先判断是：

- 环境基线漂移
- API / ORM / worker 契约漂移
- 业务执行失败
- 证据链断裂导致不可判定

### 3.3 原则三：不边跑边改

首次真实执行应尽量避免“刚看到异常就改脚本再重跑”。

若边跑边改，会导致：

- 首次执行结果失真
- 无法区分问题来自环境、服务还是 gate 逻辑
- 失去完整复盘价值

### 3.4 原则四：Stage 4 只读，Stage 6 只验已选对象

- Stage 4 只读观察 runtime / jobs 聚合演进。
- Stage 6 只验证 DB evidence 已选出的 `(bucket_name, object_key)` 是否真实存在。

---

## 4. 快速交接摘要

### 4.1 入口命令

推荐在项目虚拟环境中执行，并显式进入仓库根目录：

```bash
source /mnt/user-data/workspace/.venv/bin/activate && \
cd /mnt/user-data/workspace/Ai_Videos_Replication && \
python scripts/baseline_gate.py
```

如需显式写出证据产物位置，可使用：

```bash
source /mnt/user-data/workspace/.venv/bin/activate && \
cd /mnt/user-data/workspace/Ai_Videos_Replication && \
python scripts/baseline_gate.py \
  --output-json /mnt/user-data/workspace/Ai_Videos_Replication/baseline_gate_verdict.json \
  --output-md /mnt/user-data/workspace/Ai_Videos_Replication/baseline_gate_verdict.md
```

默认参数与当前冻结契约保持一致：

- `--project-id=656ac6b1-ecb8-4f45-9f45-556be5915168`
- `--compile-reason=manual_runtime_validation`
- `--mode=manual_runtime_validation`
- `--timeout-seconds=300`
- `--poll-interval-seconds=5`
- 默认产物：仓库根 `baseline_gate_verdict.json` / `baseline_gate_verdict.md`
- 退出码：仅 `PASS` 返回 `0`，其余 verdict 返回 `1`

### 4.2 Verdict 枚举与解释优先级

baseline gate 只允许以下四种 verdict：

- `PASS`
- `FAIL`
- `DRIFT`
- `INCONCLUSIVE`

解释优先级固定为：`INCONCLUSIVE > DRIFT > FAIL > PASS`

这表示：只要证据链不完整，应先落 `INCONCLUSIVE`；只有证据链完整且确认冻结边界偏移时，才落 `DRIFT`；只有在业务/数据失败证据成立时，才落 `FAIL`；四层全部满足时才落 `PASS`。

### 4.3 首次执行前提

首次真实执行前，至少确认以下前提全部成立：

- 当前工作仍严格限定在 `baseline gate` 独立线程
- 不在执行过程中改写 `scripts/baseline_gate.py`
- 不用脚本外人工 DB 修补或 runtime refresh 替代 Stage 4/5/6
- 仍使用冻结 smoke project：`656ac6b1-ecb8-4f45-9f45-556be5915168`
- `docker-compose` 可用，且 `avr_app / avr_worker / avr_postgres / avr_redis / avr_minio` 五个服务处于运行中
- compose / migration / settings / model / buckets 未偏离冻结基线
- 已完成：
  - `docs/checklists/production_baseline_verification_checklist.md`
  - `docs/baseline_gate_preflight_record_template.md`
- 已接受“Stage 5 资产关联为 tentative metadata-backed、Stage 6 只验 DB 已选对象”的既定口径

### 4.4 证据产物位置

首次执行的核心证据产物固定分两层：

1. 文件层
   - 仓库根 `baseline_gate_verdict.json`
   - 仓库根 `baseline_gate_verdict.md`
2. verdict 内嵌 evidence 层
   - `evidence.health_response`
   - `evidence.compile_validate_response`
   - `evidence.compile_dispatch_response`
   - `evidence.alembic_version`
   - `evidence.settings_snapshot`
   - `evidence.runtime_record`
   - `evidence.runtime_dispatch_summary`
   - `evidence.runtime_asset_association`
   - `evidence.jobs`
   - `evidence.assets`
   - `evidence.stage_timings`
   - `evidence.compose_snapshot`
   - `evidence.running_services`
   - `evidence.runtime_poll_snapshot`

其中：

- `baseline_gate_verdict.json` 是审计主产物，适合留档、比对、复盘
- `baseline_gate_verdict.md` 是人类可读摘要，适合快速浏览 layer 结果、jobs/assets/object store 概况
- 若需定位具体失败层，应优先回看对应 stage 的 evidence 字段，而不是只看顶层 `summary`

### 4.5 如何解释四种结果

#### PASS

表示冻结边界未漂移，且 Stage 0 到 Stage 6 证据链完整成立；可解释为当前冻结沙箱环境仍具备最小可重复生产基线能力。

#### FAIL

表示证据链完整，但业务执行或数据落盘链路未满足 gate 最小成功条件。优先按失败层拆解：

- Stage 2：compile validate 失败
- Stage 3：compile dispatch / response contract 失败
- Stage 4：runtime/job 聚合终态失败
- Stage 5：DB jobs/assets evidence 失败
- Stage 6：对象存储实物核验失败

#### DRIFT

表示不是主链路业务失败，而是冻结边界本身已偏离，例如 compose、服务集合、migration、settings、image model、bucket 配置等发生变化。此时应先修复基线，再考虑重跑。

#### INCONCLUSIVE

表示不能可信地下 verdict，通常是 probe、DB、HTTP、MinIO 或 stdout JSON 恢复链本身不完整。此时应先修证据链，再决定是否二次执行，不应直接把它当作业务失败。

---

## 5. 推荐角色分工

### 5.1 Driver

负责：

- 发起首次真实执行
- 保存终端输出
- 保存关键 evidence
- 记录异常发生位置与时间点

### 5.2 Reviewer

负责：

- 对照既定契约解释每个 stage 的结果
- 判断问题属于 `DRIFT / FAIL / INCONCLUSIVE` 中哪一类
- 阻止现场做越界动作

> 如果只有单人执行，也建议按 Driver / Reviewer 两种视角分开处理：先执行，再复核，不要边看边改。

---

## 6. 执行前阶段

## 6.1 前置准入条件

在进入首次真实执行前，建议至少满足以下条件：

- 已完成《首次执行前只读检查清单》
- 已完成《首次执行前检查记录模板》
- 总体结论为“可进入首次真实执行”
- 无未接受的 blocker
- 已锁定唯一 smoke project_id

## 6.2 执行前冻结事项

执行前必须确认以下对象不再变化：

- `docker-compose.yml`
- `app` / `worker` command
- `.env` 与关键 settings
- migrations head 状态
- smoke project 选择
- `scripts/baseline_gate.py`

若这些对象仍计划调整，则说明还未进入合格执行窗口。

## 6.3 smoke project 选择要求

首次执行使用的 smoke project 应满足：

- project_id 唯一且明确
- 在数据库中真实存在
- 理论上可通过 compile validate
- 不是已知损坏、已知无效或临时拼凑数据

---

## 7. 执行中阶段：按 Stage 观察

## 7.1 Stage 0：Baseline Freeze

### 关注点

- 仓库路径是否正确
- `docker-compose` 是否可用
- compose baseline 是否锁定
- 基础服务是否都在运行
- Alembic 是否在 head
- settings 中关键锁定项是否仍匹配
- smoke project 是否存在

### 正常信号

- freeze checks 全部通过
- 无 compose / migration / settings 漂移
- smoke project 存在

### 典型 DRIFT 信号

- compose 文件结构被改坏
- `app` / `worker` command 被替换
- 关键 buckets 配置漂移
- migration 不在 head
- smoke project 不存在

### 解读原则

Stage 0 失败优先解释为 **DRIFT**，不是业务失败。

---

## 7.2 Stage 1：Health Probe

### 关注点

- app 容器内 probe 是否能运行
- `/health` 是否返回 `HTTP 200`
- payload 是否为 JSON object
- required health keys 是否完整

### 正常信号

- `http_status == 200`
- payload 为 dict
- required keys 完整

### 典型 INCONCLUSIVE 信号

- probe returncode 非零
- stdout 为空
- stdout 无法恢复出 JSON object
- payload 不是 dict

### 解释原则

Stage 1 异常优先先检查：

- probe 执行链
- app 容器本身
- `/health` 路由契约
- stdout 输出形态

不要过早归咎于 compile / dispatch 逻辑。

---

## 7.3 Stage 2：Compile Validate

### 关注点

- validate 路由返回码
- payload 是否为 dict
- `is_valid`
- `errors`
- `warnings`

### 正常信号

- `HTTP 200`
- `is_valid == true`
- `errors == []`
- `warnings` 可为空，也可存在但不阻塞

### FAIL 信号

- `is_valid == false`
- `errors` 非空

### INCONCLUSIVE 信号

- 非 200
- payload 结构不可解释
- 返回结构与当前契约不符

### 解释原则

Stage 2 失败说明 smoke project 不满足 compile 基本前提；
Stage 2 inconclusive 则说明 validate 证据链本身未建立成功。

---

## 7.4 Stage 3：Compile Dispatch

### 关注点

- `POST /api/v1/compile` 是否成功
- 返回 payload 是否至少含：
  - `id`
  - `runtime_version`
  - `dispatch_summary`
- 是否真的形成新的 runtime

### 正常信号

- 返回 `200 / 201`
- `dispatch_summary` 为 dict
- 新 runtime 的 `id` 与 `runtime_version` 均不同于 previous runtime

### FAIL 信号

- 关键字段缺失
- 没有产生新的 runtime
- 已出现明确 compile fail 语义

### 解释原则

Stage 3 异常优先核对：

- route 与 schema 是否漂移
- CompilerService 行为是否变更
- response payload 结构是否已发生变化

---

## 7.5 Stage 4：Runtime Polling

### 关注点

- 能否重新按 runtime identity 找到 runtime
- jobs 是否能按 `project_id + payload.runtime_version` 查到
- derived status 如何演进

### 应预期的正常演进

一个理想过程通常表现为：

1. 初期：出现 active jobs
2. 中期：`queued/dispatched/running` 逐步向 `succeeded` 演进
3. 终态：
   - `derived_compile_status == "succeeded"`
   - `derived_dispatch_status == "fully_dispatched"`

### 必须提前接受的非阻塞现象

- stored status 可能暂时落后于 derived status
- 终态时 `dispatched_job_count` 可能为 0
- warning `terminal_runtime_dispatched_job_count_zero_is_expected_when_all_jobs_have_advanced_beyond_dispatch` 是合理的非阻塞提示

### FAIL 信号

- terminal `derived_compile_status != "succeeded"`
- terminal `derived_dispatch_status != "fully_dispatched"`
- jobs evidence 明确进入 `failed` 且无法恢复

### INCONCLUSIVE 信号

- runtime 取不到
- jobs 取不到
- 轮询对象不稳定或结构不可解释

### 执行纪律

- 不做脚本外 refresh / commit
- 不人工改写 runtime 聚合状态
- 只观察，不干预

---

## 7.6 Stage 5：DB Evidence

### 关注点

- runtime_record 是否完整
- jobs evidence 是否齐全
- 五类 required job types 是否全部存在
- required asset types 是否齐全
- assets 是否 materialized
- `external_task_id` 是否齐全
- `runtime_asset_association` evidence 是否与当前静态结论一致

### 正常信号

- 五类 jobs 全部存在
- 非 compile 对应资产类型齐全
- 资产状态满足 materialized 要求
- runtime association evidence 显示 metadata 有现实支撑

### FAIL 信号

- `unexpected_job_count`
- `missing_job_types`
- `non_succeeded_jobs`
- `missing_external_task_id`
- `missing_asset_types`
- `non_materialized_assets`
- `unexpected_materialized_asset_count`

### Warning-aware 信号

- `asset_runtime_version_association_is_tentative_and_not_confirmed_by_data`
- `duplicate_asset_types:{...}`

这些 warning 不应被直接升级为 fail，除非出现额外证据证明其已破坏 gate 的最小成功条件。

### 解释原则

Stage 5 最关键的解读点是：

- 区分“证据不足”与“明确失败”
- 区分“tentative 但有 metadata 支撑”与“完全无关联依据”

当前已确认：

- worker 会写入 `asset_metadata.runtime_version`
- worker 还会写入 `job_id/job_type/external_task_id/generated_by`
- 因此 Stage 5 的 runtime-asset 选择逻辑有现实数据支撑，但仍不是强契约

---

## 7.7 Stage 6：Object Store Probe

### 关注点

- object probe 返回是否包含 `objects`
- `objects` 是否为 list
- 每个目标对象是否 `exists == true`

### 正常信号

- DB 已选中的所有对象在 MinIO 中都能 stat 到

### FAIL 信号

- 任一目标对象不存在
- DB 声称 materialized，但对象存储中没有实物

### 解释原则

Stage 6 的价值是验证 DB evidence 不是空壳。

如果 Stage 5 看起来成功而 Stage 6 失败，应优先怀疑：

- materialization 未真正落盘
- bucket/object key 不正确
- DB 状态过早乐观

---

## 7.8 Stage 7：Verdict Render

### 最终优先级

`INCONCLUSIVE > DRIFT > FAIL > PASS`

### 含义说明

- `INCONCLUSIVE`：证据链中断或返回结构不可判定
- `DRIFT`：环境基线不满足冻结要求
- `FAIL`：业务或数据证据足够明确地失败
- `PASS`：从 Stage 0 到 Stage 6 均满足 gate 期望

### 解读纪律

不要把：

- `INCONCLUSIVE` 误当成 `FAIL`
- `DRIFT` 误当成业务失败
- 某些 warning-aware 项误当成 PASS 的反证

---

## 8. 执行后阶段

## 8.1 结果分类动作

### 若结果为 PASS

建议：

- 保存完整终端输出
- 保存关键 evidence 快照
- 记录首次执行时间、project_id、runtime_version
- 将本次结果归档为 baseline 参考样本

### 若结果为 FAIL

建议优先归类失败层级：

- Stage 2：validate 失败
- Stage 3：compile/dispatch 失败
- Stage 4：runtime 聚合失败
- Stage 5：DB evidence 失败
- Stage 6：对象实物校验失败

不要先改 gate，先确认业务链或数据链是否真实失败。

### 若结果为 DRIFT

建议：

- 优先回收或修复环境漂移
- 重新确认 compose、settings、migration、smoke project
- 不建议在 drift 状态下频繁重复跑脚本

### 若结果为 INCONCLUSIVE

建议优先排查：

1. probe stdout JSON object 恢复链
2. `/health` 路由响应结构
3. validate / compile API 响应结构
4. runtime / jobs 查询链
5. object probe 结构

先修证据链，再考虑第二次执行。

---

## 9. 首次执行复盘模板

建议首次真实执行结束后至少记录以下内容：

### 9.1 基本信息

- 执行时间：
- 执行人：
- smoke project_id：
- 最终 verdict：

### 9.2 分阶段结果

- Stage 0：
- Stage 1：
- Stage 2：
- Stage 3：
- Stage 4：
- Stage 5：
- Stage 6：
- Stage 7：

### 9.3 关键 evidence

- compile validate response：
- compile dispatch response：
- runtime poll snapshot：
- runtime dispatch summary：
- jobs evidence：
- assets evidence：
- object probe evidence：

### 9.4 问题归类

- 环境问题：
- 契约问题：
- 数据问题：
- worker / materialization 问题：
- gate 解释问题：

### 9.5 后续动作

- [ ] 无需修改，归档
- [ ] 修环境后重试
- [ ] 修业务后重试
- [ ] 修 gate 静态逻辑后再评估

---

## 10. 首次执行时的五条纪律

1. **先过检查记录模板，再进入真实执行。**
2. **不要边跑边改脚本。**
3. **Stage 4 只读观察，不主动 refresh。**
4. **Stage 5 资产关联是 tentative metadata-backed，不是强外键。**
5. **Stage 6 仅验证 DB 已选对象，不从对象存储反查 runtime。**

---

## 11. 配套文档建议

建议与以下文档配合使用：

- `docs/checklists/` 下既有只读检查清单
- `docs/gates/baseline_gate_first_execution_record_template.md`

推荐顺序：

1. 先完成只读检查清单。
2. 再完成首次执行前检查记录模板。
3. 确认准入后进入首次真实执行。
4. 执行结束后按本手册做结果归类与复盘。
