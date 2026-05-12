from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.routes.studio import _default_negative_prompt
from app.db.models import Bridge, Project, SPU, Sequence, VBU
from app.db.session import get_db
from app.main import app


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid4())

    def added_of_type(self, model_type: type) -> list[object]:
        return [item for item in self.added if isinstance(item, model_type)]


class StudioApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeSession()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def test_generate_multi_segment_success_creates_project_graph_and_calls_compiler(self) -> None:
        runtime_id = uuid4()
        project_id = uuid4()
        runtime = SimpleNamespace(id=runtime_id, runtime_version="runtime.v1")
        payload = {
            "project_name": "  Demo Launch  ",
            "target_market": "US",
            "target_language": "en-US",
            "product_name": "Lip Oil",
            "reference_note": "focus on glossy payoff",
            "segments": [
                {
                    "sequence_index": 1,
                    "sequence_type": "hook",
                    "persuasive_goal": "Stop the scroll",
                    "visual_prompt": "hero product close-up",
                    "voice_script": "Meet the shine upgrade.",
                    "negative_prompt": "avoid extra fingers",
                    "duration_ms": 4000,
                },
                {
                    "sequence_index": 2,
                    "sequence_type": "body",
                    "persuasive_goal": "Explain payoff",
                    "visual_prompt": "application demo on lips",
                    "duration_ms": 7000,
                },
            ],
        }

        with patch("app.api.v1.routes.studio.CompilerService.compile_project", return_value=runtime) as compile_mock:
            response = self.client.post("/api/v1/studio/generate", json=payload)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["runtime_id"], str(runtime_id))
        self.assertEqual(response_json["runtime_version"], "runtime.v1")

        projects = self.db.added_of_type(Project)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].name, "Demo Launch")
        self.assertEqual(projects[0].source_market, "US")
        self.assertEqual(projects[0].source_language, "en-US")
        project_id = projects[0].id
        self.assertEqual(response_json["project_id"], str(project_id))

        sequences = self.db.added_of_type(Sequence)
        spus = self.db.added_of_type(SPU)
        vbus = self.db.added_of_type(VBU)
        bridges = self.db.added_of_type(Bridge)
        self.assertEqual(len(sequences), 2)
        self.assertEqual(len(spus), 2)
        self.assertEqual(len(vbus), 1)
        self.assertEqual(len(bridges), 2)

        compile_mock.assert_called_once()
        request_model = compile_mock.call_args.args[0]
        self.assertEqual(request_model.project_id, project_id)
        self.assertEqual(request_model.compile_reason, "studio_generate")
        self.assertEqual(request_model.compile_options["source"], "studio_minimal_frontend")
        self.assertEqual(request_model.compile_options["studio_mode"], "multi_segment")
        self.assertEqual(request_model.compile_options["segment_count"], 2)
        self.assertEqual(request_model.compile_options["target_total_duration_ms"], 11000)
        self.assertEqual(request_model.compile_options["reference_note"], "focus on glossy payoff")
        self.assertTrue(request_model.auto_version)
        self.assertTrue(request_model.dispatch_jobs)

    def test_generate_multi_segment_normalizes_indexes_and_trim_fields(self) -> None:
        runtime = SimpleNamespace(id=uuid4(), runtime_version="runtime.v2")
        payload = {
            "project_name": "Normalization Demo",
            "target_market": "  ",
            "target_language": "  ",
            "product_name": "Serum Stick",
            "segments": [
                {
                    "visual_prompt": "  first reveal  ",
                    "voice_script": "   ",
                    "negative_prompt": "   ",
                    "duration_ms": 3000,
                },
                {
                    "sequence_index": 5,
                    "sequence_type": "  close  ",
                    "visual_prompt": "  payoff detail  ",
                    "voice_script": "  polished finish  ",
                    "negative_prompt": "  no blur  ",
                    "duration_ms": 4500,
                },
            ],
        }

        with patch("app.api.v1.routes.studio.CompilerService.compile_project", return_value=runtime):
            response = self.client.post("/api/v1/studio/generate", json=payload)

        self.assertEqual(response.status_code, 200)

        project = self.db.added_of_type(Project)[0]
        self.assertEqual(project.source_market, "US")
        self.assertEqual(project.source_language, "en-US")

        sequences = self.db.added_of_type(Sequence)
        spus = self.db.added_of_type(SPU)
        vbus = self.db.added_of_type(VBU)
        bridges = self.db.added_of_type(Bridge)

        self.assertEqual([sequence.sequence_index for sequence in sequences], [1, 5])
        self.assertEqual(sequences[0].sequence_type, "body")
        self.assertEqual(sequences[1].sequence_type, "close")
        self.assertEqual(spus[0].prompt_text, "first reveal")
        self.assertEqual(spus[1].prompt_text, "payoff detail")
        self.assertEqual(spus[0].negative_prompt_text, _default_negative_prompt())
        self.assertEqual(spus[1].negative_prompt_text, "no blur")
        self.assertEqual(len(vbus), 1)
        self.assertEqual(vbus[0].script_text, "polished finish")
        self.assertEqual(vbus[0].persuasive_role, "close")
        self.assertEqual([bridge.execution_order for bridge in bridges], [1, 5])

    def test_generate_legacy_single_segment_compatibility(self) -> None:
        runtime = SimpleNamespace(id=uuid4(), runtime_version="runtime.v3")
        payload = {
            "project_name": "Legacy Demo",
            "target_market": "CA",
            "target_language": "en-CA",
            "product_name": "Glow Tint",
            "visual_prompt": "  demo the tint texture  ",
            "voice_script": "  one swipe glow  ",
            "negative_prompt": "  no watermark  ",
            "duration_ms": 6500,
        }

        with patch("app.api.v1.routes.studio.CompilerService.compile_project", return_value=runtime) as compile_mock:
            response = self.client.post("/api/v1/studio/generate", json=payload)

        self.assertEqual(response.status_code, 200)

        sequences = self.db.added_of_type(Sequence)
        spus = self.db.added_of_type(SPU)
        vbus = self.db.added_of_type(VBU)
        self.assertEqual(len(sequences), 1)
        self.assertEqual(len(spus), 1)
        self.assertEqual(len(vbus), 1)
        self.assertEqual(sequences[0].sequence_index, 1)
        self.assertEqual(sequences[0].sequence_type, "hook")
        self.assertEqual(
            sequences[0].persuasive_goal,
            "Replicate a short-form ecommerce video for Glow Tint.",
        )
        self.assertEqual(spus[0].prompt_text, "demo the tint texture")
        self.assertEqual(spus[0].negative_prompt_text, "no watermark")
        self.assertEqual(vbus[0].script_text, "one swipe glow")

        request_model = compile_mock.call_args.args[0]
        self.assertEqual(request_model.compile_options["studio_mode"], "single_segment")
        self.assertEqual(request_model.compile_options["segment_count"], 1)
        self.assertEqual(request_model.compile_options["target_total_duration_ms"], 6500)

    def test_generate_requires_segments_or_legacy_visual_prompt(self) -> None:
        payload = {
            "project_name": "Invalid Demo",
            "target_market": "US",
            "target_language": "en-US",
            "product_name": "Lip Mask",
            "segments": [],
        }

        response = self.client.post("/api/v1/studio/generate", json=payload)

        self.assertEqual(response.status_code, 422)
        self.assertTrue(
            any(
                "either segments or legacy visual_prompt is required" in item["msg"]
                for item in response.json()["detail"]
            )
        )


if __name__ == "__main__":
    unittest.main()
