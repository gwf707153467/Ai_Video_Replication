from __future__ import annotations

import unittest
from pathlib import Path

from pydantic import ValidationError

from app.blueprint_sdk import (
    get_blueprint_artifact_paths,
    get_blueprint_example_path,
    get_blueprint_schema_path,
    load_blueprint_contract_doc_text,
    load_blueprint_example_payload,
    load_blueprint_schema_payload,
)
from app.compilers.orchestrator.blueprint_compiler import compile_blueprint_v0_to_runtime_packet
from app.schemas import (
    BlueprintBridgeV0,
    BlueprintCompilePreferencesV0,
    BlueprintGlobalConstraintsV0,
    BlueprintProjectV0,
    BlueprintReferenceBeatV0,
    BlueprintReferenceMappingV0,
    BlueprintReferenceV0,
    BlueprintSequenceV0,
    BlueprintSPUV0,
    BlueprintV0,
    BlueprintVBUV0,
)

API_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "blueprint_api_contract.md"
FROZEN_SURFACE_MATRIX_PATH = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "blueprint_frozen_surface_matrix.md"
P2_M7_HANDOFF_NOTE_PATH = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "blueprint_p2_m7_completion_handoff_note.md"
CONTRACT_INVENTORY_PATH = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "blueprint_contract_inventory.md"


class BlueprintContractTests(unittest.TestCase):
    def test_schema_exports_are_visible_from_app_schemas(self) -> None:
        self.assertIsNotNone(BlueprintReferenceMappingV0)
        self.assertIsNotNone(BlueprintReferenceBeatV0)
        self.assertIsNotNone(BlueprintReferenceV0)
        self.assertIsNotNone(BlueprintProjectV0)
        self.assertIsNotNone(BlueprintCompilePreferencesV0)
        self.assertIsNotNone(BlueprintGlobalConstraintsV0)
        self.assertIsNotNone(BlueprintSPUV0)
        self.assertIsNotNone(BlueprintVBUV0)
        self.assertIsNotNone(BlueprintBridgeV0)
        self.assertIsNotNone(BlueprintSequenceV0)
        self.assertIsNotNone(BlueprintV0)

    def test_exported_json_schema_matches_model_title_and_version_literal(self) -> None:
        schema = load_blueprint_schema_payload()
        self.assertEqual(schema["title"], "BlueprintV0")
        self.assertEqual(schema["properties"]["blueprint_version"]["const"], "blueprint.v0")
        self.assertIn("$defs", schema)
        self.assertIn("BlueprintSequenceV0", schema["$defs"])

    def test_example_blueprint_validates(self) -> None:
        payload = load_blueprint_example_payload()
        blueprint = BlueprintV0.model_validate(payload)

        self.assertEqual(blueprint.blueprint_id, "beauty-lip-plumper-demo")
        self.assertEqual(len(blueprint.sequences), 4)
        self.assertEqual(blueprint.compile_preferences.requested_runtime_version, "beauty-lip-plumper-demo.v0")

    def test_example_blueprint_compiles_to_runtime_packet(self) -> None:
        payload = load_blueprint_example_payload()
        blueprint = BlueprintV0.model_validate(payload)
        runtime_packet = compile_blueprint_v0_to_runtime_packet(blueprint)

        self.assertEqual(runtime_packet.runtime_version, "beauty-lip-plumper-demo.v0")
        self.assertEqual(runtime_packet.compile_reason, "blueprint_stub")
        self.assertEqual(runtime_packet.visual_track_count, 4)
        self.assertEqual(runtime_packet.audio_track_count, 4)
        self.assertEqual(runtime_packet.bridge_count, 4)
        self.assertEqual([sequence.sequence_index for sequence in runtime_packet.sequences], [0, 1, 2, 3])
        self.assertEqual(
            [sequence["language"] for sequence in runtime_packet.sequences[0].vbus],
            ["en-US"],
        )
        self.assertEqual(runtime_packet.compile_options["blueprint_id"], "beauty-lip-plumper-demo")
        self.assertEqual(runtime_packet.compile_options["aspect_ratio"], "9:16")
        self.assertEqual(
            runtime_packet.compile_options["reference"]["reference_beats"][0]["sequence_code"],
            "hook",
        )

    def test_bridge_binding_validation_rejects_empty_binding(self) -> None:
        payload = load_blueprint_example_payload()
        payload["sequences"][0]["bridges"][0]["spu_code"] = None
        payload["sequences"][0]["bridges"][0]["vbu_code"] = None

        with self.assertRaises(ValidationError) as context:
            BlueprintV0.model_validate(payload)

        self.assertIn("bridge_requires_spu_or_vbu_binding", str(context.exception))

    def test_reference_beat_sequence_validation_rejects_unknown_sequence_code(self) -> None:
        payload = load_blueprint_example_payload()
        payload["reference"]["reference_beats"][0]["sequence_code"] = "missing-sequence"

        with self.assertRaises(ValidationError) as context:
            BlueprintV0.model_validate(payload)

        self.assertIn("reference_beat_sequence_missing:hook-open:missing-sequence", str(context.exception))

    def test_sdk_discovery_paths_match_expected_repo_artifacts(self) -> None:
        self.assertEqual(get_blueprint_example_path().name, "beauty_cosmetics_blueprint_v0.json")
        self.assertEqual(get_blueprint_schema_path().name, "blueprint_v0.schema.json")
        self.assertTrue(get_blueprint_example_path().exists())
        self.assertTrue(get_blueprint_schema_path().exists())

    def test_sdk_artifact_index_and_contract_markers_remain_stable(self) -> None:
        artifact_paths = get_blueprint_artifact_paths()
        contract_doc_text = load_blueprint_contract_doc_text()

        self.assertEqual(set(artifact_paths.keys()), {"example_payload", "contract_doc", "json_schema"})
        self.assertEqual(artifact_paths["example_payload"], get_blueprint_example_path())
        self.assertEqual(artifact_paths["json_schema"], get_blueprint_schema_path())
        self.assertEqual(artifact_paths["contract_doc"].name, "blueprint_v0_contract.md")
        self.assertIn("# Blueprint v0 Contract", contract_doc_text)
        self.assertIn("bridge_requires_spu_or_vbu_binding", contract_doc_text)
        self.assertIn("reference_beat_sequence_missing:<beat_code>:<sequence_code>", contract_doc_text)
        self.assertIn("## 11. Self-check 范围", contract_doc_text)
        self.assertIn("### 11.1 Fixture evolution policy", contract_doc_text)
        self.assertIn("fixture_change_requires_contract_review", contract_doc_text)
        self.assertIn("### 11.2 Contract change discipline", contract_doc_text)
        self.assertIn("contract_change_requires_guardrail_updates", contract_doc_text)
        self.assertIn("breaking_fixture_semantics_require_versioned_surface", contract_doc_text)
        self.assertIn("contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md", contract_doc_text)
        self.assertIn("## 12. 非目标与边界", contract_doc_text)

    def test_api_contract_includes_p2_m7_change_discipline_rules(self) -> None:
        self.assertTrue(API_CONTRACT_PATH.exists())
        api_contract_text = API_CONTRACT_PATH.read_text(encoding="utf-8")

        self.assertIn("## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline", api_contract_text)
        self.assertIn("fixture_change_requires_contract_review", api_contract_text)
        self.assertIn("contract_change_requires_guardrail_updates", api_contract_text)
        self.assertIn("breaking_fixture_semantics_require_versioned_surface", api_contract_text)
        self.assertIn("contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md", api_contract_text)
        self.assertIn("## 12. 相关实现位置", api_contract_text)
        self.assertIn("## 13. 非目标", api_contract_text)

    def test_frozen_surface_matrix_contains_governance_markers(self) -> None:
        self.assertTrue(FROZEN_SURFACE_MATRIX_PATH.exists())
        frozen_surface_matrix_text = FROZEN_SURFACE_MATRIX_PATH.read_text(encoding="utf-8")

        self.assertIn("# Blueprint Frozen Surface Matrix", frozen_surface_matrix_text)
        self.assertIn("canonical_fixture_path:docs/examples/beauty_cosmetics_blueprint_v0.json", frozen_surface_matrix_text)
        self.assertIn("frozen_sdk_export_surface:app.blueprint_sdk.__all__", frozen_surface_matrix_text)
        self.assertIn("frozen_artifact_index_keys:example_payload,contract_doc,json_schema", frozen_surface_matrix_text)
        self.assertIn("frozen_self_check_entry:scripts/blueprint_self_check.py", frozen_surface_matrix_text)
        self.assertIn(
            "frozen_acceptance_slice:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints",
            frozen_surface_matrix_text,
        )
        self.assertIn("frozen_surface_requires_explicit_contract_review", frozen_surface_matrix_text)
        self.assertIn("contract_change_requires_guardrail_updates", frozen_surface_matrix_text)
        self.assertIn("breaking_surface_change_requires_versioned_surface", frozen_surface_matrix_text)
        self.assertIn("continuity_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md", frozen_surface_matrix_text)
        self.assertIn("contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md", frozen_surface_matrix_text)
        self.assertIn("matrix is governance_artifact_not_completion_note", frozen_surface_matrix_text)
        self.assertIn("handoff note is continuity_artifact_not_surface_matrix", frozen_surface_matrix_text)

    def test_p2_m7_handoff_note_contains_cross_reference_markers(self) -> None:
        self.assertTrue(P2_M7_HANDOFF_NOTE_PATH.exists())
        handoff_note_text = P2_M7_HANDOFF_NOTE_PATH.read_text(encoding="utf-8")

        self.assertIn("governance_matrix_anchor:docs/contracts/blueprint_frozen_surface_matrix.md", handoff_note_text)
        self.assertIn("contract_inventory_anchor:docs/contracts/blueprint_contract_inventory.md", handoff_note_text)
        self.assertIn("authoritative_acceptance_section_anchor:## 6. P2-M7 验收结果", handoff_note_text)
        self.assertIn("authoritative_acceptance_unittest_anchor:### 6.1 unittest acceptance", handoff_note_text)
        self.assertIn("authoritative_acceptance_unittest_command:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints", handoff_note_text)
        self.assertIn("authoritative_acceptance_unittest_result:Ran 28 tests in 0.121s", handoff_note_text)
        self.assertIn("authoritative_acceptance_unittest_ok:OK", handoff_note_text)
        self.assertIn("authoritative_acceptance_self_check_anchor:### 6.2 self-check acceptance", handoff_note_text)
        self.assertIn("authoritative_acceptance_self_check_command:scripts/blueprint_self_check.py", handoff_note_text)
        self.assertIn("authoritative_acceptance_self_check_result:blueprint self-check ok", handoff_note_text)
        self.assertIn("### 6.3 Inventory section-anchor hardening completion", handoff_note_text)
        self.assertIn("section_anchor_hardening_completion_status:completed", handoff_note_text)
        self.assertIn("section_anchor_hardening_completion_scope:docs/tests/self-check_only", handoff_note_text)
        self.assertIn("section_anchor_hardening_inventory_entrypoint:docs/contracts/blueprint_contract_inventory.md", handoff_note_text)
        self.assertIn("section_anchor_hardening_inventory_role:authoritative_navigation_entrypoint_for_key_section_and_boundary_anchors", handoff_note_text)
        self.assertIn("section_anchor_hardening_guardrail_surfaces:tests/test_blueprint_contract.py,scripts/blueprint_self_check.py", handoff_note_text)
        self.assertIn("section_anchor_hardening_no_runtime_surface_change", handoff_note_text)
        self.assertIn("section_anchor_hardening_no_baseline_reopen", handoff_note_text)
        self.assertIn("### 9.1 只读交叉引用定位", handoff_note_text)
        self.assertIn("本 handoff note 的职责是固定 P2-M7 的完成结论、authoritative acceptance 与后续连续推进规则", handoff_note_text)
        self.assertIn("frozen surface matrix 的职责是固定 Blueprint line 的 frozen public surface、guardrail 联动关系与显式 contract review 纪律", handoff_note_text)
        self.assertIn("两者都属于 read-only / repo-local / zero-side-effect 文档面，但不应互相替代", handoff_note_text)

    def test_contract_inventory_contains_frozen_entries_and_guardrail_markers(self) -> None:
        self.assertTrue(CONTRACT_INVENTORY_PATH.exists())
        inventory_text = CONTRACT_INVENTORY_PATH.read_text(encoding="utf-8")

        self.assertIn("# Blueprint Contract Inventory", inventory_text)
        self.assertIn("inventory_scope:blueprint_contract_docs_only", inventory_text)
        self.assertIn("inventory_mode:read_only_repo_local_zero_side_effect", inventory_text)
        self.assertIn("inventory_entry_path:docs/contracts/blueprint_v0_contract.md", inventory_text)
        self.assertIn("inventory_entry_path:docs/contracts/blueprint_api_contract.md", inventory_text)
        self.assertIn("inventory_entry_path:docs/contracts/blueprint_frozen_surface_matrix.md", inventory_text)
        self.assertIn("inventory_entry_path:docs/contracts/blueprint_p2_m7_completion_handoff_note.md", inventory_text)
        self.assertIn("inventory_anchor_v0_contract:docs/contracts/blueprint_v0_contract.md", inventory_text)
        self.assertIn("inventory_anchor_api_contract:docs/contracts/blueprint_api_contract.md", inventory_text)
        self.assertIn("inventory_anchor_frozen_surface_matrix:docs/contracts/blueprint_frozen_surface_matrix.md", inventory_text)
        self.assertIn("inventory_anchor_p2_m7_handoff:docs/contracts/blueprint_p2_m7_completion_handoff_note.md", inventory_text)
        self.assertIn("inventory_section_anchor_v0_self_check:## 11. Self-check 范围", inventory_text)
        self.assertIn("inventory_section_anchor_v0_fixture_policy:### 11.1 Fixture evolution policy", inventory_text)
        self.assertIn("inventory_section_anchor_v0_contract_discipline:### 11.2 Contract change discipline", inventory_text)
        self.assertIn("inventory_section_anchor_api_p2_m7:## 11. P2-M7 Fixture Evolution Policy / Contract Change Discipline", inventory_text)
        self.assertIn("inventory_section_anchor_api_impl_locations:## 12. 相关实现位置", inventory_text)
        self.assertIn("inventory_section_anchor_api_non_goals:## 13. 非目标", inventory_text)
        self.assertIn("inventory_impl_anchor_sdk_init:app/blueprint_sdk/__init__.py", inventory_text)
        self.assertIn("inventory_impl_anchor_artifacts:app/blueprint_sdk/artifacts.py", inventory_text)
        self.assertIn("inventory_impl_anchor_routes:app/api/v1/routes/blueprint_routes.py", inventory_text)
        self.assertIn("inventory_impl_anchor_router:app/api/v1/router.py", inventory_text)
        self.assertIn("inventory_impl_anchor_schema:app/schemas/blueprint.py", inventory_text)
        self.assertIn("inventory_impl_anchor_compiler:app/compilers/orchestrator/blueprint_compiler.py", inventory_text)
        self.assertIn("inventory_impl_anchor_self_check:scripts/blueprint_self_check.py", inventory_text)
        self.assertIn("inventory_impl_anchor_test_api_endpoints:tests/test_blueprint_api_endpoints.py", inventory_text)
        self.assertIn("inventory_impl_anchor_test_sdk_exports:tests/test_blueprint_sdk_exports.py", inventory_text)
        self.assertIn("inventory_impl_anchor_test_sdk_artifacts:tests/test_blueprint_sdk_artifacts.py", inventory_text)
        self.assertIn("inventory_impl_anchor_test_contract:tests/test_blueprint_contract.py", inventory_text)
        self.assertIn("inventory_impl_locations_mirror_api_contract_section_12", inventory_text)
        self.assertIn("inventory_impl_locations_are_navigation_only", inventory_text)
        self.assertIn("inventory_impl_location_drift_requires_guardrail_updates", inventory_text)
        self.assertIn("inventory_section_anchor_matrix_role_split:matrix is governance_artifact_not_completion_note", inventory_text)
        self.assertIn("inventory_section_anchor_matrix_handoff_split:handoff note is continuity_artifact_not_surface_matrix", inventory_text)
        self.assertIn(
            "inventory_section_anchor_matrix_acceptance_handoff:authoritative_acceptance_handoff_anchor:docs/contracts/blueprint_p2_m7_completion_handoff_note.md",
            inventory_text,
        )
        self.assertIn("inventory_section_anchor_handoff_cross_reference:### 9.1 只读交叉引用定位", inventory_text)
        self.assertIn("inventory_section_anchor_handoff_matrix_link:governance_matrix_anchor:docs/contracts/blueprint_frozen_surface_matrix.md", inventory_text)
        self.assertIn(
            "inventory_section_anchor_handoff_acceptance:authoritative_acceptance_section_anchor:## 6. P2-M7 验收结果",
            inventory_text,
        )
        self.assertIn(
            "inventory_section_anchor_handoff_unittest_acceptance:authoritative_acceptance_unittest_anchor:### 6.1 unittest acceptance",
            inventory_text,
        )
        self.assertIn(
            "inventory_section_anchor_handoff_self_check_acceptance:authoritative_acceptance_self_check_anchor:### 6.2 self-check acceptance",
            inventory_text,
        )
        self.assertIn(
            "inventory_acceptance_unittest_command_marker:authoritative_acceptance_unittest_command:tests.test_blueprint_sdk_exports,tests.test_blueprint_sdk_artifacts,tests.test_blueprint_contract,tests.test_blueprint_api_endpoints",
            inventory_text,
        )
        self.assertIn(
            "inventory_acceptance_unittest_result_marker:authoritative_acceptance_unittest_result:Ran 28 tests in 0.121s",
            inventory_text,
        )
        self.assertIn("inventory_acceptance_unittest_ok_marker:authoritative_acceptance_unittest_ok:OK", inventory_text)
        self.assertIn(
            "inventory_acceptance_self_check_command_marker:authoritative_acceptance_self_check_command:scripts/blueprint_self_check.py",
            inventory_text,
        )
        self.assertIn(
            "inventory_acceptance_self_check_result_marker:authoritative_acceptance_self_check_result:blueprint self-check ok",
            inventory_text,
        )
        self.assertIn("inventory_guardrail_test:tests/test_blueprint_contract.py", inventory_text)
        self.assertIn("inventory_guardrail_self_check:scripts/blueprint_self_check.py", inventory_text)
        self.assertIn("inventory_requires_explicit_contract_review", inventory_text)
        self.assertIn("inventory_marker_drift_requires_guardrail_updates", inventory_text)
        self.assertIn("inventory_cross_reference_required_for_all_frozen_contract_docs", inventory_text)
        self.assertIn("inventory_missing_anchor_is_guardrail_failure", inventory_text)
        self.assertIn("inventory_section_anchor_drift_requires_guardrail_updates", inventory_text)
        self.assertIn("inventory_section_anchor_missing_is_guardrail_failure", inventory_text)
        self.assertIn("inventory_acceptance_anchor_drift_requires_guardrail_updates", inventory_text)
        self.assertIn("inventory_acceptance_anchor_missing_is_guardrail_failure", inventory_text)
        self.assertIn("inventory_is_governance_artifact_not_sdk_surface", inventory_text)
        self.assertIn("inventory_non_goal:no_sdk_surface_expansion", inventory_text)
        self.assertIn("inventory_non_goal:no_runtime_capability_expansion", inventory_text)
        self.assertIn("inventory_non_goal:no_baseline_reopen", inventory_text)


if __name__ == "__main__":
    unittest.main()
