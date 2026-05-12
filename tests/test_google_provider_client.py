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
        operation_create = {
            "id": "video-123",
            "status": "queued",
            "model": "veo-test",
        }
        operation_done = {
            "id": "video-123",
            "status": "completed",
            "result": {
                "url": "https://cdn.example.com/generated-video.webm",
            },
        }
        download_response = MagicMock(
            status_code=200,
            headers={"content-type": "video/webm"},
            content=b"video-bytes",
        )
        http_client = MagicMock()
        http_client.request.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value=operation_create)),
            MagicMock(status_code=200, json=MagicMock(return_value=operation_done)),
        ]
        http_client.get.return_value = download_response
        context_client = MagicMock()
        context_client.__enter__.return_value = http_client
        context_client.__exit__.return_value = None

        with patch.object(provider_client, "_build_http_client", return_value=context_client):
            result = provider_client.generate_video(
                prompt="  cinematic product demo  ",
                negative_prompt="avoid clutter",
                sample_count=2,
                aspect_ratio="9:16",
                duration_seconds=6,
                fps=24,
                seed=7,
                resolution="1080x1920",
                person_generation="allow_adult",
                output_gcs_uri="gs://relay-output/video-123",
                enhance_prompt=True,
                compression_quality="optimized",
                last_frame={"url": "https://cdn.example.com/last-frame.png"},
                mask={"url": "https://cdn.example.com/mask.png"},
                reference_images=["https://cdn.example.com/input.png"],
                poll_interval_seconds=0.5,
                max_polls=3,
            )

        self.assertEqual(http_client.request.call_count, 2)
        create_call = http_client.request.call_args_list[0]
        self.assertEqual(create_call.args[:2], ("POST", "/v1/video/create"))
        self.assertEqual(
            create_call.kwargs["json"],
            {
                "model": "veo-test",
                "prompt": "cinematic product demo",
                "sample_count": 2,
                "negative_prompt": "avoid clutter",
                "aspect_ratio": "9:16",
                "duration_seconds": 6,
                "fps": 24,
                "seed": 7,
                "resolution": "1080x1920",
                "person_generation": "allow_adult",
                "output_gcs_uri": "gs://relay-output/video-123",
                "enhance_prompt": True,
                "compression_quality": "optimized",
                "last_frame": {"url": "https://cdn.example.com/last-frame.png"},
                "mask": {"url": "https://cdn.example.com/mask.png"},
                "images": ["https://cdn.example.com/input.png"],
            },
        )
        poll_call = http_client.request.call_args_list[1]
        self.assertEqual(poll_call.args[:2], ("GET", "/v1/videos/video-123"))
        http_client.get.assert_called_once_with("https://cdn.example.com/generated-video.webm")
        self.assertEqual(result.video_bytes, b"video-bytes")
        self.assertEqual(result.content_type, "video/webm")
        self.assertEqual(
            result.provider_payload,
            {
                "model": "veo-test",
                "sdk": "google-genai",
                "request": {
                    "sample_count": 2,
                    "aspect_ratio": "9:16",
                    "duration_seconds": 6,
                    "fps": 24,
                    "seed": 7,
                    "resolution": "1080x1920",
                    "person_generation": "allow_adult",
                    "output_gcs_uri": "gs://relay-output/video-123",
                    "enhance_prompt": True,
                    "compression_quality": "optimized",
                    "negative_prompt_present": True,
                    "reference_images_count": 1,
                    "poll_interval_seconds": 0.5,
                    "max_polls": 3,
                },
                "response": {
                    "operation_name": "video-123",
                    "operation_type": "dict",
                    "result_type": "dict",
                    "generated_videos_count": 1,
                    "video_uri": "https://cdn.example.com/generated-video.webm",
                },
            },
        )

    def test_generate_video_rejects_missing_prompt_before_http_call(self) -> None:
        provider_client = self._build_client()

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client.generate_video(prompt="   ")

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_video_prompt_missing")
        self.assertEqual(exc.message, "Google video generation prompt is missing.")

    def test_poll_video_operation_rejects_missing_operation(self) -> None:
        provider_client = self._build_client()

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._poll_video_operation(
                MagicMock(),
                None,
                poll_interval_seconds=0.0,
                max_polls=1,
            )

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_provider_response_invalid")
        self.assertEqual(exc.message, "Google video generation did not return an operation.")

    def test_poll_video_operation_maps_operation_error(self) -> None:
        provider_client = self._build_client()
        operation = SimpleNamespace(
            name="operations/video-failed",
            done=True,
            error=SimpleNamespace(code=500, message="provider exploded"),
        )

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._poll_video_operation(
                MagicMock(),
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
        operation = {"id": "operations/video-poll", "status": "queued"}
        client = MagicMock()
        client.request.side_effect = RuntimeError("poll boom")

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._poll_video_operation(
                client,
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
        operation = {"id": "operations/video-timeout", "status": "queued"}
        client = MagicMock()
        client.request.return_value = MagicMock(status_code=200, json=MagicMock(return_value=operation))

        with patch("app.providers.google.client.time.sleep") as sleep_mock:
            with self.assertRaises(GoogleProviderError) as exc_info:
                provider_client._poll_video_operation(
                    client,
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
        operation = {
            "id": "video-download",
            "status": "completed",
            "result": {"url": "https://cdn.example.com/generated-video.mp4"},
        }
        client = MagicMock()
        client.get.side_effect = RuntimeError("download boom")

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client._extract_generated_video(client, operation)

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_video_download_failed")
        self.assertEqual(
            exc.message,
            "Google video download failed for uri=https://cdn.example.com/generated-video.mp4: download boom",
        )


class GoogleProviderClientVoiceTests(unittest.TestCase):
    def _build_client(self) -> GoogleProviderClient:
        return GoogleProviderClient(
            api_key="test-google-key",
            video_model="veo-test",
            image_model="imagen-test",
            tts_model="gemini-tts-test",
        )

    def test_generate_voice_reports_unsupported_for_relay_provider(self) -> None:
        provider_client = self._build_client()

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client.generate_voice(
                text="  Hello.  ",
                voice_name="Zephyr",
                language_code="en-GB",
            )

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_tts_generation_failed")
        self.assertEqual(
            exc.message,
            "Google TTS generation is not supported by the configured relay provider.",
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

    def test_generate_voice_rejects_missing_text_before_support_check(self) -> None:
        provider_client = self._build_client()

        with self.assertRaises(GoogleProviderError) as exc_info:
            provider_client.generate_voice(text="   ")

        exc = exc_info.exception
        self.assertEqual(exc.code, "google_tts_text_missing")
        self.assertEqual(exc.message, "Google TTS input text is missing.")


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
        image_response = {
            "created": 123,
            "data": [
                {
                    "url": "https://cdn.example.com/generated-image.png",
                }
            ],
        }
        download_response = MagicMock(
            status_code=200,
            headers={"content-type": "image/png"},
            content=b"png-bytes",
        )
        http_client = MagicMock()
        http_client.request.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value=image_response),
        )
        http_client.get.return_value = download_response
        context_client = MagicMock()
        context_client.__enter__.return_value = http_client
        context_client.__exit__.return_value = None

        with patch.object(provider_client, "_build_http_client", return_value=context_client):
            result = provider_client.generate_image(
                prompt="product still",
                negative_prompt="ignore me",
                sample_count=2,
                aspect_ratio="1:1",
                safety_setting="block_only_high",
                person_generation="allow_adult",
            )

        http_client.request.assert_called_once_with(
            "POST",
            "/v1/images/generations",
            json={
                "model": "imagen-test",
                "prompt": "product still",
                "n": 2,
                "size": "1024x1024",
            },
        )
        http_client.get.assert_called_once_with("https://cdn.example.com/generated-image.png")
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
