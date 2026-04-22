from dataclasses import dataclass
import time
from typing import Any

from google import genai
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

        client = genai.Client(api_key=self.api_key)
        config_kwargs: dict[str, Any] = {
            "numberOfImages": sample_count,
        }
        if aspect_ratio:
            config_kwargs["aspectRatio"] = aspect_ratio
        if safety_setting:
            config_kwargs["safetyFilterLevel"] = safety_setting
        if person_generation:
            config_kwargs["personGeneration"] = person_generation

        try:
            response = client.models.generate_images(
                model=self.image_model,
                prompt=prompt,
                config=types.GenerateImagesConfig(**config_kwargs),
            )
        except Exception as exc:
            raise GoogleProviderError(
                "google_image_generation_failed",
                f"Google image generation request failed via google-genai SDK: {exc}",
            ) from exc

        image_bytes, content_type, response_summary = self._extract_generated_image(response)
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

        client = genai.Client(api_key=self.api_key)
        config_kwargs: dict[str, Any] = {
            "number_of_videos": sample_count,
        }
        if negative_prompt:
            config_kwargs["negative_prompt"] = negative_prompt
        if aspect_ratio:
            config_kwargs["aspect_ratio"] = aspect_ratio
        if duration_seconds is not None:
            config_kwargs["duration_seconds"] = duration_seconds
        if fps is not None:
            config_kwargs["fps"] = fps
        if seed is not None:
            config_kwargs["seed"] = seed
        if resolution:
            config_kwargs["resolution"] = resolution
        if person_generation:
            config_kwargs["person_generation"] = person_generation
        if output_gcs_uri:
            config_kwargs["output_gcs_uri"] = output_gcs_uri
        if enhance_prompt is not None:
            config_kwargs["enhance_prompt"] = enhance_prompt
        if compression_quality:
            config_kwargs["compression_quality"] = compression_quality
        if last_frame is not None:
            config_kwargs["last_frame"] = last_frame
        if mask is not None:
            config_kwargs["mask"] = mask
        if reference_images:
            config_kwargs["reference_images"] = reference_images

        normalized_poll_interval = (
            self.video_poll_interval_seconds
            if poll_interval_seconds is None
            else float(poll_interval_seconds)
        )
        normalized_max_polls = self.video_max_polls if max_polls is None else int(max_polls)

        try:
            operation = client.models.generate_videos(
                model=self.video_model,
                prompt=normalized_prompt,
                config=types.GenerateVideosConfig(**config_kwargs),
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
                f"Google video generation request failed via google-genai SDK: {exc}",
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

        client = genai.Client(api_key=self.api_key)
        normalized_speech_config = self._build_speech_config(
            voice_name=voice_name,
            language_code=language_code,
            speech_config=speech_config,
        )

        config_kwargs: dict[str, Any] = {
            "response_modalities": ["audio"],
        }
        if normalized_speech_config is not None:
            config_kwargs["speech_config"] = normalized_speech_config

        response_summary = None
        attempt_used = 0
        last_retryable_error: GoogleProviderError | None = None
        for attempt in range(1, self.tts_max_attempts + 1):
            attempt_used = attempt
            try:
                response = client.models.generate_content(
                    model=self.tts_model,
                    contents=normalized_text,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
                audio_bytes, content_type, response_summary = self._extract_generated_voice(response)
                break
            except GoogleProviderError as exc:
                if exc.code != "google_provider_response_invalid" or attempt >= self.tts_max_attempts:
                    raise
                last_retryable_error = exc
                time.sleep(self.tts_retry_backoff_seconds * attempt)
            except Exception as exc:
                raise GoogleProviderError(
                    "google_tts_generation_failed",
                    f"Google TTS generation request failed via google-genai SDK: {exc}",
                ) from exc
        else:  # pragma: no cover - defensive guard
            raise last_retryable_error or GoogleProviderError(
                "google_provider_response_invalid",
                "Google TTS response did not yield usable audio after retries.",
            )

        provider_payload = {
            "model": self.tts_model,
            "sdk": "google-genai",
            "request": {
                "voice_name": voice_name,
                "language_code": language_code,
                "speech_config_present": normalized_speech_config is not None,
                "speech_config_type": type(normalized_speech_config).__name__
                if normalized_speech_config is not None
                else None,
                "text_length": len(normalized_text),
                "attempt_count": attempt_used,
            },
            "response": response_summary,
        }
        return GoogleGeneratedVoice(
            audio_bytes=audio_bytes,
            content_type=content_type,
            provider_payload=provider_payload,
        )

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
        client: genai.Client,
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
        operation_name = self._read_value(current_operation, "name", default="unknown")
        effective_max_polls = max(0, max_polls)
        effective_poll_interval = max(0.0, float(poll_interval_seconds))

        for poll_index in range(effective_max_polls + 1):
            if self._read_value(current_operation, "done", default=False):
                error = self._read_value(current_operation, "error")
                if error is not None:
                    error_code = self._read_value(error, "code", default="unknown")
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
                current_operation = client.operations.get(operation=current_operation)
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

    def _extract_generated_video(self, client: genai.Client, operation: Any) -> tuple[bytes, str, dict]:
        result = self._read_value(operation, "result")
        if result is None:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google video operation completed without a result payload.",
            )

        generated_videos = self._read_value(result, "generated_videos")
        if not isinstance(generated_videos, list) or not generated_videos:
            raise GoogleProviderError(
                "google_provider_response_invalid",
                "Google video response does not contain generated_videos.",
            )

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
    def _infer_video_content_type(video_uri: str | None) -> str:
        normalized_uri = str(video_uri or "").lower()
        if normalized_uri.endswith(".mov"):
            return "video/quicktime"
        if normalized_uri.endswith(".webm"):
            return "video/webm"
        return "video/mp4"

    @staticmethod
    def _read_value(payload: Any, key: str, default: Any = None) -> Any:
        if isinstance(payload, dict):
            return payload.get(key, default)
        return getattr(payload, key, default)
