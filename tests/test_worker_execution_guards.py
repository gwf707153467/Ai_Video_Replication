from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.workers.executors import (
    CompileRuntimeExecutor,
    FailHardMergeExecutor,
    GoogleVideoExecutor,
    GoogleVoiceExecutor,
    ProviderExecutorError,
    ProviderExecutorRegistry,
)
from app.workers.tasks import _validate_execution_result


class WorkerExecutionValidationTests(unittest.TestCase):
    def test_validate_execution_result_rejects_stub_success_for_runtime_job(self) -> None:
        with self.assertRaises(ProviderExecutorError) as raised:
            _validate_execution_result(
                {
                    "status": "succeeded_stub",
                    "provider": "stub",
                },
                task_name="render.video",
                asset_plan={
                    "asset_type": "generated_video",
                    "asset_role": "render_output",
                    "filename": "job-1.mp4",
                    "content_type": "video/mp4",
                },
            )

        self.assertEqual(raised.exception.code, "provider_stub_result_disallowed")
        self.assertEqual(
            raised.exception.message,
            "render.video returned succeeded_stub; stub success is forbidden for runtime jobs.",
        )

    def test_validate_execution_result_requires_binary_payload_for_image_asset(self) -> None:
        with self.assertRaises(ProviderExecutorError) as raised:
            _validate_execution_result(
                {
                    "status": "succeeded",
                    "provider": "google",
                },
                task_name="render.image",
                asset_plan={
                    "asset_type": "generated_image",
                    "asset_role": "render_output",
                    "filename": "job-image-1.png",
                    "content_type": "image/png",
                },
            )

        self.assertEqual(raised.exception.code, "binary_payload_required")
        self.assertEqual(
            raised.exception.message,
            "render.image requires binary_payload for image/png artifacts.",
        )

    def test_validate_execution_result_rejects_non_bytes_binary_payload_for_video_asset(self) -> None:
        with self.assertRaises(ProviderExecutorError) as raised:
            _validate_execution_result(
                {
                    "status": "succeeded",
                    "provider": "google",
                    "binary_payload": "not-bytes",
                },
                task_name="render.video",
                asset_plan={
                    "asset_type": "generated_video",
                    "asset_role": "render_output",
                    "filename": "job-video-1.mp4",
                    "content_type": "video/mp4",
                },
            )

        self.assertEqual(raised.exception.code, "binary_payload_invalid_type")
        self.assertEqual(
            raised.exception.message,
            "render.video produced non-bytes binary_payload for video/mp4 artifacts.",
        )

    def test_validate_execution_result_rejects_empty_binary_payload_for_voice_asset(self) -> None:
        with self.assertRaises(ProviderExecutorError) as raised:
            _validate_execution_result(
                {
                    "status": "succeeded",
                    "provider": "google",
                    "binary_payload": b"",
                },
                task_name="render.voice",
                asset_plan={
                    "asset_type": "audio",
                    "asset_role": "voice_output",
                    "filename": "job-voice-1.wav",
                    "content_type": "audio/wav",
                },
            )

        self.assertEqual(raised.exception.code, "binary_payload_empty")
        self.assertEqual(
            raised.exception.message,
            "render.voice produced empty binary_payload for audio/wav artifacts.",
        )

    def test_validate_execution_result_accepts_memoryview_binary_payload_for_merge_asset(self) -> None:
        _validate_execution_result(
            {
                "status": "succeeded",
                "provider": "google",
                "binary_payload": memoryview(b"merged-video"),
            },
            task_name="merge.runtime",
            asset_plan={
                "asset_type": "export",
                "asset_role": "merged_output",
                "filename": "runtime-v1-job-merge-1.mp4",
                "content_type": "video/mp4",
            },
        )


class FailHardMergeExecutorTests(unittest.TestCase):
    def test_execute_raises_fail_hard_error_after_runtime_payload_check(self) -> None:
        executor = FailHardMergeExecutor()
        executor._load_runtime_payload = MagicMock(
            return_value=(SimpleNamespace(runtime_version="runtime-v1"), {"project_id": "project-1"})
        )
        job = SimpleNamespace(id="job-merge-1", payload={}, job_type="merge")

        with self.assertRaises(ProviderExecutorError) as raised:
            executor.execute(
                job=job,
                project_id="project-1",
                runtime_version="runtime-v1",
                task_name="merge.runtime",
                asset_plan={
                    "asset_type": "export",
                    "asset_role": "merged_output",
                    "filename": "runtime-v1-job-merge-1.mp4",
                    "content_type": "video/mp4",
                },
            )

        executor._load_runtime_payload.assert_called_once_with(
            project_id="project-1",
            runtime_version="runtime-v1",
        )
        self.assertEqual(raised.exception.code, "merge_execution_not_ready")
        self.assertEqual(
            raised.exception.message,
            "merge.runtime real execution chain is not implemented yet: object-read + mux pipeline is required, stub success is disabled.",
        )


class GoogleVoiceExecutorRuntimeContextTests(unittest.TestCase):
    def test_resolve_voice_inputs_uses_runtime_vbu_defaults(self) -> None:
        executor = GoogleVoiceExecutor()
        executor._resolve_runtime_context = MagicMock(
            return_value=(
                SimpleNamespace(runtime_version="runtime-v1"),
                {"project_id": "project-1"},
                {},
                [
                    {
                        "sequence_id": "seq-1",
                        "sequence_code": "hook",
                        "sequence_index": 0,
                        "vbus": [
                            {
                                "vbu_id": "vbu-1",
                                "vbu_code": "voice-main",
                                "persuasive_role": "narrator",
                                "script_text": "Runtime narration for case-001.",
                                "language": "en-US",
                                "voice_profile": {"voice_name": "Aoede"},
                                "tts_params": {
                                    "voice_name": "Zephyr",
                                    "language_code": "en-GB",
                                    "speech_config": {"speaking_rate": 1.1},
                                },
                            }
                        ],
                    }
                ],
            )
        )
        job = SimpleNamespace(id="job-voice-runtime", payload={}, job_type="render_voice")

        text, voice_name, language_code, speech_config, selection_payload = executor._resolve_voice_inputs(
            job=job,
            project_id="project-1",
            runtime_version="runtime-v1",
        )

        executor._resolve_runtime_context.assert_called_once_with(
            project_id="project-1",
            runtime_version="runtime-v1",
        )
        self.assertEqual(text, "Runtime narration for case-001.")
        self.assertEqual(voice_name, "Zephyr")
        self.assertEqual(language_code, "en-GB")
        self.assertEqual(speech_config, {"speaking_rate": 1.1})
        self.assertEqual(
            selection_payload,
            {
                "sequence_id": "seq-1",
                "sequence_code": "hook",
                "sequence_index": 0,
                "vbu_id": "vbu-1",
                "vbu_code": "voice-main",
                "persuasive_role": "narrator",
                "text_source": "runtime_vbu",
            },
        )

    def test_resolve_voice_inputs_prefers_job_payload_over_runtime_vbu(self) -> None:
        executor = GoogleVoiceExecutor()
        executor._resolve_runtime_context = MagicMock(
            return_value=(
                SimpleNamespace(runtime_version="runtime-v1"),
                {"project_id": "project-1"},
                {},
                [
                    {
                        "sequence_id": "seq-2",
                        "sequence_code": "benefit",
                        "sequence_index": 1,
                        "vbus": [
                            {
                                "vbu_id": "vbu-2",
                                "vbu_code": "voice-override",
                                "persuasive_role": "seller",
                                "script_text": "Runtime text should be ignored.",
                                "language": "en-US",
                                "tts_params": {
                                    "voice_name": "RuntimeVoice",
                                    "language_code": "en-US",
                                    "speech_config": {"speaking_rate": 0.9},
                                },
                            }
                        ],
                    }
                ],
            )
        )
        job = SimpleNamespace(
            id="job-voice-payload",
            payload={
                "provider_inputs": {
                    "text": "Payload supplied text wins.",
                    "voice_name": "PayloadVoice",
                    "language_code": "zh-CN",
                    "speech_config": {"pitch": -2},
                }
            },
            job_type="render_voice",
        )

        text, voice_name, language_code, speech_config, selection_payload = executor._resolve_voice_inputs(
            job=job,
            project_id="project-1",
            runtime_version="runtime-v1",
        )

        self.assertEqual(text, "Payload supplied text wins.")
        self.assertEqual(voice_name, "PayloadVoice")
        self.assertEqual(language_code, "zh-CN")
        self.assertEqual(speech_config, {"pitch": -2})
        self.assertEqual(
            selection_payload,
            {
                "sequence_id": "seq-2",
                "sequence_code": "benefit",
                "sequence_index": 1,
                "vbu_id": "vbu-2",
                "vbu_code": "voice-override",
                "persuasive_role": "seller",
                "text_source": "job_payload",
            },
        )


class GoogleVideoExecutorRuntimeContextTests(unittest.TestCase):
    def test_resolve_video_inputs_builds_prompt_and_selection_from_runtime_spu(self) -> None:
        executor = GoogleVideoExecutor()
        executor._resolve_runtime_context = MagicMock(
            return_value=(
                SimpleNamespace(runtime_version="runtime-v1"),
                {"project_id": "project-1"},
                {
                    "aspect_ratio": "9:16",
                    "style_tags": {"pace": "fast", "tone": "confident"},
                    "reference": {
                        "structural_goal": "Hook then demo",
                        "retained_axes": {"camera": "close-up"},
                        "reference_beats": ["hook", "demo"],
                        "notes": "keep hands visible",
                    },
                    "banned_elements": {"watermark": "yes", "competitor": "BrandX"},
                },
                [
                    {
                        "sequence_id": "seq-video-1",
                        "sequence_code": "hook",
                        "sequence_index": 0,
                        "sequence_type": "opening",
                        "persuasive_goal": "stop the scroll",
                        "spus": [
                            {
                                "spu_id": "spu-1",
                                "spu_code": "shot-1",
                                "display_name": "Hero shot",
                                "prompt_text": "Close-up product reveal with hand interaction.",
                                "negative_prompt_text": "No cluttered background.",
                                "duration_ms": 6000,
                                "visual_constraints": {
                                    "resolution": "1080x1920",
                                    "person_generation": "allow_adult",
                                },
                                "reference_mapping": {"beat": "intro-product"},
                            }
                        ],
                    }
                ],
            )
        )
        job = SimpleNamespace(id="job-video-runtime", payload={}, job_type="render_video")

        prompt, negative_prompt, generation_options, selection_payload = executor._resolve_video_inputs(
            job=job,
            project_id="project-1",
            runtime_version="runtime-v1",
        )

        self.assertIn("Close-up product reveal with hand interaction.", prompt)
        self.assertIn("Project ID: project-1", prompt)
        self.assertIn("Sequence type: opening", prompt)
        self.assertIn("Persuasive goal: stop the scroll", prompt)
        self.assertIn("SPU display name: Hero shot", prompt)
        self.assertIn("Style tags: pace=fast, tone=confident", prompt)
        self.assertIn("Visual constraints: resolution=1080x1920, person_generation=allow_adult", prompt)
        self.assertIn("Reference mapping: beat=intro-product", prompt)
        self.assertIn(
            "Reference guidance: Hook then demo\n\ncamera=close-up\n\nhook, demo\n\nkeep hands visible",
            prompt,
        )
        self.assertEqual(
            negative_prompt,
            "No cluttered background.\n\nAvoid these elements: watermark=yes, competitor=BrandX",
        )
        self.assertNotIn("generate_audio", generation_options)
        self.assertEqual(
            generation_options,
            {
                "sample_count": 1,
                "aspect_ratio": "9:16",
                "duration_seconds": 6,
                "fps": None,
                "seed": None,
                "resolution": "1080x1920",
                "person_generation": "allow_adult",
                "output_gcs_uri": None,
                "enhance_prompt": None,
                "compression_quality": None,
                "last_frame": None,
                "mask": None,
                "reference_images": None,
                "poll_interval_seconds": None,
                "max_polls": None,
            },
        )
        self.assertEqual(
            selection_payload,
            {
                "sequence_id": "seq-video-1",
                "sequence_code": "hook",
                "sequence_index": 0,
                "spu_id": "spu-1",
                "spu_code": "shot-1",
                "display_name": "Hero shot",
                "prompt_source": "runtime_spu",
            },
        )


class CompileRuntimeExecutorTests(unittest.TestCase):
    def test_execute_returns_non_stub_success_from_runtime_payload(self) -> None:
        executor = CompileRuntimeExecutor()
        executor._resolve_runtime_context = MagicMock(
            return_value=(
                SimpleNamespace(
                    id="runtime-1",
                    runtime_version="runtime-v1",
                    compile_status="compiled",
                    dispatch_status="fully_dispatched",
                ),
                {
                    "project_id": "project-1",
                    "compile_options": {"aspect_ratio": "9:16", "style_tags": {"pace": "fast"}},
                    "sequences": [
                        {
                            "spus": [{"spu_id": "spu-1"}, {"spu_id": "spu-2"}],
                            "vbus": [{"vbu_id": "vbu-1"}],
                        },
                        {
                            "spus": [],
                            "vbus": [{"vbu_id": "vbu-2"}, {"vbu_id": "vbu-3"}],
                        },
                    ],
                },
                {"aspect_ratio": "9:16", "style_tags": {"pace": "fast"}},
                [
                    {
                        "spus": [{"spu_id": "spu-1"}, {"spu_id": "spu-2"}],
                        "vbus": [{"vbu_id": "vbu-1"}],
                    },
                    {
                        "spus": [],
                        "vbus": [{"vbu_id": "vbu-2"}, {"vbu_id": "vbu-3"}],
                    },
                ],
            )
        )
        job = SimpleNamespace(id="job-compile-1", payload={}, job_type="compile")

        result = executor.execute(
            job=job,
            project_id="project-1",
            runtime_version="runtime-v1",
            task_name="compile.runtime",
            asset_plan=None,
        )

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["provider"], "runtime_payload")
        self.assertEqual(result["content_type"], "text/plain; charset=utf-8")
        self.assertIn("compile runtime execution materialized from persisted runtime payload", result["text_payload"])
        self.assertIn("sequence_count=2", result["text_payload"])
        self.assertIn("spu_count=2", result["text_payload"])
        self.assertIn("vbu_count=3", result["text_payload"])
        self.assertEqual(
            result["provider_payload"],
            {
                "job_type": "compile",
                "task_name": "compile.runtime",
                "runtime_version": "runtime-v1",
                "provider_name": "runtime_payload",
                "runtime_id": "runtime-1",
                "runtime_compile_status": "compiled",
                "runtime_dispatch_status": "fully_dispatched",
                "payload_project_id": "project-1",
                "compile_options_keys": ["aspect_ratio", "style_tags"],
                "sequence_count": 2,
                "spu_count": 2,
                "vbu_count": 3,
            },
        )

    def test_compile_runtime_result_passes_worker_validation_without_asset_plan(self) -> None:
        executor = CompileRuntimeExecutor()
        executor._resolve_runtime_context = MagicMock(
            return_value=(
                SimpleNamespace(
                    id="runtime-2",
                    runtime_version="runtime-v2",
                    compile_status="compiled",
                    dispatch_status="not_dispatched",
                ),
                {
                    "project_id": "project-2",
                    "compile_options": {},
                    "sequences": [],
                },
                {},
                [],
            )
        )
        job = SimpleNamespace(id="job-compile-2", payload={}, job_type="compile")

        result = executor.execute(
            job=job,
            project_id="project-2",
            runtime_version="runtime-v2",
            task_name="compile.runtime",
            asset_plan=None,
        )

        _validate_execution_result(result, task_name="compile.runtime", asset_plan=None)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["provider"], "runtime_payload")

    def test_registry_resolves_compile_to_runtime_backed_executor(self) -> None:
        compile_executor = ProviderExecutorRegistry.resolve("compile")

        self.assertIsInstance(compile_executor, CompileRuntimeExecutor)
        self.assertNotEqual(compile_executor.provider_name, "stub")


if __name__ == "__main__":
    unittest.main()
