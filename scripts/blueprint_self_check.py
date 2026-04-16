from __future__ import annotations

from pathlib import Path

from app.blueprint_sdk import (
    compile_blueprint_v0_to_runtime_packet,
    get_blueprint_artifact_paths,
    get_blueprint_schema_path,
    load_blueprint_contract_doc_text,
    load_blueprint_example_payload,
    load_blueprint_example_v0,
    load_blueprint_schema_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
API_CONTRACT_PATH = REPO_ROOT / "docs" / "contracts" / "blueprint_api_contract.md"
FROZEN_SURFACE_MATRIX_PATH = REPO_ROOT / "docs" / "contracts" / "blueprint_frozen_surface_matrix.md"
P2_M7_HANDOFF_NOTE_PATH = REPO_ROOT / "docs" / "contracts" / "blueprint_p2_m7_completion_handoff_note.md"
CONTRACT_INVENTORY_PATH = REPO_ROOT / "docs" / "contracts" / "blueprint_contract_inventory.md"
EXPECTED_ARTIFACT_KEYS = {"example_payload", "contract_doc", "json_schema"}
EXPECTED_CONTRACT_MARKERS = (
    "# Blueprint v0 Contract",
    "bridge_requires_spu_or_vbu_binding",
    "reference_beat_sequence_missing:<beat_code>:<sequence_code>",
    "## 11. Self-check 范围",
    "### 11.1 Fixture evolution policy",
    "fixture_change_requires_contract_review",
    "### 11.2 Contract change discipline",
    "contract_change_requires_guardrail_updates",
    "breaking_fixture_semantics_require_versioned_surface",
    "contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md",
    "## 12. 非目标与边界",
)
EXPECTED_API_CONTRACT_MARKERS = (
    "## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline",
    "fixture_change_requires_contract_review",
    "contract_change_requires_guardrail_updates",
    "breaking_fixture_semantics_require_versioned_surface",
    "contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md",
    "## 12. 相关实现位置",
    "## 13. 非目标",
)
EXPECTED_FROZEN_SURFACE_MATRIX_MARKERS = (
    "# Blueprint Frozen Surface Matrix",
    "canonical_fixture_path:docs/examples/beauty_cosmetics_blueprint_v0.json",
    "frozen_sdk_export_surface:app.blueprint_sdk.__all__",
    "frozen_artifact_index_keys:example_payload,contract_doc,json_schema",
    "frozen_self_check_entry:scripts/blueprint_self_check.py",
    "frozen_acceptance_slice:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints",
    "authoritative_acceptance_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md",
    "frozen_surface_requires_explicit_contract_review",
    "contract_change_requires_guardrail_updates",
    "breaking_surface_change_requires_versioned_surface",
    "continuity_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md",
    "contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md",
    "matrix is governance_artifact_not_completion_note",
    "handoff note is continuity_artifact_not_surface_matrix",
)
EXPECTED_P2_M7_HANDOFF_NOTE_MARKERS = (
    "governance_matrix_anchor:docs/contracts/blueprint_frozen_surface_matrix.md",
    "contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md",
    "### 9.1 只读交叉引用定位",
    "authoritative_acceptance_section_anchor:## 6. P2-M7 验收结果",
    "authoritative_acceptance_unittest_anchor:### 6.1 unittest acceptance",
    "authoritative_acceptance_unittest_command:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints",
    "authoritative_acceptance_unittest_result:Ran 28 tests in 0.121s",
    "authoritative_acceptance_unittest_ok:OK",
    "authoritative_acceptance_self_check_anchor:### 6.2 self-check acceptance",
    "authoritative_acceptance_self_check_command:scripts/blueprint_self_check.py",
    "authoritative_acceptance_self_check_result:blueprint self-check ok",
    "### 6.3 Inventory section-anchor hardening completion",
    "section_anchor_hardening_completion_status:completed",
    "section_anchor_hardening_completion_scope:docs/tests/self-check_only",
    "section_anchor_hardening_inventory_entrypoint:docs/contracts/blueprint_contract_inventory.md",
    "section_anchor_hardening_inventory_role:authoritative_navigation_entrypoint_for_key_section_and_boundary_anchors",
    "section_anchor_hardening_guardrail_surfaces:tests/test_blueprint_contract.py,scripts/blueprint_self_check.py",
    "section_anchor_hardening_no_runtime_surface_change",
    "section_anchor_hardening_no_baseline_reopen",
    "本 handoff note 的职责是固定 P2-M7 的完成结论、authoritative acceptance 与后续连续推进规则",
    "frozen surface matrix 的职责是固定 Blueprint line 的 frozen public surface、guardrail 联动关系与显式 contract review 纪律",
    "两者都属于 read-only / repo-local / zero-side-effect 文档面，但不应互相替代",
)
EXPECTED_CONTRACT_INVENTORY_MARKERS = (
    "# Blueprint Contract Inventory",
    "inventory_scope:blueprint_contract_docs_only",
    "inventory_mode:read_only_repo_local_zero_side_effect",
    "inventory_entry_path:docs/contracts/blueprint_v0_contract.md",
    "inventory_entry_path:docs/contracts/blueprint_api_contract.md",
    "inventory_entry_path:docs/contracts/blueprint_frozen_surface_matrix.md",
    "inventory_entry_path:docs/contracts/blueprint_p2_m7_completion_handoff_note.md",
    "inventory_anchor_v0_contract:docs/contracts/blueprint_v0_contract.md",
    "inventory_anchor_api_contract:docs/contracts/blueprint_api_contract.md",
    "inventory_anchor_frozen_surface_matrix:docs/contracts/blueprint_frozen_surface_matrix.md",
    "inventory_anchor_p2_m7_handoff:docs/contracts/blueprint_p2_m7_completion_handoff_note.md",
    "inventory_section_anchor_v0_self_check:## 11. Self-check 范围",
    "inventory_section_anchor_v0_fixture_policy:### 11.1 Fixture evolution policy",
    "inventory_section_anchor_v0_contract_discipline:### 11.2 Contract change discipline",
    "inventory_section_anchor_api_p2_m7:## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline",
    "inventory_section_anchor_api_impl_locations:## 12. 相关实现位置",
    "inventory_section_anchor_api_non_goals:## 13. 非目标",
    "inventory_impl_anchor_sdk_init:app/blueprint_sdk/__init__.py",
    "inventory_impl_anchor_artifacts:app/blueprint_sdk/artifacts.py",
    "inventory_impl_anchor_routes:app/api/v1/routes/blueprint_routes.py",
    "inventory_impl_anchor_router:app/api/v1/router.py",
    "inventory_impl_anchor_schema:app/schemas/blueprint.py",
    "inventory_impl_anchor_compiler:app/compilers/orchestrator/blueprint_compiler.py",
    "inventory_impl_anchor_self_check:scripts/blueprint_self_check.py",
    "inventory_impl_anchor_test_api_endpoints:tests/test_blueprint_api_endpoints.py",
    "inventory_impl_anchor_test_sdk_exports:tests/test_blueprint_sdk_exports.py",
    "inventory_impl_anchor_test_sdk_artifacts:tests/test_blueprint_sdk_artifacts.py",
    "inventory_impl_anchor_test_contract:tests/test_blueprint_contract.py",
    "inventory_impl_locations_mirror_api_contract_section_12",
    "inventory_impl_locations_are_navigation_only",
    "inventory_impl_location_drift_requires_guardrail_updates",
    "inventory_section_anchor_matrix_role_split:matrix is governance_artifact_not_completion_note",
    "inventory_section_anchor_matrix_handoff_split:handoff note is continuity_artifact_not_surface_matrix",
    "inventory_section_anchor_matrix_acceptance_handoff:authoritative_acceptance_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md",
    "inventory_section_anchor_handoff_cross_reference:### 9.1 只读交叉引用定位",
    "inventory_section_anchor_handoff_matrix_link:governance_matrix_anchor:docs/contracts/blueprint_frozen_surface_matrix.md",
    "inventory_section_anchor_handoff_acceptance:authoritative_acceptance_section_anchor:## 6. P2-M7 验收结果",
    "inventory_section_anchor_handoff_unittest_acceptance:authoritative_acceptance_unittest_anchor:### 6.1 unittest acceptance",
    "inventory_section_anchor_handoff_self_check_acceptance:authoritative_acceptance_self_check_anchor:### 6.2 self-check acceptance",
    "inventory_acceptance_unittest_command_marker:authoritative_acceptance_unittest_command:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints",
    "inventory_acceptance_unittest_result_marker:authoritative_acceptance_unittest_result:Ran 28 tests in 0.121s",
    "inventory_acceptance_unittest_ok_marker:authoritative_acceptance_unittest_ok:OK",
    "inventory_acceptance_self_check_command_marker:authoritative_acceptance_self_check_command:scripts/blueprint_self_check.py",
    "inventory_acceptance_self_check_result_marker:authoritative_acceptance_self_check_result:blueprint self-check ok",
    "inventory_guardrail_test:tests/test_blueprint_contract.py",
    "inventory_guardrail_self_check:scripts/blueprint_self_check.py",
    "inventory_requires_explicit_contract_review",
    "inventory_marker_drift_requires_guardrail_updates",
    "inventory_cross_reference_required_for_all_frozen_contract_docs",
    "inventory_missing_anchor_is_guardrail_failure",
    "inventory_section_anchor_drift_requires_guardrail_updates",
    "inventory_section_anchor_missing_is_guardrail_failure",
    "inventory_acceptance_anchor_drift_requires_guardrail_updates",
    "inventory_acceptance_anchor_missing_is_guardrail_failure",
    "inventory_is_governance_artifact_not_sdk_surface",
    "inventory_non_goal:no_sdk_surface_expansion",
    "inventory_non_goal:no_runtime_capability_expansion",
    "inventory_non_goal:no_baseline_reopen",
)
EXPECTED_SCHEMA_MARKERS = (
    "BlueprintV0",
    "blueprint.v0",
    "BlueprintSequenceV0",
)
EXPECTED_SEQUENCE_CODES = ["hook", "problem", "demo", "cta"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    _assert(API_CONTRACT_PATH.exists(), "api_contract_missing")
    _assert(FROZEN_SURFACE_MATRIX_PATH.exists(), "frozen_surface_matrix_missing")
    _assert(P2_M7_HANDOFF_NOTE_PATH.exists(), "p2_m7_handoff_note_missing")
    _assert(CONTRACT_INVENTORY_PATH.exists(), "contract_inventory_missing")

    blueprint_payload = load_blueprint_example_payload()
    blueprint = load_blueprint_example_v0()
    runtime_packet = compile_blueprint_v0_to_runtime_packet(blueprint)
    artifact_paths = get_blueprint_artifact_paths()
    contract_doc_text = load_blueprint_contract_doc_text()
    api_contract_text = API_CONTRACT_PATH.read_text(encoding="utf-8")
    frozen_surface_matrix_text = FROZEN_SURFACE_MATRIX_PATH.read_text(encoding="utf-8")
    p2_m7_handoff_note_text = P2_M7_HANDOFF_NOTE_PATH.read_text(encoding="utf-8")
    contract_inventory_text = CONTRACT_INVENTORY_PATH.read_text(encoding="utf-8")
    schema_payload = load_blueprint_schema_payload()
    schema_path = get_blueprint_schema_path()

    _assert(set(artifact_paths.keys()) == EXPECTED_ARTIFACT_KEYS, "artifact_index_keys_mismatch")
    _assert(artifact_paths["example_payload"].name == "beauty_cosmetics_blueprint_v0.json", "example_fixture_path_name_mismatch")
    _assert(artifact_paths["contract_doc"].name == "blueprint_v0_contract.md", "contract_doc_path_name_mismatch")
    _assert(artifact_paths["json_schema"] == schema_path, "schema_path_index_mismatch")
    _assert(blueprint_payload["blueprint_version"] == "blueprint.v0", "example_blueprint_version_mismatch")
    _assert(blueprint_payload["blueprint_id"] == "beauty-lip-plumper-demo", "example_blueprint_id_mismatch")
    _assert(
        blueprint_payload["compile_preferences"]["requested_runtime_version"] == "beauty-lip-plumper-demo.v0",
        "example_requested_runtime_version_mismatch",
    )
    _assert(
        blueprint_payload["compile_preferences"]["compile_reason"] == "blueprint_stub",
        "example_compile_reason_mismatch",
    )
    _assert(blueprint.blueprint_version == "blueprint.v0", "validated_blueprint_version_mismatch")
    _assert([sequence.sequence_code for sequence in blueprint.sequences] == EXPECTED_SEQUENCE_CODES, "sequence_code_order_mismatch")
    _assert(schema_payload["title"] == EXPECTED_SCHEMA_MARKERS[0], "schema_title_mismatch")
    _assert(
        schema_payload["properties"]["blueprint_version"]["const"] == EXPECTED_SCHEMA_MARKERS[1],
        "schema_version_literal_mismatch",
    )
    _assert(EXPECTED_SCHEMA_MARKERS[2] in schema_payload["$defs"], "schema_sequence_def_missing")
    _assert(runtime_packet.runtime_version == "beauty-lip-plumper-demo.v0", "runtime_version_mismatch")
    _assert(runtime_packet.compile_options["blueprint_id"] == blueprint.blueprint_id, "compile_option_blueprint_id_mismatch")
    _assert(
        runtime_packet.compile_options["reference"]["reference_beats"][0]["sequence_code"] == "hook",
        "reference_beat_sequence_code_mismatch",
    )
    for marker in EXPECTED_CONTRACT_MARKERS:
        _assert(marker in contract_doc_text, f"contract_marker_missing:{marker}")
    for marker in EXPECTED_API_CONTRACT_MARKERS:
        _assert(marker in api_contract_text, f"api_contract_marker_missing:{marker}")
    for marker in EXPECTED_FROZEN_SURFACE_MATRIX_MARKERS:
        _assert(marker in frozen_surface_matrix_text, f"frozen_surface_matrix_marker_missing:{marker}")
    for marker in EXPECTED_P2_M7_HANDOFF_NOTE_MARKERS:
        _assert(marker in p2_m7_handoff_note_text, f"p2_m7_handoff_note_marker_missing:{marker}")
    for marker in EXPECTED_CONTRACT_INVENTORY_MARKERS:
        _assert(marker in contract_inventory_text, f"contract_inventory_marker_missing:{marker}")

    print("blueprint self-check ok")
    print(f"blueprint_id={blueprint.blueprint_id}")
    print(f"runtime_version={runtime_packet.runtime_version}")
    print(f"sequence_count={len(runtime_packet.sequences)}")
    print(f"visual_track_count={runtime_packet.visual_track_count}")
    print(f"audio_track_count={runtime_packet.audio_track_count}")
    print(f"bridge_count={runtime_packet.bridge_count}")
    print(f"artifact_index_keys={sorted(artifact_paths.keys())}")
    print(f"example_path={artifact_paths['example_payload']}")
    print(f"contract_doc_path={artifact_paths['contract_doc']}")
    print(f"schema_path={schema_path}")
    print(f"api_contract_path={API_CONTRACT_PATH}")
    print(f"contract_inventory_path={CONTRACT_INVENTORY_PATH}")


if __name__ == "__main__":
    main()
