# Blueprint Frozen Surface Matrix

## 1. 文档目的

本文档用于把当前 Blueprint line 的冻结 public surface、guardrail 依赖关系与变更联动要求整理成单一只读 artifact，防止后续窗口在不自觉的情况下扩展或漂移既有 contract 面。

本文档只服务于 governance / guardrail：

- read_only_repo_local_zero_side_effect
- 不扩展 runtime capability
- 不改变 baseline gate 逻辑、边界或判定语义
- 不引入 DB / dispatch / ingest / provider integration

---

## 2. Frozen surface inventory

当前冻结面按类别归纳如下。

### 2.1 Canonical fixture / contract-bearing example

- canonical_fixture_path:docs/examples/beauty_cosmetics_blueprint_v0.json
- fixture 不是普通示例，而是 contract-bearing example
- fixture 中冻结的 `blueprint_id`、`blueprint_version`、`requested_runtime_version`、`compile_reason`、`aspect_ratio`、sequence 顺序与 reference beat 对应关系，均属于 guardrail 范围

### 2.2 SDK export / discovery surface

- frozen_sdk_export_surface:app.blueprint_sdk.__all__
- frozen_artifact_index_keys:example_payload,contract_doc,json_schema
- `app.blueprint_sdk.artifacts` 与 package `__all__` 当前仅暴露已接受的最小 surface，不应通过新增 accessor 或新增 key 静默扩面

### 2.3 Route / response surface

- Blueprint route surface 继续限定为 validate / compile-preview 的纯内存只读入口
- 当前 route、response model、validator message 与 compile-preview 冻结预期均属于 contract surface
- 任何 breaking semantic change 都不能以“原地修改当前 surface”的方式落地

### 2.4 Self-check / acceptance slice

- frozen_self_check_entry:scripts/blueprint_self_check.py
- frozen_acceptance_slice:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints
- authoritative_acceptance_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md
- self-check 与 acceptance tests 共同构成 Blueprint line 的最小 consistency guardrail

---

## 3. 变更联动矩阵

| 变更类型 | 是否允许在当前 surface 内直接改动 | 必须同步更新 |
| --- | --- | --- |
| canonical fixture 内容调整 | 仅允许非 breaking 且经过明确审查 | contract docs / tests / self-check |
| schema 字段或 validator message 调整 | 仅允许窄范围、非 breaking 纪律化更新 | schema / docs / tests / self-check |
| SDK export surface 或 artifact index 调整 | 原则上不建议；若必须调整需明确 guardrail 联动 | docs / tests / self-check |
| route path / response model / compile-preview 预期调整 | 仅允许在明确 contract 变更下进行 | docs / tests / self-check |
| breaking semantic change | 不允许在当前 frozen surface 上静默修改 | 新 versioned surface / 新 milestone |

冻结纪律摘要：

- frozen_surface_requires_explicit_contract_review
- contract_change_requires_guardrail_updates
- breaking_surface_change_requires_versioned_surface

---

## 4. Narrow implementation rule

后续若继续沿 Blueprint 方向推进，默认只能做以下类型工作：

- 文档冻结面补充
- self-check 断言补强
- tests 对冻结 marker 的只读校验
- repo-local contract consistency hardening

明确禁止借此 surface 做以下扩展：

- DB persistence / migration
- dispatch / worker / queue integration
- ingest / upload parsing pipeline
- provider runtime integration
- 新 endpoint 或 runtime side effect

---

## 5. 结论

本 artifact 的作用不是提供新能力，而是明确指出：

1. 哪些面已经冻结
2. 哪些改动会触发联动更新义务
3. 哪些变化已经越过当前 Blueprint minimal package 的边界

后续若需要扩展能力，应通过新的 versioned surface 或新的 milestone 处理，而不是修改当前 frozen line。

## 6. Handoff / governance split

- continuity_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md
- contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md
- frozen_surface_matrix 负责冻结 surface inventory、guardrail linkage 与 breaking-change discipline
- p2_m7_completion_handoff_note 负责冻结 authoritative acceptance、continuity framing 与下一窗口推进规则
- matrix is governance_artifact_not_completion_note
- handoff note is continuity_artifact_not_surface_matrix
- 两者交叉引用的目的只是防漂移，不代表扩展 SDK / artifact index / runtime capability
