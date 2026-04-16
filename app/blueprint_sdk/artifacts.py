from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas import BlueprintV0


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
EXAMPLES_ROOT = DOCS_ROOT / "examples"
CONTRACTS_ROOT = DOCS_ROOT / "contracts"
SCHEMAS_ROOT = CONTRACTS_ROOT / "schemas"

BLUEPRINT_EXAMPLE_FILENAME = "beauty_cosmetics_blueprint_v0.json"
BLUEPRINT_CONTRACT_FILENAME = "blueprint_v0_contract.md"
BLUEPRINT_SCHEMA_FILENAME = "blueprint_v0.schema.json"


def get_blueprint_example_path() -> Path:
    """Return the frozen example Blueprint fixture path."""

    return EXAMPLES_ROOT / BLUEPRINT_EXAMPLE_FILENAME


def load_blueprint_example_payload() -> dict[str, Any]:
    """Load the frozen example Blueprint fixture payload."""

    return json.loads(get_blueprint_example_path().read_text(encoding="utf-8"))


def load_blueprint_example_v0() -> BlueprintV0:
    """Load and validate the frozen example Blueprint fixture."""

    return BlueprintV0.model_validate(load_blueprint_example_payload())


def get_blueprint_contract_doc_path() -> Path:
    """Return the frozen Blueprint V0 contract document path."""

    return CONTRACTS_ROOT / BLUEPRINT_CONTRACT_FILENAME


def load_blueprint_contract_doc_text() -> str:
    """Load the frozen Blueprint V0 contract document text."""

    return get_blueprint_contract_doc_path().read_text(encoding="utf-8")


def get_blueprint_schema_path() -> Path:
    """Return the frozen Blueprint V0 JSON schema path."""

    return SCHEMAS_ROOT / BLUEPRINT_SCHEMA_FILENAME


def load_blueprint_schema_payload() -> dict[str, Any]:
    """Load the frozen Blueprint V0 JSON schema payload."""

    return json.loads(get_blueprint_schema_path().read_text(encoding="utf-8"))


def get_blueprint_artifact_paths() -> dict[str, Path]:
    """Return the frozen repo-local Blueprint artifact path index."""

    return {
        "example_payload": get_blueprint_example_path(),
        "contract_doc": get_blueprint_contract_doc_path(),
        "json_schema": get_blueprint_schema_path(),
    }


__all__ = [
    "get_blueprint_example_path",
    "load_blueprint_example_payload",
    "load_blueprint_example_v0",
    "get_blueprint_contract_doc_path",
    "load_blueprint_contract_doc_text",
    "get_blueprint_schema_path",
    "load_blueprint_schema_payload",
    "get_blueprint_artifact_paths",
]
