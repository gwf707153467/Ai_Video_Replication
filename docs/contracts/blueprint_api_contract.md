# Blueprint API Contract

## 1. 文档目的

本文件定义 `P2-M2 Blueprint API surface` 的最小非侵入式接口契约。

目标是把 `BlueprintV0` 的校验与 compile preview 能力固定为 repo 内可复用 API 入口，同时保持以下边界：

- 不触碰 baseline gate 逻辑、边界与判断语义
- 不引入 DB migration
- 不创建 `CompiledRuntime`
- 不触发现有 production dispatch 主链
- 不扩展到完整 ingest / parsing pipeline

---

## 2. 路由范围

当前 Blueprint API 由 `app/api/v1/routes/blueprint_routes.py` 提供，并通过 `app/api/v1/router.py` 挂载到：

- 根前缀：`/api` + `/v1`
- Blueprint 子路由：`/blueprints`

因此当前有效接口为：

- `POST` 到 Blueprint validate route
- `POST` 到 Blueprint compile-preview route

---

## 3. 输入模型

两个接口都直接接收 `BlueprintV0` 作为请求体。

请求体必须满足：

- `docs/contracts/blueprint_v0_contract.md` 中定义的全部字段语义
- `app/schemas/blueprint.py` 中定义的全部字段约束与 cross-field validation

当请求体非法时，接口返回 FastAPI / Pydantic 标准 `422` 响应。

---

## 4. Validate route

### 4.1 接口目的

对 Blueprint 做纯 schema / semantic validation，并返回标准化摘要，不产生任何持久化副作用。

### 4.2 成功响应模型

响应模型为 `BlueprintValidationRead`：

```json
{
  "blueprint_id": "beauty-lip-plumper-demo",
  "blueprint_version": "blueprint.v0",
  "is_valid": true,
  "counts": {
    "sequences": 4,
    "spus": 4,
    "vbus": 4,
    "bridges": 4,
    "reference_beats": 4
  },
  "requested_runtime_version": "beauty-lip-plumper-demo.v0",
  "effective_runtime_version": "beauty-lip-plumper-demo.v0",
  "dispatch_jobs": false
}
```

### 4.3 字段语义

- `blueprint_id`：Blueprint 标识
- `blueprint_version`：当前固定为 `blueprint.v0`
- `is_valid`：当前成功响应固定为 `true`
- `counts`：Blueprint 结构摘要
  - `sequences`：sequence 数
  - `spus`：SPU 总数
  - `vbus`：VBU 总数
  - `bridges`：Bridge 总数
  - `reference_beats`：reference beat 总数
- `requested_runtime_version`：来自 `compile_preferences.requested_runtime_version`
- `effective_runtime_version`：若请求未显式提供版本，则回退为 `<blueprint_id>.stub`
- `dispatch_jobs`：透传 Blueprint compile preference，仅表达输入意图；validate 接口不会执行 dispatch

---

## 5. Compile-preview route

### 5.1 接口目的

将 Blueprint 通过最小 compiler stub 编译成 `RuntimePacket` 预览结果。

### 5.2 成功响应模型

响应模型为 `BlueprintCompilePreviewRead`：

```json
{
  "blueprint_id": "beauty-lip-plumper-demo",
  "blueprint_version": "blueprint.v0",
  "runtime_packet": {
    "project_id": "<deterministic-uuid>",
    "runtime_version": "beauty-lip-plumper-demo.v0",
    "compile_reason": "blueprint_stub",
    "compile_options": {
      "blueprint_id": "beauty-lip-plumper-demo"
    },
    "visual_track_count": 4,
    "audio_track_count": 4,
    "bridge_count": 4,
    "sequences": []
  }
}
```

### 5.3 行为边界

该接口当前行为严格限定为：

1. 校验 `BlueprintV0`
2. 调用 `compile_blueprint_v0_to_runtime_packet(...)`
3. 返回内存态 `RuntimePacket`

明确不做：

- DB 持久化
- `CompiledRuntime` 创建
- job dispatch
- baseline 相关逻辑复用或替换

---

## 6. 错误语义

当前 Blueprint API 不额外包裹 validation error。

因此：

- Blueprint 非法 → `422 Unprocessable Entity`
- 错误内容遵循 FastAPI / Pydantic 标准结构
- 自定义 validator 错误文案会出现在 `detail[].msg` 中

例如：

- `bridge_requires_spu_or_vbu_binding`
- `reference_beat_sequence_missing:<beat_code>:<sequence_code>`

---

## 7. P2-M3 稳定导出面

为避免下游调用继续分散依赖 repo 内部路径，当前额外冻结一个最小 package-level public surface：`app.blueprint_sdk`。

当前稳定导出符号为：

- `BlueprintV0`
- `BlueprintValidationCountsV0`
- `BlueprintValidationRead`
- `BlueprintCompilePreviewRead`
- `compile_blueprint_v0_to_runtime_packet(...)`
- `validate_blueprint(...)`
- `compile_blueprint_preview(...)`
- `router`

该导出层只做 re-export，不引入新行为，不改变 Blueprint schema / compiler / API 路由语义。

## 8. P2-M4 Artifact Access Surface

在 P2-M3 稳定导出面之上，当前进一步冻结一个只读、零副作用的 Blueprint artifact access surface，供脚本、测试与下游集成统一访问 repo 内 contract artifacts。

当前稳定 accessor 为：

- `get_blueprint_example_path()`
- `load_blueprint_example_payload()`
- `load_blueprint_example_v0()`
- `get_blueprint_contract_doc_path()`
- `load_blueprint_contract_doc_text()`

该 access surface 的边界为：

- 仅访问 repo 内 frozen Blueprint example / contract artifacts
- 不访问 DB / Redis / MinIO
- 不创建或修改任何文件
- 不扩展 API route、compile-preview 或 runtime 行为
- 不引入 dispatch / persistence / baseline 相关逻辑

## 9. P2-M5 Contract Packaging / Discovery Hardening

在 P2-M4 的只读 artifact accessor 基础上，当前进一步冻结一组 repo-local contract packaging / discovery helper，用于把 Blueprint example、contract doc、JSON schema 的定位方式统一为稳定 SDK surface。

当前新增稳定 accessor 为：

- `get_blueprint_schema_path()`
- `load_blueprint_schema_payload()`
- `get_blueprint_artifact_paths()`

其中：

- `get_blueprint_schema_path()`：返回 `docs/contracts/schemas/blueprint_v0.schema.json`
- `load_blueprint_schema_payload()`：返回 Blueprint V0 JSON schema 的反序列化 payload
- `get_blueprint_artifact_paths()`：返回稳定 artifact index，当前包含：
  - `example_payload`
  - `contract_doc`
  - `json_schema`

P2-M5 的目标仅为 discovery hardening，不扩大运行能力。其边界为：

- 仅返回 repo-local `Path` 或 JSON payload
- 不执行 schema registry、远程拉取或动态搜索
- 不新增 endpoint、DB 持久化、dispatch、runtime/provider 集成
- 不修改 Blueprint compile contract 与 baseline gate 任何既有语义

## 10. P2-M6 Contract Consistency Guardrails

P2-M6 在既有 SDK / artifact access surface 之上，补充一组只读、零副作用的一致性护栏，用于防止 example fixture、contract doc、JSON schema、package export surface 与 self-check 之间发生静默漂移。

当前 guardrail 重点冻结：

- `app.blueprint_sdk.__all__` 中的 Blueprint public surface 顺序与符号集合
- artifact index key 集合固定为：
  - `example_payload`
  - `contract_doc`
  - `json_schema`
- `load_blueprint_contract_doc_text()` 返回的 contract doc 中必须持续包含关键 marker：
  - `# Blueprint v0 Contract`
  - `bridge_requires_spu_or_vbu_binding`
  - `reference_beat_sequence_missing:<beat_code>:<sequence_code>`
  - `## 11. Self-check 范围`
  - `## 12. 非目标与边界`
- self-check 继续只验证 repo-local artifact 与 compile stub 的稳定性，不引入 runtime side effect

P2-M6 的边界保持不变：

- 不新增 endpoint、CLI 子命令或后台任务
- 不接入 DB / Redis / MinIO / provider runtime
- 不扩展 Blueprint compile 为持久化、dispatch 或 ingest pipeline
- 不修改 baseline gate、compile preview、既有 schema validator 与判断语义

## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline

P2-M7 为 Blueprint public surface 增加一组只读 contract discipline guardrails，用于约束 fixture、schema、SDK export、API doc 与 self-check 的协同变更。

当前冻结规则为：

- `fixture_change_requires_contract_review`：canonical example fixture 仍为 `docs/examples/beauty_cosmetics_blueprint_v0.json`；任何会影响 request/response 示例、compile-preview 预期、sequence 顺序或关键字段语义的变更，都必须同步更新 `docs/contracts/blueprint_v0_contract.md`、`docs/contracts/blueprint_api_contract.md`、测试与 self-check
- `contract_change_requires_guardrail_updates`：若改动 `app.blueprint_sdk.__all__`、artifact index keys、route path、response model、关键 validator message 或 compile-preview 冻结示例预期，必须在同一提交中同步更新 docs、tests 与 self-check
- `breaking_fixture_semantics_require_versioned_surface`：若 Blueprint 或 API 契约发生 breaking semantic change，应通过新的 versioned surface / milestone 承载，而不是静默原地修改 `blueprint.v0` 或当前 Blueprint routes
- `contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md`
- P2-M7 仍保持只读、零副作用范围：不新增 endpoint、DB / dispatch / runtime 集成能力，不引入新的持久化语义

## 12. 相关实现位置

- `app/blueprint_sdk/__init__.py`
- `app/blueprint_sdk/artifacts.py`
- `app/api/v1/routes/blueprint_routes.py`
- `app/api/v1/router.py`
- `app/schemas/blueprint.py`
- `app/compilers/orchestrator/blueprint_compiler.py`
- `scripts/blueprint_self_check.py`
- `tests/test_blueprint_api_endpoints.py`
- `tests/test_blueprint_sdk_exports.py`
- `tests/test_blueprint_sdk_artifacts.py`
- `tests/test_blueprint_contract.py`

---

## 13. 非目标

本最小 API surface 当前不覆盖：

- Blueprint 文件上传
- Blueprint 持久化存储
- Blueprint DB-backed compile
- Blueprint -> Project/Sequence/SPU/VBU/Bridge 落库
- 生产 dispatch 编排
- provider 执行链整合
