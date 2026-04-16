from __future__ import annotations

import json
from pathlib import Path

from app.schemas.blueprint import BlueprintV0


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "docs" / "contracts" / "schemas" / "blueprint_v0.schema.json"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = BlueprintV0.model_json_schema()
    OUTPUT_PATH.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"exported blueprint schema to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
