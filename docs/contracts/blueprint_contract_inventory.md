# Blueprint Contract Inventory

## 1. 文档目的

本文档用于把当前 Blueprint line 下已经冻结、且会参与 guardrail 的 contract docs 做成单一只读 inventory，降低后续窗口只改某一份文档而忘记检查其余文档 marker 的漂移风险。

本文档只服务于 governance / guardrail：

- inventory_scope:blueprint_contract_docs_only
- inventory_mode:read_only_repo_local_zero_side_effect
- inventory_non_goal:no_sdk_surface_expansion
- inventory_non_goal:no_runtime_capability_expansion
- inventory_non_goal:no_baseline_reopen

---

## 2. Frozen contract doc inventory

### 2.1 Blueprint v0 schema / validation contract

- inventory_entry_path:docs/contracts/blueprint_v0_contract.md
- inventory_anchor_v0_contract:docs/contracts/blueprint_v0_contract.md
- inventory_entry_role:blueprint_schema_and_validation_contract
- inventory_required_markers:# Blueprint v0 Contract
- inventory_required_markers:bridge_requires_spu_or_vbu_binding
- inventory_required_markers:reference_beat_sequence_missing:<beat_code>:<sequence_code>
- inventory_required_markers:fixture_change_requires_contract_review
- inventory_required_markers:contract_change_requires_guardrail_updates
- inventory_required_markers:breaking_fixture_semantics_require_versioned_surface
- inventory_required_markers:contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md
- inventory_section_anchor_v0_self_check:## 11. Self-check 范围
- inventory_section_anchor_v0_fixture_policy:### 11.1 Fixture evolution policy
- inventory_section_anchor_v0_contract_discipline:### 11.2 Contract change discipline

### 2.2 Blueprint API surface contract

- inventory_entry_path:docs/contracts/blueprint_api_contract.md
- inventory_anchor_api_contract:docs/contracts/blueprint_api_contract.md
- inventory_entry_role:blueprint_api_surface_and_change_discipline
- inventory_required_markers:## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline
- inventory_required_markers:fixture_change_requires_contract_review
- inventory_required_markers:contract_change_requires_guardrail_updates
- inventory_required_markers:breaking_fixture_semantics_require_versioned_surface
- inventory_required_markers:contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md
- inventory_required_markers:## 12. 相关实现位置
- inventory_required_markers:## 13. 非目标
- inventory_section_anchor_api_p2_m7:## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline
- inventory_section_anchor_api_impl_locations:## 12. 相关实现位置
- inventory_section_anchor_api_non_goals:## 13. 非目标
- inventory_impl_anchor_sdk_init:app/blueprint_sdk/__init__.py
- inventory_impl_anchor_artifacts:app/blueprint_sdk/artifacts.py
- inventory_impl_anchor_routes:app/api/v1/routes/blueprint_routes.py
- inventory_impl_anchor_router:app/api/v1/router.py
- inventory_impl_anchor_schema:app/schemas/blueprint.py
- inventory_impl_anchor_compiler:app/compilers/orchestrator/blueprint_compiler.py
- inventory_impl_anchor_self_check:scripts/blueprint_self_check.py
- inventory_impl_anchor_test_api_endpoints:tests/test_blueprint_api_endpoints.py
- inventory_impl_anchor_test_sdk_exports:tests/test_blueprint_sdk_exports.py
- inventory_impl_anchor_test_sdk_artifacts:tests/test_blueprint_sdk_artifacts.py
- inventory_impl_anchor_test_contract:tests/test_blueprint_contract.py
- inventory_impl_locations_mirror_api_contract_section_12
- inventory_impl_locations_are_navigation_only
- inventory_impl_location_drift_requires_guardrail_updates

### 2.3 Frozen surface governance matrix

- inventory_entry_path:docs/contracts/blueprint_frozen_surface_matrix.md
- inventory_anchor_frozen_surface_matrix:docs/contracts/blueprint_frozen_surface_matrix.md
- inventory_entry_role:frozen_surface_inventory_and_guardrail_linkage
- inventory_required_markers:# Blueprint Frozen Surface Matrix
- inventory_required_markers:canonical_fixture_path:docs/examples/beauty_cosmetics_blueprint_v0.json
- inventory_required_markers:frozen_sdk_export_surface:app.blueprint_sdk.__all__
- inventory_required_markers:frozen_artifact_index_keys:example_payload,contract_doc,json_schema
- inventory_required_markers:frozen_self_check_entry:scripts/blueprint_self_check.py
- inventory_required_markers:frozen_acceptance_slice:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints
- inventory_required_markers:authoritative_acceptance_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md
- inventory_required_markers:frozen_surface_requires_explicit_contract_review
- inventory_required_markers:contract_change_requires_guardrail_updates
- inventory_required_markers:breaking_surface_change_requires_versioned_surface
- inventory_required_markers:continuity_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md
- inventory_required_markers:contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md
- inventory_section_anchor_matrix_role_split:matrix is governance_artifact_not_completion_note
- inventory_section_anchor_matrix_handoff_split:handoff note is continuity_artifact_not_surface_matrix
- inventory_section_anchor_matrix_acceptance_handoff:authoritative_acceptance_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md

### 2.4 P2-M7 continuity / acceptance handoff note

- inventory_entry_path:docs/contracts/blueprint_p2_m7_completion_handoff_note.md
- inventory_anchor_p2_m7_handoff:docs/contracts/blueprint_p2_m7_completion_handoff_note.md
- inventory_entry_role:continuity_and_authoritative_acceptance
- inventory_required_markers:governance_matrix_anchor:docs/contracts/blueprint_frozen_surface_matrix.md
- inventory_required_markers:contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md
- inventory_section_anchor_handoff_cross_reference:### 9.1 只读交叉引用定位
- inventory_section_anchor_handoff_matrix_link:governance_matrix_anchor:docs/contracts/blueprint_frozen_surface_matrix.md
- inventory_section_anchor_handoff_acceptance:authoritative_acceptance_section_anchor:## 6. P2-M7 验收结果
- inventory_section_anchor_handoff_unittest_acceptance:authoritative_acceptance_unittest_anchor:### 6.1 unittest acceptance
- inventory_section_anchor_handoff_self_check_acceptance:authoritative_acceptance_self_check_anchor:### 6.2 self-check acceptance
- inventory_acceptance_unittest_command_marker:authoritative_acceptance_unittest_command:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints
- inventory_acceptance_unittest_result_marker:authoritative_acceptance_unittest_result:Ran 28 tests in 0.121s
- inventory_acceptance_unittest_ok_marker:authoritative_acceptance_unittest_ok:OK
- inventory_acceptance_self_check_command_marker:authoritative_acceptance_self_check_command:scripts/blueprint_self_check.py
- inventory_acceptance_self_check_result_marker:authoritative_acceptance_self_check_result:blueprint self-check ok
- inventory_required_markers:本 handoff note 的职责是固定 P2-M7 的完成结论、authoritative acceptance 与后续连续推进规则
- inventory_required_markers:frozen surface matrix 的职责是固定 Blueprint line 的 frozen public surface、guardrail 联动关系与显式 contract review 纪律
- inventory_required_markers:两者都属于 read-only / repo-local / zero-side-effect 文档面，但不应互相替代

---

## 3. Guardrail anchoring

当前 inventory 的窄 guardrail 锚点固定为：

- inventory_guardrail_test:tests/test_blueprint_contract.py
- inventory_guardrail_self_check:scripts/blueprint_self_check.py
- inventory_requires_explicit_contract_review
- inventory_marker_drift_requires_guardrail_updates
- inventory_cross_reference_required_for_all_frozen_contract_docs
- inventory_missing_anchor_is_guardrail_failure
- inventory_section_anchor_drift_requires_guardrail_updates
- inventory_section_anchor_missing_is_guardrail_failure
- inventory_acceptance_anchor_drift_requires_guardrail_updates
- inventory_acceptance_anchor_missing_is_guardrail_failure
- inventory_is_governance_artifact_not_sdk_surface
- inventory_does_not_replace_underlying_contract_docs

---

## 4. 边界与非目标

本 inventory 只负责帮助识别“哪些 contract docs 与哪些 marker 已冻结并需要联动检查”，不承担以下职责：

- 不修改 `app.blueprint_sdk.artifacts`
- 不修改 `get_blueprint_artifact_paths()` 的 exact key set
- 不修改 `app.blueprint_sdk.__all__`
- 不扩展 Blueprint runtime capability
- 不进入 DB / dispatch / ingest / provider integration
- 不重开 baseline gate thread

一句话总结：

> inventory 用于收敛 contract doc 盘点与 marker drift guardrail，而不是用于新增 SDK surface、artifact index、route、schema version 或 runtime 行为。
