"""Stable package-level Blueprint public surface.

This package intentionally re-exports the minimal Blueprint contract entrypoints
landed across P2-M1 ~ P2-M6 so downstream callers can import a frozen, narrow
surface from ``app.blueprint_sdk`` without reaching into repo internals.
"""

from app.api.v1.routes.blueprint_routes import (
    compile_blueprint_preview,
    router,
    validate_blueprint,
)
from app.blueprint_sdk.artifacts import (
    get_blueprint_artifact_paths,
    get_blueprint_contract_doc_path,
    get_blueprint_example_path,
    get_blueprint_schema_path,
    load_blueprint_contract_doc_text,
    load_blueprint_example_payload,
    load_blueprint_example_v0,
    load_blueprint_schema_payload,
)
from app.compilers.orchestrator.blueprint_compiler import compile_blueprint_v0_to_runtime_packet
from app.schemas import (
    BlueprintCompilePreviewRead,
    BlueprintV0,
    BlueprintValidationCountsV0,
    BlueprintValidationRead,
)

__all__ = [
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
]
