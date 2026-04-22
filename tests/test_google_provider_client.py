from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from google.genai import types

from app.providers.google.client import GoogleProviderClient, GoogleProviderError


class GoogleProviderClientVideoTests(unittest.TestCase):
    def _build_client(self) -> GoogleProviderClient:
        return GoogleProviderClient(
            api_key="test-google-key",
            video_model="veo-test",
            image_model="imagen-test",
            tts_model="gemini-tts-test",
        )

    def test_generate_video_success_path_returns_downloaded_bytes_and_request_summary(self) -> None:
        provider_client = self._build_client()
        video_file = SimpleNamespace(uri="gs://bucket/generated-video.webm", video_bytes=b"video-bytes")
        operation = SimpleNamespace(
            name="operations/video-123",
            done=True,
            result=SimpleNamespace(
                generated_videos=[SimpleNamespace(video=video_file)],
            ),
        )
        sdk_client = SimpleNamespace(
            models=SimpleNamespace(generate_videos=MagicMock(return_value=operation)),
            operations=SimpleNamespace(get=MagicMock()),
            files=SimpleNamespace(download=MagicMock()),
        )

        with patch("app.providers.google.client.genai.Client", return_value=sdk_client) as client_ctor:
            result = provider_client.generate_video(
                prompt="  cinematic product demo  ",
                negative_prompt="avoid clutter",
                sample_count=2,
                aspect_ratio="9:16",
                duration_seconds=6,
                resolution="1080x1920",
                poll_interval_seconds=0.5,
                max_polls=3,
            )

        client_ctor.assert_called_once_with(api_key="test-google-key")
        sdk_client.models.generate_videos.assert_called_once()
        call_kwargs = sdk_client.models.generate_videos.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "veo-test")
        self.assertEqual(call_kwargs["prompt"], "cinematic product demo")
        self.assertEqual(
            call_kwargs["config"].model_dump(exclude_none=True),
            {
                "number_of_videos": 2,
                "duration_seconds": 6,
                "aspect_ratio": "9:16",
                "resolution": "1080x1920",
                "negative_prompt": "avoid clutter",
            },
        )
        sdk_client.files.download.assert_called_once_with(file=video_file)
        self.assertEqual(result.video_bytes, b"video-bytes")
        self.assertEqual(result.content_type, "video/webm")
        self.assertNotIn("generate_audio", result.provider_payload["request"])
        self.assertEqual(
            result.provider_payload,
            {
                "model": "veo-test",
                "sdk": "google-genai",
                "request": {
                    "sample_count": 2,
                    "aspect_ratio": "9:16",
                    "duration_seconds": 6,
                    "fps": None,
                    "seed": None,
                    "resolution": "1080x1920",
                    "person_generation": None,
                    "output_gcs_uri": None,
                    "enhance_prompt": None,
                    "compression_quality": None,
                    "negative_prompt_present": True,
                    "reference_images_count": 0,
                    "poll_interval_seconds": 0.5,
                    "max_polls": 3,
                },
                "response": {
                    "operation_name": "operations/video-123",
                    "operation_type": "SimpleNamespace",
                    "result_type": "SimpleNamespace",
                    "generated_videos_count": 1,
                    "video_uri": "gs://bucket/generated-video.webm",
                },
            },
        )

    def test_generate_video_rejects_missing_prompt_before_sdk_call(self) -> None:
        provider_client = self._build_client()

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client.generate_video(prompt="   ")

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_video_prompt_missing")
        self.assertEqual(exc.message, "Google video generation prompt is missing.")

    def test_poll_video_operation_maps_operation_error(self) -> None:
        provider_client = self._build_client()
        sdk_client = SimpleNamespace(operations=SimpleNamespace(get=MagicMock()))
        operation = SimpleNamespace(
            name="operations/video-failed",
            done=True,
            error=SimpleNamespace(code=500, message="provider exploded"),
        )

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._poll_video_operation(
                sdk_client,
                operation,
                poll_interval_seconds=0.0,
                max_polls=1,
            )

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_video_generation_failed")
        self.assertEqual(
            exc.message,
            "Google video generation operation failed (operation=operations/video-failed, code=500): provider exploded",
        )

    def test_poll_video_operation_maps_poll_failure(self) -> None:
        provider_client = self._build_client()
        operation = SimpleNamespace(name="operations/video-poll", done=False)
        sdk_client = SimpleNamespace(
            operations=SimpleNamespace(get=MagicMock(side_effect=RuntimeError("poll boom"))),
        )

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._poll_video_operation(
                sdk_client,
                operation,
                poll_interval_seconds=0.0,
                max_polls=1,
            )

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_video_poll_failed")
        self.assertEqual(
            exc.message,
            "Google video generation operation polling failed for operations/video-poll: poll boom",
        )

    def test_poll_video_operation_times_out_after_max_polls(self) -> None:
        provider_client = self._build_client()
        operation = SimpleNamespace(name="operations/video-timeout", done=False)
        sdk_client = SimpleNamespace(
            operations=SimpleNamespace(get=MagicMock(return_value=operation)),
        )

        with patch("app.providers.google.client.time.sleep") as sleep_mock:
            with self.assertRaises(GoogleProviderError) as exc_info:
                provider_client._poll_video_operation(
                    sdk_client,
                    operation,
                    poll_interval_seconds=0.25,
                    max_polls=1,
                )

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_video_generation_timeout")
        self.assertEqual(
            exc.message,
            "Google video generation did not complete within poll limit (operation=operations/video-timeout, max_polls=1, poll_interval_seconds=0.25).",
        )
        sleep_mock.assert_called_once_with(0.25)

    def test_extract_generated_video_maps_download_failure(self) -> None:
        provider_client = self._build_client()
        video_file = SimpleNamespace(uri="gs://bucket/generated-video.mp4")
        operation = SimpleNamespace(
            name="operations/video-download",
            result=SimpleNamespace(generated_videos=[SimpleNamespace(video=video_file)]),
        )
        sdk_client = SimpleNamespace(
            files=SimpleNamespace(download=MagicMock(side_effect=RuntimeError("download boom"))),
        )

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._extract_generated_video(sdk_client, operation)

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_video_download_failed")
        self.assertEqual(
            exc.message,
            "Google video download failed for uri=gs://bucket/generated-video.mp4: download boom",
        )


class GoogleProviderClientVoiceTests(unittest.TestCase):
    def _build_client(self) -> GoogleProviderClient:
        return GoogleProviderClient(
            api_key="test-google-key",
            video_model="veo-test",
            image_model="imagen-test",
            tts_model="gemini-tts-test",
        )

    def test_generate_voice_success_path_returns_audio_bytes_and_request_summary(self) -> None:
        provider_client = self._build_client()
        response = SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(
                                inline_data=SimpleNamespace(
                                    data=b"voice-bytes",
                                    mime_type="audio/wav",
                                )
                            )
                        ]
                    )
                )
            ]
        )
        sdk_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=MagicMock(return_value=response)),
        )

        with patch("app.providers.google.client.genai.Client", return_value=sdk_client) as client_ctor:
            result = provider_client.generate_voice(
                text="  Hello.  ",
                voice_name="Zephyr",
                language_code="en-GB",
            )

        client_ctor.assert_called_once_with(api_key="test-google-key")
        sdk_client.models.generate_content.assert_called_once()
        call_kwargs = sdk_client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gemini-tts-test")
        self.assertEqual(call_kwargs["contents"], "Hello.")
        self.assertEqual(
            call_kwargs["config"].model_dump(exclude_none=True),
            {
                "response_modalities": ["audio"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": "Zephyr",
                        }
                    },
                    "language_code": "en-GB",
                },
            },
        )
        self.assertEqual(result.audio_bytes, b"voice-bytes")
        self.assertEqual(result.content_type, "audio/wav")
        self.assertEqual(
            result.provider_payload,
            {
                "model": "gemini-tts-test",
                "sdk": "google-genai",
                "request": {
                    "voice_name": "Zephyr",
                    "language_code": "en-GB",
                    "speech_config_present": True,
                    "speech_config_type": "SpeechConfig",
                    "text_length": 6,
                    "attempt_count": 1,
                },
                "response": {
                    "response_type": "SimpleNamespace",
                    "candidates_count": 1,
                    "candidate_index": 0,
                    "part_index": 0,
                },
            },
        )

    def test_build_speech_config_merges_voice_name_into_existing_speech_config(self) -> None:
        provider_client = self._build_client()
        speech_config = types.SpeechConfig(language_code="en-US")

        result = provider_client._build_speech_config(
            voice_name="Zephyr",
            language_code=None,
            speech_config=speech_config,
        )

        self.assertIsInstance(result, types.SpeechConfig)
        self.assertEqual(
            result.model_dump(exclude_none=True),
            {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": "Zephyr",
                    }
                },
                "language_code": "en-US",
            },
        )

    def test_build_speech_config_rejects_invalid_dict_shape(self) -> None:
        provider_client = self._build_client()

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._build_speech_config(
                voice_name=None,
                language_code=None,
                speech_config={"pitch": -2},
            )

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_tts_config_invalid")
        self.assertIn("Google TTS speech_config is invalid:", exc.message)
        self.assertIn("pitch", exc.message)

    def test_extract_generated_voice_rejects_non_bytes_inline_audio(self) -> None:
        provider_client = self._build_client()
        response = SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(
                                inline_data=SimpleNamespace(data="not-bytes", mime_type="audio/wav")
                            )
                        ]
                    )
                )
            ]
        )

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._extract_generated_voice(response)

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_provider_response_invalid")
        self.assertEqual(exc.message, "Google TTS inline audio payload is not bytes.")

    def test_generate_voice_retries_when_response_has_no_inline_audio(self) -> None:
        provider_client = self._build_client()
        retry_response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[]))])
        success_response = SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(
                                inline_data=SimpleNamespace(
                                    data=b"voice-bytes",
                                    mime_type="audio/wav",
                                )
                            )
                        ]
                    )
                )
            ]
        )
        sdk_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=MagicMock(side_effect=[retry_response, success_response])),
        )

        with patch("app.providers.google.client.genai.Client", return_value=sdk_client):
            with patch("app.providers.google.client.time.sleep") as sleep_mock:
                result = provider_client.generate_voice(text="Retry me.")

        self.assertEqual(result.audio_bytes, b"voice-bytes")
        self.assertEqual(result.provider_payload["request"]["attempt_count"], 2)
        self.assertEqual(sdk_client.models.generate_content.call_count, 2)
        sleep_mock.assert_called_once_with(provider_client.tts_retry_backoff_seconds)


class GoogleProviderClientImageAndHelperTests(unittest.TestCase):
    def _build_client(self) -> GoogleProviderClient:
        return GoogleProviderClient(
            api_key="test-google-key",
            video_model="veo-test",
            image_model="imagen-test",
            tts_model="gemini-tts-test",
        )

    def test_generate_image_success_path_returns_png_and_marks_negative_prompt_unforwarded(self) -> None:
        provider_client = self._build_client()
        response = SimpleNamespace(
            generated_images=[
                SimpleNamespace(
                    image=SimpleNamespace(image_bytes=b"png-bytes", mime_type="image/png"),
                )
            ]
        )
        sdk_client = SimpleNamespace(
            models=SimpleNamespace(generate_images=MagicMock(return_value=response)),
        )

        with patch("app.providers.google.client.genai.Client", return_value=sdk_client):
            result = provider_client.generate_image(
                prompt="product still",
                negative_prompt="ignore me",
                sample_count=2,
                aspect_ratio="1:1",
                safety_setting="block_only_high",
                person_generation="allow_adult",
            )

        sdk_client.models.generate_images.assert_called_once()
        call_kwargs = sdk_client.models.generate_images.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "imagen-test")
        self.assertEqual(call_kwargs["prompt"], "product still")
        self.assertEqual(
            call_kwargs["config"].model_dump(exclude_none=True),
            {
                "number_of_images": 2,
                "aspect_ratio": "1:1",
                "safety_filter_level": "BLOCK_ONLY_HIGH",
                "person_generation": "ALLOW_ADULT",
            },
        )
        self.assertEqual(result.image_bytes, b"png-bytes")
        self.assertEqual(result.content_type, "image/png")
        self.assertEqual(result.provider_payload["request"]["negative_prompt_present"], True)
        self.assertEqual(result.provider_payload["request"]["negative_prompt_forwarded"], False)

    def test_extract_generated_image_rejects_non_bytes_payload(self) -> None:
        provider_client = self._build_client()
        response = SimpleNamespace(
            generated_images=[
                SimpleNamespace(image=SimpleNamespace(image_bytes="not-bytes", mime_type="image/png"))
            ]
        )

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._extract_generated_image(response)

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_provider_response_invalid")
        self.assertEqual(exc.message, "Google image response returned non-bytes image payload.")

    def test_helper_functions_cover_content_type_inference_and_value_reads(self) -> None:
        self.assertEqual(
            GoogleProviderClient._infer_video_content_type("https://example.com/video.mov"),
            "video/quicktime",
        )
        self.assertEqual(
            GoogleProviderClient._infer_video_content_type("https://example.com/video.webm"),
            "video/webm",
        )
        self.assertEqual(
            GoogleProviderClient._infer_video_content_type("https://example.com/video.unknown"),
            "video/mp4",
        )
        self.assertEqual(
            GoogleProviderClient._read_value({"status": "ok"}, "status"),
            "ok",
        )
        self.assertEqual(
            GoogleProviderClient._read_value(SimpleNamespace(status="ok"), "status"),
            "ok",
        )
        self.assertEqual(
            GoogleProviderClient._read_value(SimpleNamespace(), "missing", default="fallback"),
            "fallback",
        )


if __name__ == "__main__":
    unittest.main()
