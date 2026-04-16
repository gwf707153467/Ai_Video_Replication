# Compile API Contract

## 1. 文档目的

本文件定义当前实现下 compile API 的请求、响应、错误语义、校验规则、runtime 创建规则与 dispatch 结果语义。

本 contract 只描述仓库现状，不扩展未来编排能力，也不改变既有主链路实现。

---

## 2. 适用范围

本文件覆盖以下接口：

- `POST /api/v1/compile`
- `GET /api/v1/compile/validate/{project_id}`

核心实现位置：

- `app/api/v1/routes/compile_routes.py`
- `app/schemas/compile.py`
- `app/compilers/orchestrator/compiler_service.py`
- `app/services/compile_validator_service.py`
- `app/services/runtime_state_service.py`

---

## 3. 路由挂载与访问前缀

compile 路由由 `app/main.py` 中的 `api_router` 挂载到：

- 根前缀：`/api/v1`
- compile 子路由：`/compile`

因此当前有效接口为：

- `POST /api/v1/compile`
- `GET /api/v1/compile/validate/{project_id}`

---

## 4. POST /api/v1/compile

### 4.1 接口目的

对指定 project 执行一次 compile：

1. 先做 project 结构校验
2. 解析 runtime version
3. 聚合 sequences / spus / vbus / bridges
4. 创建一条 `compiled_runtimes` 记录
5. 可选地创建并 dispatch 5 条标准 jobs

### 4.2 请求模型

请求体模型为 `CompileRequest`：

```json
{
  "project_id": "656ac6b1-ecb8-4f45-9f45-556be5915168",
  "runtime_version": null,
  "compile_reason": "manual",
  "compile_options": {},
  "auto_version": true,
  "dispatch_jobs": false
}
```

字段语义：

- `project_id`：目标项目 UUID，必填
- `runtime_version`：可选；当且仅当 `auto_version=false` 时才会直接采用
- `compile_reason`：编译原因，默认 `manual`
- `compile_options`：自由结构字典，默认 `{}`
- `auto_version`：是否自动生成版本号，默认 `true`
- `dispatch_jobs`：是否在 compile 后立即派发 jobs，默认 `false`

### 4.3 runtime version 解析规则

`CompilerService._resolve_runtime_version()` 当前规则如下：

1. 若 `runtime_version` 有值且 `auto_version=false` → 使用传入值
2. 否则，只要 `auto_version=true` 或 `runtime_version` 为空 → 调 `RuntimeVersionService.next_version(project_id)`
3. 其余情况回退为使用 `runtime_version`

等价理解：

- 想强制指定版本号，必须同时满足：
  - `runtime_version` 非空
  - `auto_version=false`
- 默认行为是自动生成版本号

### 4.4 前置校验

compile 会先调用 `CompileValidatorService.validate_project(project_id)`。

若校验结果 `is_valid=false`，接口不会创建 runtime，而是直接报错 `project_invalid`。

校验规则：

#### 错误项（阻断 compile）

- 无 sequence → `missing_sequences`
- 无 spu → `missing_spus`
- 某 spu 指向不存在 sequence → `spu_sequence_missing:{spu_code}`
- 某 vbu 指向不存在 sequence → `vbu_sequence_missing:{vbu_code}`
- 某 bridge 指向不存在 sequence → `bridge_sequence_missing:{bridge_code}`

#### 警告项（不阻断 compile）

- 无 vbu → `missing_vbus`
- 无 bridge → `missing_bridges`

#### counts

返回结构中总是含：

- `sequences`
- `spus`
- `vbus`
- `bridges`

---

## 5. Compile 成功时的 runtime 创建契约

### 5.1 创建时机

只有在以下条件同时满足时才创建 runtime：

- project 存在
- validation 通过（即 `errors=[]`）

### 5.2 新 runtime 初始字段

新建 `CompiledRuntime` 时写入：

- `project_id = request.project_id`
- `runtime_version = <解析结果>`
- `compile_status = "compiled"`
- `runtime_payload = <RuntimePacket>`
- `dispatch_status = "not_dispatched"`
- `dispatch_summary = {}`
- `compile_started_at = datetime.utcnow()`
- `compile_finished_at = datetime.utcnow()`

### 5.3 runtime_payload 结构

`runtime_payload` 当前至少包含：

- `project_id`
- `runtime_version`
- `compile_reason`
- `compile_options`
- `visual_track_count`
- `audio_track_count`
- `bridge_count`
- `sequences`

其中 `sequences[]` 每项至少含：

- `sequence_id`
- `sequence_index`
- `sequence_type`
- `persuasive_goal`
- `spus[]`
- `vbus[]`
- `bridges[]`

### 5.4 sequence 内嵌对象字段

#### `spus[]`

每项至少包含：

- `spu_id`
- `spu_code`
- `display_name`
- `asset_role`
- `duration_ms`
- `generation_mode`
- `prompt_text`
- `negative_prompt_text`
- `visual_constraints`
- `status`

#### `vbus[]`

每项至少包含：

- `vbu_id`
- `vbu_code`
- `persuasive_role`
- `script_text`
- `voice_profile`
- `language`
- `duration_ms`
- `tts_params`
- `status`

#### `bridges[]`

每项至少包含：

- `bridge_id`
- `bridge_code`
- `bridge_type`
- `spu_id`
- `vbu_id`
- `execution_order`
- `transition_policy`
- `status`

---

## 6. dispatch_jobs=false 的响应契约

当 `dispatch_jobs=false` 时：

- runtime 最终 `compile_status = "compiled"`
- runtime 最终 `dispatch_status = "not_dispatched"`
- `dispatch_summary` 会被写成零计数摘要，而不是空字典

结构如下：

```json
{
  "runtime_version": "v1",
  "job_count": 0,
  "queued_job_count": 0,
  "dispatched_job_count": 0,
  "undispatched_job_count": 0,
  "dispatch_status": "not_dispatched",
  "jobs": []
}
```

这意味着：

- compile API 即使不 dispatch，也会产出一条完整 runtime 记录
- 后续审计不应把 `dispatch_summary={}` 作为非派发模式的稳定事实，稳定事实应以提交后的零计数摘要为准

---

## 7. dispatch_jobs=true 的响应契约

当 `dispatch_jobs=true` 时，compile 除了创建 runtime，还会执行标准 job 创建与派发。

### 7.1 固定创建的 job types

固定为 5 类：

- `compile`
- `render_image`
- `render_video`
- `render_voice`
- `merge`

### 7.2 job payload 基础字段

每条 job payload 至少包含：

- `runtime_version`
- `dispatch_source = "compile_endpoint"`

### 7.3 render_image 专属 payload

`render_image` 额外补充：

- `prompt`
- `negative_prompt`
- `provider_inputs`

`provider_inputs` 当前固定至少包含：

- `prompt`
- `negative_prompt`
- `sample_count = 1`
- `aspect_ratio = "9:16"`
- `source = "compiler_minimal_render_image_prompt_v1"`
- `runtime_version`

### 7.4 render_image prompt 组装规则

`_build_render_image_payload()` 当前组 prompt 的规则为：

1. 从 project 写入：
   - `Project: {project.name}`
   - `Target market: {project.source_market}`
   - `Target language: {project.source_language}`
   - 若存在 notes，则加入 `Project notes: ...`
2. 从 sequences 按顺序写入 sequence plan
3. 在所有 SPU 中，优先选择**第一个有 `prompt_text` 的 SPU** 作为 primary SPU
4. 若找到 primary SPU：
   - 追加 `Primary visual subject: {display_name}`
   - 追加该 `prompt_text`
   - 规范化 `negative_prompt_text` 为 `negative_prompt`
   - 读取 `visual_constraints`
5. 若没有带 prompt 的 SPU，但存在 SPU：
   - 只追加第一条 SPU 的 display_name 作为 primary visual subject
6. 若存在 `visual_constraints`，追加文本化后的 constraints
7. 最终将各段按换行拼接为 `prompt`

### 7.5 dispatch 成功后的 runtime 状态

job dispatch 结束后，runtime 会被直接更新为：

- `compile_status = "dispatched"`
- `dispatch_status = <dispatch summary status>`
- `dispatch_summary = <创建/派发摘要>`

注意：这里的 `compile_status = "dispatched"` 只是 compile 阶段的提交结果；后续 worker 运行后，runtime 状态会被 `RuntimeStateService.refresh_runtime_status()` 进一步推导为 `running` / `succeeded` / `failed`。

### 7.6 dispatch summary 结构

结构至少包含：

- `runtime_version`
- `job_count`
- `queued_job_count`
- `dispatched_job_count`
- `undispatched_job_count`
- `dispatch_status`
- `jobs[]`

其中 `jobs[]` 每项至少含：

- `job_id`
- `job_type`
- `status`
- `external_task_id`

### 7.7 dispatch_status 判定

compile 创建 / 派发阶段的判定规则：

- 全部 job 成功拿到 task id → `fully_dispatched`
- 否则 → `partially_dispatched`

当前 `_create_and_dispatch_jobs()` 不会在 compile 阶段返回 `not_dispatched`。

---

## 8. POST /api/v1/compile 响应模型

响应模型为 `CompiledRuntimeRead`，至少包含：

- `id`
- `project_id`
- `runtime_version`
- `compile_status`
- `runtime_payload`
- `dispatch_status`
- `dispatch_summary`
- `last_error_code`
- `last_error_message`
- `compile_started_at`
- `compile_finished_at`
- `created_at`

### 8.1 成功响应示意（dispatch_jobs=true）

```json
{
  "id": "9c5a8e97-924a-475e-91a1-c3db0a60571b",
  "project_id": "656ac6b1-ecb8-4f45-9f45-556be5915168",
  "runtime_version": "v7",
  "compile_status": "dispatched",
  "runtime_payload": {"...": "..."},
  "dispatch_status": "fully_dispatched",
  "dispatch_summary": {
    "runtime_version": "v7",
    "job_count": 5,
    "queued_job_count": 0,
    "dispatched_job_count": 5,
    "undispatched_job_count": 0,
    "dispatch_status": "fully_dispatched",
    "jobs": [
      {
        "job_id": "e836ac89-f00b-4431-bdd0-f2a78c0f6b4b",
        "job_type": "render_image",
        "status": "dispatched",
        "external_task_id": "..."
      }
    ]
  },
  "last_error_code": null,
  "last_error_message": null,
  "compile_started_at": "2026-03-30T...",
  "compile_finished_at": "2026-03-30T...",
  "created_at": "2026-03-30T..."
}
```

注意：

- API 返回当下提交时点的 runtime 视图
- 若随后 worker 继续推进，DB 中 runtime 状态可能继续变化
- 因此 compile API 响应不等同于最终执行完成态

---

## 9. GET /api/v1/compile/validate/{project_id}

### 9.1 接口目的

返回 compile 前置校验结果，不创建 runtime，不 dispatch jobs。

### 9.2 响应模型

响应模型为 `CompileValidationRead`：

- `project_id`
- `is_valid`
- `errors[]`
- `warnings[]`
- `counts{}`

### 9.3 判定规则

- 只有当 `errors` 为空时，`is_valid = true`
- `warnings` 不阻断 compile

### 9.4 成功响应示意

```json
{
  "project_id": "656ac6b1-ecb8-4f45-9f45-556be5915168",
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "counts": {
    "sequences": 1,
    "spus": 1,
    "vbus": 1,
    "bridges": 1
  }
}
```

### 9.5 有 warning 的合法响应示意

```json
{
  "project_id": "...",
  "is_valid": true,
  "errors": [],
  "warnings": ["missing_bridges"],
  "counts": {
    "sequences": 3,
    "spus": 5,
    "vbus": 2,
    "bridges": 0
  }
}
```

### 9.6 非法响应示意

```json
{
  "project_id": "...",
  "is_valid": false,
  "errors": ["missing_sequences", "missing_spus"],
  "warnings": ["missing_vbus", "missing_bridges"],
  "counts": {
    "sequences": 0,
    "spus": 0,
    "vbus": 0,
    "bridges": 0
  }
}
```

---

## 10. 错误语义

### 10.1 `POST /api/v1/compile`

- project 不存在 → HTTP `404`, `detail="project_not_found"`
- validation 不通过 → HTTP `422`, `detail="project_invalid"`

### 10.2 `GET /api/v1/compile/validate/{project_id}`

- project 不存在 → HTTP `404`, `detail="project_not_found"`

注意：

- 当前 route 层只显式处理上述 `ValueError`
- 其他未预期异常将继续向上抛出，由框架默认错误处理接管

---

## 11. 与 runtime 聚合状态的边界

compile API 负责：

- 校验 project
- 生成 runtime payload
- 创建 runtime
- 可选创建并 dispatch jobs

compile API **不负责** 最终 runtime 运行态闭环。最终运行态由 worker 执行后，通过 `RuntimeStateService.refresh_runtime_status()` 聚合更新。

因此边界应理解为：

- compile API 返回的是“提交时刻状态”
- runtime_state_service 负责把后续 job 执行结果折叠为 runtime 最终状态

典型演化路径：

- compile-only：`compiled / not_dispatched`
- 已提交异步任务：`dispatched / fully_dispatched`
- worker 开始执行后：runtime 可能进入 `running`
- 全部 job 成功：runtime 进入 `succeeded`
- 任一 job 失败：runtime 进入 `failed`

---

## 12. 当前冻结成功锚点

当前 compile API 的已验证成功锚点为 smoke project：

- `project_id = 656ac6b1-ecb8-4f45-9f45-556be5915168`
- 成功 runtime：`v7`
- runtime id：`9c5a8e97-924a-475e-91a1-c3db0a60571b`

该样本已确认：

- compile API 可成功创建 runtime 并 dispatch 5 个 jobs
- runtime 最终收敛为：
  - `compile_status = succeeded`
  - `dispatch_status = fully_dispatched`
- `dispatch_summary` 显示 5 个 job 全部 succeeded
- 关联 assets 已完成 materialization

因此 `v7` 是当前 compile API contract 的可执行成功参考样本。

---

## 13. 对外使用建议

对 runbook、probe、repeatability report、控制面板或自动验收脚本，建议按以下方式使用 compile API：

1. 先调用 `/api/v1/compile/validate/{project_id}` 检查结构合法性
2. 再调用 `POST /api/v1/compile` 触发 compile
3. 若 `dispatch_jobs=true`，不要把 compile 响应当作最终执行完成态
4. 最终状态应通过：
   - `compiled_runtimes.dispatch_summary`
   - `jobs` 表
   - `assets` 表
   联合核对
5. 若需要稳定复现 smoke，应沿用冻结基线：
   - 当前 compose 修复不回退
   - `GOOGLE_IMAGE_MODEL=imagen-4.0-fast-generate-001`
   - 不改 provider 主逻辑

若后续 compile request schema、runtime payload、dispatch summary、错误语义或 validate 规则发生变化，必须同步更新本 contract。
