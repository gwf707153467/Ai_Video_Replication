from __future__ import annotations

import unittest

import app.blueprint_sdk as blueprint_sdk
from app.blueprint_sdk import artifacts


class BlueprintSdkArtifactsTests(unittest.TestCase):
    def test_package___all___includes_artifact_accessors(self) -> None:
        self.assertIn("get_blueprint_example_path", blueprint_sdk.__all__)
        self.assertIn("load_blueprint_example_payload", blueprint_sdk.__all__)
        self.assertIn("load_blueprint_example_v0", blueprint_sdk.__all__)
        self.assertIn("get_blueprint_contract_doc_path", blueprint_sdk.__all__)
        self.assertIn("load_blueprint_contract_doc_text", blueprint_sdk.__all__)
        self.assertIn("get_blueprint_schema_path", blueprint_sdk.__all__)
        self.assertIn("load_blueprint_schema_payload", blueprint_sdk.__all__)
        self.assertIn("get_blueprint_artifact_paths", blueprint_sdk.__all__)

    def test_package_level_artifact_symbols_resolve_to_expected_functions(self) -> None:
        self.assertIs(blueprint_sdk.get_blueprint_example_path, artifacts.get_blueprint_example_path)
        self.assertIs(
            blueprint_sdk.load_blueprint_example_payload,
            artifacts.load_blueprint_example_payload,
        )
        self.assertIs(blueprint_sdk.load_blueprint_example_v0, artifacts.load_blueprint_example_v0)
        self.assertIs(
            blueprint_sdk.get_blueprint_contract_doc_path,
            artifacts.get_blueprint_contract_doc_path,
        )
        self.assertIs(
            blueprint_sdk.load_blueprint_contract_doc_text,
            artifacts.load_blueprint_contract_doc_text,
        )
        self.assertIs(blueprint_sdk.get_blueprint_schema_path, artifacts.get_blueprint_schema_path)
        self.assertIs(
            blueprint_sdk.load_blueprint_schema_payload,
            artifacts.load_blueprint_schema_payload,
        )
        self.assertIs(blueprint_sdk.get_blueprint_artifact_paths, artifacts.get_blueprint_artifact_paths)

    def test_example_path_is_stable_and_exists(self) -> None:
        path = blueprint_sdk.get_blueprint_example_path()
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "beauty_cosmetics_blueprint_v0.json")

    def test_example_payload_loads_expected_frozen_fixture(self) -> None:
        payload = blueprint_sdk.load_blueprint_example_payload()
        self.assertEqual(payload["blueprint_version"], "blueprint.v0")
        self.assertEqual(payload["blueprint_id"], "beauty-lip-plumper-demo")

    def test_example_blueprint_model_validates_successfully(self) -> None:
        blueprint = blueprint_sdk.load_blueprint_example_v0()
        self.assertEqual(blueprint.blueprint_id, "beauty-lip-plumper-demo")
        self.assertEqual(len(blueprint.sequences), 4)
        self.assertEqual(
            blueprint.compile_preferences.requested_runtime_version,
            "beauty-lip-plumper-demo.v0",
        )

    def test_contract_doc_path_is_stable_and_exists(self) -> None:
        path = blueprint_sdk.get_blueprint_contract_doc_path()
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "blueprint_v0_contract.md")

    def test_contract_doc_text_loads_expected_markers(self) -> None:
        contract_doc_text = blueprint_sdk.load_blueprint_contract_doc_text()
        self.assertIn("# Blueprint v0 Contract", contract_doc_text)
        self.assertIn("bridge_requires_spu_or_vbu_binding", contract_doc_text)
        self.assertIn("reference_beat_sequence_missing:<beat_code>:<sequence_code>", contract_doc_text)
        self.assertIn("## 11. Self-check 范围", contract_doc_text)
        self.assertIn("### 11.1 Fixture evolution policy", contract_doc_text)
        self.assertIn("fixture_change_requires_contract_review", contract_doc_text)
        self.assertIn("### 11.2 Contract change discipline", contract_doc_text)
        self.assertIn("contract_change_requires_guardrail_updates", contract_doc_text)
        self.assertIn("breaking_fixture_semantics_require_versioned_surface", contract_doc_text)
        self.assertIn("## 12. 非目标与边界", contract_doc_text)

    def test_schema_path_is_stable_and_exists(self) -> None:
        path = blueprint_sdk.get_blueprint_schema_path()
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "blueprint_v0.schema.json")

    def test_schema_payload_loads_expected_blueprint_schema(self) -> None:
        payload = blueprint_sdk.load_blueprint_schema_payload()
        self.assertEqual(payload["title"], "BlueprintV0")
        self.assertEqual(payload["properties"]["blueprint_version"]["const"], "blueprint.v0")
        self.assertIn("BlueprintSequenceV0", payload["$defs"])

    def test_artifact_paths_index_is_stable_and_repo_local(self) -> None:
        artifact_paths = blueprint_sdk.get_blueprint_artifact_paths()
        self.assertEqual(set(artifact_paths.keys()), {"example_payload", "contract_doc", "json_schema"})
        self.assertEqual(artifact_paths["example_payload"], blueprint_sdk.get_blueprint_example_path())
        self.assertEqual(artifact_paths["contract_doc"], blueprint_sdk.get_blueprint_contract_doc_path())
        self.assertEqual(artifact_paths["json_schema"], blueprint_sdk.get_blueprint_schema_path())
        self.assertTrue(all(path.exists() for path in artifact_paths.values()))


if __name__ == "__main__":
    unittest.main()
