from __future__ import annotations

import base64
from dataclasses import dataclass
import time
from typing import Any
from urllib.parse import quote

import httpx
from google.genai import types


class GoogleProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class GoogleGeneratedImage:
    image_bytes: bytes
    content_type: str
    provider_payload: dict


@dataclass
class GoogleGeneratedVideo:
    video_bytes: bytes
    content_type: str
    provider_payload: dict


@dataclass
class GoogleGeneratedVoice:
    audio_bytes: bytes
    content_type: str
    provider_payload: dict


class GoogleProviderClient:
    relay_base_url = "https://ai.ai666.net"

    def __init__(self, api_key: str, video_model: str, image_model: str, tts_model: str) -> None:
        self.api_key = api_key
        self.video_model = video_model
        self.image_model = image_model
        self.tts_model = tts_model
        self.timeout = 120.0
        self.video_poll_interval_seconds = 20.0
        self.video_max_polls = 45
        self.tts_max_attempts = 3
        self.tts_retry_backoff_seconds = 2.0

    def healthcheck(self) -> dict:
        return {
            "provider": "google",
            "configured": bool(self.api_key),
            "video_model": self.video_model,
            "image_model": self.image_model,
            "tts_model": self.tts_model,
        }

    def generate_image(
        self,
        *,
        prompt: str,
        negative_prompt: str | None = None,
        sample_count: int = 1,
        aspect_ratio: str | None = None,
        safety_setting: str | None = None,
        person_generation: str | None = None,
    ) -> GoogleGeneratedImage:
        if not self.api_key:
            raise GoogleProviderError(
                "google_provider_not_configured",
                "Google API key is not configured.",
            )
        if not self.image_model:
            raise GoogleProviderError(
                "google_image_model_not_configured",
                "Google image model is not configured.",
            )

        normalized_prompt = str(prompt or "").strip()
        request_payload: dict[str, Any] = {
            "model": self.image_model,
            "prompt": normalized_prompt or str(prompt or ""),
            "n": max(1, int(sample_count or 1)),
        }
        image_size = self._map_image_size(aspect_ratio)
        if image_size:
            request_payload["size"] = image_size

        try:
            with self._build_http_client() as client:
                response_payload = self._request_json(
                    client,
                    "POST",
                    "/v1/images/generations",
                    json=request_payload,
                )
                image_bytes, content_type, response_summary = self._extract_relay_generated_image(
                    client,
                    response_payload,
                )
        except GoogleProviderError:
            raise
        except Exception as exc:
            raise GoogleProviderError(
                "google_image_generation_failed",
                f"Google image generation request failed via relay HTTP API: {exc}",
            ) from exc

        provider_payload = {
            "model": self.image_model,
            "sdk": "google-genai",
            "request": {
                "sample_count": sample_count,
                "aspect_ratio": aspect_ratio,
                "safety_setting": safety_setting,
                "person_generation": person_generation,
                "negative_prompt_present": bool(negative_prompt),
                "negative_prompt_forwarded": False,
            },
            "response": response_summary,
        }
        return GoogleGeneratedImage(
            image_bytes=image_bytes,
            content_type=content_type,
            provider_payload=provider_payload,
        )

    def generate_video(
        self,
        *,
        prompt: str,
        negative_prompt: str | None = None,
        sample_count: int = 1,
        aspect_ratio: str | None = None,
        duration_seconds: int | None = None,
        fps: int | None = None,
        seed: int | None = None,
        resolution: str | None = None,
        person_generation: str | None = None,
        output_gcs_uri: str | None = None,
        enhance_prompt: bool | None = None,
        compression_quality: str | None = None,
        last_frame: Any | None = None,
        mask: Any | None = None,
        reference_images: list[Any] | None = None,
        poll_interval_seconds: float | None = None,
        max_polls: int | None = None,
    ) -> GoogleGeneratedVideo:
        if not self.api_key:
            raise GoogleProviderError(
                "google_provider_not_configured",
                "Google API key is not configured.",
            )
        if not self.video_model:
            raise GoogleProviderError(
                "google_video_model_not_configured",
                "Google video model is not configured.",
            )
        normalized_prompt = str(prompt or "").strip()
        if not normalized_prompt:
            raise GoogleProviderError(
                "google_video_prompt_missing",
                "Google video generation prompt is missing.",
            )

        normalized_poll_interval = (
            self.video_poll_interval_seconds
            if poll_interval_seconds is None
            else float(poll_interval_seconds)
        )
        normalized_max_polls = self.video_max_polls if max_polls is None else int(max_polls)
        reference_image_urls = self._extract_reference_image_urls(reference_images)

        request_payload: dict[str, Any] = {
            "model": self.video_model,
            "prompt": normalized_prompt,
            "sample_count": max(1, int(sample_count or 1)),
        }
        if negative_prompt:
            request_payload["negative_prompt"] = negative_prompt
        if aspect_ratio:
            request_payload["aspect_ratio"] = aspect_ratio
        if duration_seconds is not None:
            request_payload["duration_seconds"] = int(duration_seconds)
        if fps is not None:
            request_payload["fps"] = int(fps)
        if seed is not None:
            request_payload["seed"] = int(seed)
        if resolution:
            request_payload["resolution"] = resolution
        if person_generation:
            request_payload["person_generation"] = person_generation
        if output_gcs_uri:
            request_payload["output_gcs_uri"] = output_gcs_uri
        if enhance_prompt is not None:
            request_payload["enhance_prompt"] = bool(enhance_prompt)
        if compression_quality:
            request_payload["compression_quality"] = compression_quality
        if last_frame is not None:
            request_payload["last_frame"] = last_frame
        if mask is not None:
            request_payload["mask"] = mask
        if reference_image_urls:
            request_payload["images"] = reference_image_urls

        try:
            with self._build_http_client() as client:
                operation = self._request_json(
                    client,
                    "POST",
                    "/v1/video/create",
                    json=request_payload,
                )
                completed_operation = self._poll_video_operation(
                    client,
                    operation,
                    poll_interval_seconds=normalized_poll_interval,
                    max_polls=normalized_max_polls,
                )
                video_bytes, content_type, response_summary = self._extract_generated_video(
                    client,
                    completed_operation,
                )
        except GoogleProviderError:
            raise
        except Exception as exc:
            raise GoogleProviderError(
                "google_video_generation_failed",
                f"Google video generation request failed via relay HTTP API: {exc}",
            ) from exc

        provider_payload = {
            "model": self.video_model,
            "sdk": "google-genai",
            "request": {
                "sample_count": sample_count,
                "aspect_ratio": aspect_ratio,
                "duration_seconds": duration_seconds,
                "fps": fps,
                "seed": seed,
                "resolution": resolution,
                "person_generation": person_generation,
                "output_gcs_uri": output_gcs_uri,
                "enhance_prompt": enhance_prompt,
                "compression_quality": compression_quality,
                "negative_prompt_present": bool(negative_prompt),
                "reference_images_count": len(reference_images or []),
                "poll_interval_seconds": normalized_poll_interval,
                "max_polls": normalized_max_polls,
            },
            "response": response_summary,
        }
        return GoogleGeneratedVideo(
            video_bytes=video_bytes,
            content_type=content_type,
            provider_payload=provider_payload,
        )

    def generate_voice(
        self,
        *,
        text: str,
        voice_name: str | None = None,
        language_code: str | None = None,
        speech_config: Any | None = None,
    ) -> GoogleGeneratedVoice:
        del voice_name, language_code, speech_config

        if not self.api_key:
            raise GoogleProviderError(
                "google_provider_not_configured",
                "Google API key is not configured.",
            )
        if not self.tts_model:
            raise GoogleProviderError(
                "google_tts_model_not_configured",
                "Google TTS model is not configured.",
            )
        normalized_text = str(text or "").strip()
        if not normalized_text:
            raise GoogleProviderError(
                "google_tts_text_missing",
                "Google TTS input text is missing.",
            )

        raise GoogleProviderError(
            "google_tts_generation_failed",
            "Google TTS generation is not supported by the configured relay provider.",
        )

    def _build_http_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.relay_base_url,
            headers=self._build_headers(),
            timeout=self.timeout,
            follow_redirects=True,
        )

    def _build_headers(self) -> dict[str, str]:
        authorization_value = self.api_key.strip()
        if authorization_value and not authorization_value.lower().startswith("bearer "):
            authorization_value = f"Bearer {authorization_value}"
        return {
            "Authorization": authorization_value,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request_json(
        self,
        client: httpx.Client,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        response = client.request(method, path, json=json)
        if response.status_code >= 400:
            raise RuntimeError(
                f"HTTP {response.status_code} calling {path}: {response.text}"
            )
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"Relay returned non-JSON payload for {path}: {exc}") from exc

    def _extract_relay_generated_image(
        self,
        client: httpx.Client,
        response: Any,
    ) -> tuple[bytes, str, dict]:
        legacy_generated_images = self._read_value(response, "generated_images")
        if isinstance(legacy_generated_images, list):
            return self._extract_generated_image(response)

        data = self._read_value(response, "data")
        if not isinstance(data, list) or not data:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google image response does not contain generated_images.",
            )

        first_generated = self._coerce_dict(data[0])
        b64_payload = self._read_value(first_generated, "b64_json")
        if isinstance(b64_payload, str) and b64_payload.strip():
            try:
                image_bytes = base64.b64decode(b64_payload)
            except Exception as exc:
                raise GoogleProviderError(
                    "google_provider_response_invalid",
                    f"Google image response returned invalid base64 image payload: {exc}",
                ) from exc
            if not image_bytes:
                raise GoogleProviderError(
                    "google_provider_response_invalid",
                    "Google image response decoded to empty image bytes.",
                )
            content_type = self._infer_image_content_type(
                self._read_value(first_generated, "url")
            )
        else:
            image_url = self._read_value(first_generated, "url")
            if not image_url:
                raise GoogleProviderError(
                    "google_provider_response_invalid",
                    "Google image response does not contain generated_images.",
                )
            image_bytes, content_type = self._download_binary_url(client, str(image_url))

        response_summary = {
            "generated_images_count": len(data),
            "response_type": type(response).__name__,
        }
        return image_bytes, content_type, response_summary

    def _extract_generated_image(self, response: Any) -> tuple[bytes, str, dict]:
        generated_images = self._read_value(response, "generated_images")
        if not isinstance(generated_images, list) or not generated_images:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google image response does not contain generated_images.",
            )

        first_generated = generated_images[0]
        image_part = self._read_value(first_generated, "image", default=first_generated)
        image_bytes = self._read_value(image_part, "image_bytes")
        content_type = self._read_value(image_part, "mime_type", default="image/png")

        if not image_bytes:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google image response does not contain image bytes.",
            )
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google image response returned non-bytes image payload.",
            )

        image_bytes = bytes(image_bytes)
        if not image_bytes:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google image response decoded to empty image bytes.",
            )

        response_summary = {
            "generated_images_count": len(generated_images),
            "response_type": type(response).__name__,
        }
        return image_bytes, str(content_type or "image/png"), response_summary

    def _poll_video_operation(
        self,
        client: Any,
        operation: Any,
        *,
        poll_interval_seconds: float,
        max_polls: int,
    ) -> Any:
        if operation is None:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google video generation did not return an operation.",
            )

        current_operation = operation
        operation_name = self._read_value(current_operation, "name") or self._read_value(
            current_operation,
            "id",
            default="unknown",
        )
        effective_max_polls = max(0, max_polls)
        effective_poll_interval = max(0.0, float(poll_interval_seconds))

        for poll_index in range(effective_max_polls + 1):
            if self._is_video_operation_done(current_operation):
                error = self._extract_video_operation_error(current_operation)
                if error is not None:
                    error_code = self._read_value(
                        error,
                        "code",
                        default=self._read_value(current_operation, "code", default="unknown"),
                    )
                    error_message = self._read_value(error, "message", default=str(error))
                    raise GoogleProviderError(
                        "google_video_generation_failed",
                        "Google video generation operation failed "
                        f"(operation={operation_name}, code={error_code}): {error_message}",
                    )
                return current_operation

            if poll_index >= effective_max_polls:
                break

            if effective_poll_interval > 0:
                time.sleep(effective_poll_interval)

            try:
                current_operation = self._fetch_video_operation(client, current_operation)
            except Exception as exc:
                raise GoogleProviderError(
                    "google_video_poll_failed",
                    f"Google video generation operation polling failed for {operation_name}: {exc}",
                ) from exc

        raise GoogleProviderError(
            "google_video_generation_timeout",
            "Google video generation did not complete within poll limit "
            f"(operation={operation_name}, max_polls={effective_max_polls}, "
            f"poll_interval_seconds={effective_poll_interval}).",
        )

    def _fetch_video_operation(self, client: Any, operation: Any) -> Any:
        operation_id = self._read_value(operation, "id")
        if operation_id and hasattr(client, "request"):
            path = f"/v1/videos/{quote(str(operation_id), safe='')}"
            return self._request_json(client, "GET", path)

        operations_client = getattr(client, "operations", None)
        if operations_client is not None and hasattr(operations_client, "get"):
            return operations_client.get(operation=operation)

        operation_name = self._read_value(operation, "name")
        if operation_name and hasattr(client, "request"):
            path = f"/v1/videos/{quote(str(operation_name), safe='')}"
            return self._request_json(client, "GET", path)
        raise RuntimeError("video operation id is missing")

    def _extract_generated_video(self, client: Any, operation: Any) -> tuple[bytes, str, dict]:
        result = self._read_value(operation, "result")
        if result is not None:
            generated_videos = self._read_value(result, "generated_videos")
            if isinstance(generated_videos, list) and generated_videos:
                first_generated = generated_videos[0]
                video = self._read_value(first_generated, "video", default=first_generated)
                if video is None:
                    raise GoogleProviderError(
                        "google_provider_response_invalid",
                        "Google video response does not contain a video object.",
                    )

                video_uri = self._read_value(video, "uri")
                if not video_uri:
                    raise GoogleProviderError(
                        "google_provider_response_invalid",
                        "Google video response does not contain a downloadable video uri.",
                    )

                try:
                    client.files.download(file=video)
                except Exception as exc:
                    raise GoogleProviderError(
                        "google_video_download_failed",
                        f"Google video download failed for uri={video_uri}: {exc}",
                    ) from exc

                video_bytes = self._read_value(video, "video_bytes")
                if not isinstance(video_bytes, (bytes, bytearray)):
                    raise GoogleProviderError(
                        "google_provider_response_invalid",
                        "Google video download did not populate video_bytes.",
                    )
                video_bytes = bytes(video_bytes)
                if not video_bytes:
                    raise GoogleProviderError(
                        "google_provider_response_invalid",
                        "Google video download produced empty video bytes.",
                    )

                content_type = self._read_value(video, "mime_type") or self._infer_video_content_type(video_uri)
                response_summary = {
                    "operation_name": self._read_value(operation, "name"),
                    "operation_type": type(operation).__name__,
                    "result_type": type(result).__name__,
                    "generated_videos_count": len(generated_videos),
                    "video_uri": video_uri,
                }
                return video_bytes, str(content_type or "video/mp4"), response_summary

        video_uri = self._resolve_video_download_url(result if result is not None else operation)
        if not video_uri:
            video_uri = self._resolve_video_download_url(operation)
        if not video_uri:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google video response does not contain a downloadable video uri.",
            )

        try:
            video_bytes, downloaded_content_type = self._download_binary_url(client, video_uri)
        except Exception as exc:
            raise GoogleProviderError(
                "google_video_download_failed",
                f"Google video download failed for uri={video_uri}: {exc}",
            ) from exc

        if not isinstance(video_bytes, (bytes, bytearray)):
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google video download did not populate video_bytes.",
            )
        video_bytes = bytes(video_bytes)
        if not video_bytes:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google video download produced empty video bytes.",
            )

        result_payload = self._read_value(operation, "result", default=operation)
        response_summary = {
            "operation_name": self._read_value(operation, "name") or self._read_value(operation, "id"),
            "operation_type": type(operation).__name__,
            "result_type": type(result_payload).__name__,
            "generated_videos_count": self._count_generated_videos(operation),
            "video_uri": video_uri,
        }
        return video_bytes, downloaded_content_type or self._infer_video_content_type(video_uri), response_summary

    def _download_binary_url(self, client: Any, url: str) -> tuple[bytes, str]:
        response = client.get(url)
        status_code = getattr(response, "status_code", 200)
        if status_code >= 400:
            raise RuntimeError(f"HTTP {status_code}: {getattr(response, 'text', '')}")

        content_type = ""
        headers = getattr(response, "headers", None)
        if headers is not None and hasattr(headers, "get"):
            content_type = str(headers.get("content-type") or "")
        if content_type.lower().startswith("application/json"):
            raise RuntimeError(getattr(response, "text", "unexpected JSON download response"))

        content = getattr(response, "content", None)
        if not isinstance(content, (bytes, bytearray)):
            raise RuntimeError("download response did not contain bytes")
        normalized_content = bytes(content)
        return normalized_content, content_type or self._infer_image_content_type(url)

    def _resolve_video_download_url(self, payload: Any) -> str | None:
        direct_candidates = [
            self._read_value(payload, "video_url"),
            self._read_value(payload, "download_url"),
            self._read_value(payload, "url"),
        ]
        for candidate in direct_candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

        nested_mappings = [
            self._read_value(payload, "video"),
            self._read_value(payload, "output"),
            self._read_value(payload, "result"),
            self._read_value(payload, "data"),
            self._read_value(payload, "file"),
            self._read_value(payload, "assets"),
        ]
        for candidate in nested_mappings:
            resolved = self._resolve_video_download_url_from_candidate(candidate)
            if resolved:
                return resolved
        return None

    def _resolve_video_download_url_from_candidate(self, candidate: Any) -> str | None:
        if isinstance(candidate, str) and candidate.strip().startswith(("http://", "https://")):
            return candidate.strip()
        if isinstance(candidate, list):
            for item in candidate:
                resolved = self._resolve_video_download_url_from_candidate(item)
                if resolved:
                    return resolved
            return None
        if isinstance(candidate, dict):
            for key in ("url", "uri", "download_url", "video_url"):
                value = candidate.get(key)
                if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
                    return value.strip()
            for key in ("video", "file", "output", "result", "data", "assets"):
                resolved = self._resolve_video_download_url_from_candidate(candidate.get(key))
                if resolved:
                    return resolved
            return None
        if candidate is not None and hasattr(candidate, "__dict__"):
            return self._resolve_video_download_url_from_candidate(vars(candidate))
        return None

    def _count_generated_videos(self, payload: Any) -> int:
        result = self._read_value(payload, "result")
        generated_videos = self._read_value(result, "generated_videos") if result is not None else None
        if isinstance(generated_videos, list) and generated_videos:
            return len(generated_videos)

        for candidate in (
            self._read_value(payload, "output"),
            self._read_value(payload, "data"),
            self._read_value(payload, "assets"),
        ):
            if isinstance(candidate, list) and candidate:
                return len(candidate)
        return 1

    def _is_video_operation_done(self, operation: Any) -> bool:
        if bool(self._read_value(operation, "done", default=False)):
            return True
        status = str(self._read_value(operation, "status") or "").strip().lower()
        return status in {"succeeded", "completed", "success", "done", "ready", "failed", "error", "cancelled", "canceled", "rejected", "expired"}

    def _extract_video_operation_error(self, operation: Any) -> Any | None:
        error = self._read_value(operation, "error")
        if error is not None:
            return error

        status = str(self._read_value(operation, "status") or "").strip().lower()
        if status not in {"failed", "error", "cancelled", "canceled", "rejected", "expired"}:
            return None

        message = (
            self._read_value(operation, "message")
            or self._read_value(operation, "detail")
            or self._read_value(operation, "last_error")
            or status
        )
        return {
            "code": self._read_value(operation, "code", default="unknown"),
            "message": self._read_value(message, "message", default=str(message)),
        }

    def _extract_reference_image_urls(self, reference_images: list[Any] | None) -> list[str]:
        urls: list[str] = []
        for reference_image in reference_images or []:
            if isinstance(reference_image, str) and reference_image.strip():
                urls.append(reference_image.strip())
                continue
            if isinstance(reference_image, dict):
                for key in ("url", "uri", "image_url", "source_url"):
                    value = reference_image.get(key)
                    if isinstance(value, str) and value.strip():
                        urls.append(value.strip())
                        break
                continue
            if reference_image is not None:
                for key in ("url", "uri", "image_url", "source_url"):
                    value = getattr(reference_image, key, None)
                    if isinstance(value, str) and value.strip():
                        urls.append(value.strip())
                        break
        return urls

    def _map_image_size(self, aspect_ratio: str | None) -> str | None:
        normalized = str(aspect_ratio or "").strip()
        if normalized == "1:1":
            return "1024x1024"
        if normalized == "16:9":
            return "1536x864"
        if normalized == "9:16":
            return "864x1536"
        if normalized == "4:3":
            return "1152x864"
        if normalized == "3:4":
            return "864x1152"
        return None

    def _build_speech_config(
        self,
        *,
        voice_name: str | None,
        language_code: str | None,
        speech_config: Any | None,
    ) -> Any | None:
        normalized_voice_name = str(voice_name).strip() if voice_name is not None else None
        if normalized_voice_name == "":
            normalized_voice_name = None
        normalized_language_code = (
            str(language_code).strip() if language_code is not None else None
        )
        if normalized_language_code == "":
            normalized_language_code = None

        if isinstance(speech_config, str):
            normalized = speech_config.strip()
            if not normalized:
                raise GoogleProviderError(
                    "google_tts_config_invalid",
                    "Google TTS speech_config string cannot be empty.",
                )
            return normalized

        if speech_config is None:
            if normalized_voice_name is None and normalized_language_code is None:
                return None
            config_kwargs: dict[str, Any] = {}
            if normalized_language_code is not None:
                config_kwargs["language_code"] = normalized_language_code
            if normalized_voice_name is not None:
                config_kwargs["voice_config"] = types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=normalized_voice_name,
                    )
                )
            return types.SpeechConfig(**config_kwargs)

        if isinstance(speech_config, types.SpeechConfig):
            config_kwargs = speech_config.model_dump(exclude_none=True)
            if normalized_language_code is not None and not config_kwargs.get("language_code"):
                config_kwargs["language_code"] = normalized_language_code
            if (
                normalized_voice_name is not None
                and not config_kwargs.get("voice_config")
                and not config_kwargs.get("multi_speaker_voice_config")
            ):
                config_kwargs["voice_config"] = {
                    "prebuilt_voice_config": {
                        "voice_name": normalized_voice_name,
                    }
                }
            return types.SpeechConfig(**config_kwargs)

        if isinstance(speech_config, types.VoiceConfig):
            config_kwargs = {
                "voice_config": speech_config,
            }
            if normalized_language_code is not None:
                config_kwargs["language_code"] = normalized_language_code
            return types.SpeechConfig(**config_kwargs)

        if isinstance(speech_config, dict):
            config_kwargs = dict(speech_config)
            if normalized_language_code is not None and not config_kwargs.get("language_code"):
                config_kwargs["language_code"] = normalized_language_code
            if (
                normalized_voice_name is not None
                and not config_kwargs.get("voice_config")
                and not config_kwargs.get("multi_speaker_voice_config")
            ):
                config_kwargs["voice_config"] = {
                    "prebuilt_voice_config": {
                        "voice_name": normalized_voice_name,
                    }
                }
            try:
                return types.SpeechConfig(**config_kwargs)
            except Exception as exc:
                raise GoogleProviderError(
                    "google_tts_config_invalid",
                    f"Google TTS speech_config is invalid: {exc}",
                ) from exc

        raise GoogleProviderError(
            "google_tts_config_invalid",
            "Google TTS speech_config must be None, str, dict, SpeechConfig, or VoiceConfig.",
        )

    def _extract_generated_voice(self, response: Any) -> tuple[bytes, str, dict]:
        candidates = self._read_value(response, "candidates")
        if not isinstance(candidates, list) or not candidates:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google TTS response does not contain candidates.",
            )

        for candidate_index, candidate in enumerate(candidates):
            content = self._read_value(candidate, "content")
            parts = self._read_value(content, "parts")
            if not isinstance(parts, list) or not parts:
                continue

            for part_index, part in enumerate(parts):
                inline_data = self._read_value(part, "inline_data")
                if inline_data is None:
                    continue

                audio_bytes = self._read_value(inline_data, "data")
                if audio_bytes is None:
                    continue
                if not isinstance(audio_bytes, (bytes, bytearray)):
                    raise GoogleProviderError(
                        "google_provider_response_invalid",
                        "Google TTS inline audio payload is not bytes.",
                    )

                audio_bytes = bytes(audio_bytes)
                if not audio_bytes:
                    continue

                content_type = self._read_value(inline_data, "mime_type") or "audio/wav"
                response_summary = {
                    "response_type": type(response).__name__,
                    "candidates_count": len(candidates),
                    "candidate_index": candidate_index,
                    "part_index": part_index,
                }
                return audio_bytes, str(content_type), response_summary

        raise GoogleProviderError(
            "google_provider_response_invalid",
            "Google TTS response does not contain inline audio data.",
        )

    @staticmethod
    def _infer_image_content_type(image_uri: str | None) -> str:
        normalized_uri = str(image_uri or "").lower()
        if normalized_uri.endswith(".jpg") or normalized_uri.endswith(".jpeg"):
            return "image/jpeg"
        if normalized_uri.endswith(".webp"):
            return "image/webp"
        return "image/png"

    @staticmethod
    def _infer_video_content_type(video_uri: str | None) -> str:
        normalized_uri = str(video_uri or "").lower()
        if normalized_uri.endswith(".mov"):
            return "video/quicktime"
        if normalized_uri.endswith(".webm"):
            return "video/webm"
        return "video/mp4"

    @staticmethod
    def _coerce_dict(payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if payload is None:
            return {}
        if hasattr(payload, "__dict__"):
            return vars(payload)
        return {}

    @staticmethod
    def _read_value(payload: Any, key: str, default: Any = None) -> Any:
        if isinstance(payload, dict):
            return payload.get(key, default)
        return getattr(payload, key, default)
