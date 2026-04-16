from __future__ import annotations

import inspect
import unittest

from fastapi import APIRouter

import app.blueprint_sdk as blueprint_sdk
from app.api.v1.routes.blueprint_routes import (
    compile_blueprint_preview as compile_blueprint_preview_route,
    router as blueprint_router,
    validate_blueprint as validate_blueprint_route,
)
from app.blueprint_sdk import artifacts
from app.compilers.orchestrator.blueprint_compiler import compile_blueprint_v0_to_runtime_packet
from app.schemas import (
    BlueprintCompilePreviewRead,
    BlueprintV0,
    BlueprintValidationCountsV0,
    BlueprintValidationRead,
)


class BlueprintSdkExportsTests(unittest.TestCase):
    def test_package___all___matches_frozen_public_surface(self) -> None:
        self.assertEqual(
            blueprint_sdk.__all__,
            [
                "BlueprintV0",
                "BlueprintValidationCountsV0",
                "BlueprintValidationRead",
                "BlueprintCompilePreviewRead",
                "compile_blueprint_v0_to_runtime_packet",
                "validate_blueprint",
                "compile_blueprint_preview",
                "router",
                "get_blueprint_example_path",
                "load_blueprint_example_payload",
                "load_blueprint_example_v0",
                "get_blueprint_contract_doc_path",
                "load_blueprint_contract_doc_text",
                "get_blueprint_schema_path",
                "load_blueprint_schema_payload",
                "get_blueprint_artifact_paths",
            ],
        )

    def test_package_level_imports_resolve_to_expected_symbols(self) -> None:
        self.assertIs(blueprint_sdk.BlueprintV0, BlueprintV0)
        self.assertIs(blueprint_sdk.BlueprintValidationCountsV0, BlueprintValidationCountsV0)
        self.assertIs(blueprint_sdk.BlueprintValidationRead, BlueprintValidationRead)
        self.assertIs(blueprint_sdk.BlueprintCompilePreviewRead, BlueprintCompilePreviewRead)
        self.assertIs(
            blueprint_sdk.compile_blueprint_v0_to_runtime_packet,
            compile_blueprint_v0_to_runtime_packet,
        )
        self.assertIs(blueprint_sdk.validate_blueprint, validate_blueprint_route)
        self.assertIs(blueprint_sdk.compile_blueprint_preview, compile_blueprint_preview_route)
        self.assertIs(blueprint_sdk.router, blueprint_router)
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

    def test_route_module___all___matches_minimal_public_surface(self) -> None:
        self.assertEqual(
            blueprint_sdk.validate_blueprint.__module__,
            "app.api.v1.routes.blueprint_routes",
        )
        self.assertEqual(
            blueprint_sdk.compile_blueprint_preview.__module__,
            "app.api.v1.routes.blueprint_routes",
        )

    def test_compiler_and_route_signatures_remain_minimal_and_stable(self) -> None:
        self.assertEqual(
            list(inspect.signature(compile_blueprint_v0_to_runtime_packet).parameters.keys()),
            ["blueprint"],
        )
        self.assertEqual(
            list(inspect.signature(blueprint_sdk.validate_blueprint).parameters.keys()),
            ["payload"],
        )
        self.assertEqual(
            list(inspect.signature(blueprint_sdk.compile_blueprint_preview).parameters.keys()),
            ["payload"],
        )

    def test_router_surface_stays_package_visible(self) -> None:
        self.assertIsInstance(blueprint_sdk.router, APIRouter)


if __name__ == "__main__":
    unittest.main()
