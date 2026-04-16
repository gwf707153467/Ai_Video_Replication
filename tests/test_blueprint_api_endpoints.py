from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = REPO_ROOT / "docs" / "examples" / "beauty_cosmetics_blueprint_v0.json"


class BlueprintApiEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_db] = lambda: iter([object()])
        self.client = TestClient(app)
        self.example_payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def test_validate_blueprint_success_returns_exact_counts_and_runtime_passthrough(self) -> None:
        response = self.client.post("/api/v1/blueprints/validate", json=self.example_payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "blueprint_id": "beauty-lip-plumper-demo",
                "blueprint_version": "blueprint.v0",
                "is_valid": True,
                "counts": {
                    "sequences": 4,
                    "spus": 4,
                    "vbus": 4,
                    "bridges": 4,
                    "reference_beats": 4,
                },
                "requested_runtime_version": "beauty-lip-plumper-demo.v0",
                "effective_runtime_version": "beauty-lip-plumper-demo.v0",
                "dispatch_jobs": False,
            },
        )

    def test_validate_blueprint_success_returns_stub_runtime_when_version_missing(self) -> None:
        payload = json.loads(json.dumps(self.example_payload))
        payload["compile_preferences"]["requested_runtime_version"] = None

        response = self.client.post("/api/v1/blueprints/validate", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requested_runtime_version"], None)
        self.assertEqual(response.json()["effective_runtime_version"], "beauty-lip-plumper-demo.stub")
        self.assertEqual(
            response.json()["counts"],
            {
                "sequences": 4,
                "spus": 4,
                "vbus": 4,
                "bridges": 4,
                "reference_beats": 4,
            },
        )

    def test_compile_preview_success_returns_wrapped_runtime_packet_and_calls_compiler_once(self) -> None:
        runtime_packet = {
            "project_id": str(uuid4()),
            "runtime_version": "beauty-lip-plumper-demo.v0",
            "compile_reason": "blueprint_stub",
            "compile_options": {"blueprint_id": "beauty-lip-plumper-demo"},
            "visual_track_count": 4,
            "audio_track_count": 4,
            "bridge_count": 4,
            "sequences": [
                {
                    "sequence_id": str(uuid4()),
                    "sequence_index": 0,
                    "sequence_type": "hook",
                    "persuasive_goal": "Stop scroll immediately with visual payoff promise.",
                    "spus": [{"spu_code": "hook-visual"}],
                    "vbus": [{"vbu_code": "hook-voice"}],
                    "bridges": [{"bridge_code": "hook-bind"}],
                }
            ],
        }

        with patch(
            "app.api.v1.routes.blueprint_routes.compile_blueprint_v0_to_runtime_packet"
        ) as compile_mock:
            compile_mock.return_value = runtime_packet

            response = self.client.post("/api/v1/blueprints/compile-preview", json=self.example_payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "blueprint_id": "beauty-lip-plumper-demo",
                "blueprint_version": "blueprint.v0",
                "runtime_packet": runtime_packet,
            },
        )
        compile_mock.assert_called_once()
        request_model = compile_mock.call_args.args[0]
        self.assertEqual(request_model.blueprint_id, "beauty-lip-plumper-demo")
        self.assertEqual(request_model.blueprint_version, "blueprint.v0")
        self.assertEqual(len(request_model.sequences), 4)

    def test_validate_blueprint_invalid_payload_returns_422_and_surfaces_custom_validator_message(self) -> None:
        payload = json.loads(json.dumps(self.example_payload))
        payload["reference"]["reference_beats"][0]["sequence_code"] = "missing-sequence"

        response = self.client.post("/api/v1/blueprints/validate", json=payload)

        self.assertEqual(response.status_code, 422)
        self.assertTrue(
            any(
                item["msg"] == "Value error, reference_beat_sequence_missing:hook-open:missing-sequence"
                for item in response.json()["detail"]
            )
        )


if __name__ == "__main__":
    unittest.main()
