from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.db.models import CompiledRuntime, Job
from app.db.session import SessionLocal
from app.providers.google.client import GoogleProviderClient, GoogleProviderError


class ProviderExecutorError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ProviderExecutionResult:
    status: str = "succeeded_stub"
    provider: str = "stub"
    output_filename: str | None = None
    provider_payload: dict | None = None
    binary_payload: bytes | None = None
    text_payload: str | None = None
    content_type: str | None = None

    def to_dict(self) -> dict:
        payload = {
            "status": self.status,
            "provider": self.provider,
            "output_filename": self.output_filename,
            "provider_payload": self.provider_payload or {},
        }
        if self.binary_payload is not None:
            payload["binary_payload"] = self.binary_payload
        if self.text_payload is not None:
            payload["text_payload"] = self.text_payload
        if self.content_type is not None:
            payload["content_type"] = self.content_type
        return payload


class BaseProviderExecutor:
    provider_name = "stub"

    def execute(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
        task_name: str,
        asset_plan: dict | None = None,
    ) -> dict:
        output_filename = asset_plan.get("filename") if asset_plan else None
        content_type = asset_plan.get("content_type") if asset_plan else "text/plain; charset=utf-8"
        text_payload = None
        if asset_plan:
            text_payload = (
                f"stub materialized artifact\n"
                f"project_id={project_id}\n"
                f"runtime_version={runtime_version}\n"
                f"job_id={job.id}\n"
                f"job_type={job.job_type}\n"
                f"task_name={task_name}\n"
                f"provider_name={self.provider_name}\n"
            )

        return ProviderExecutionResult(
            status="succeeded_stub",
            provider=self.provider_name,
            output_filename=output_filename,
            provider_payload={
                "job_type": job.job_type,
                "task_name": task_name,
                "runtime_version": runtime_version,
                "provider_name": self.provider_name,
            },
            text_payload=text_payload,
            content_type=content_type,
        ).to_dict()

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _coerce_dict(value: Any) -> dict:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _coerce_list(value: Any) -> list:
        return value if isinstance(value, list) else []

    @classmethod
    def _coerce_positive_int(cls, value: Any, *, default: int | None = None) -> int | None:
        if value is None:
            return default
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return default
        if normalized < 1:
            return default
        return normalized

    @classmethod
    def _coerce_bool(cls, value: Any, *, default: bool | None = None) -> bool | None:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return default

    @classmethod
    def _duration_ms_to_seconds(cls, value: Any) -> int | None:
        duration_ms = cls._coerce_positive_int(value)
        if duration_ms is None:
            return None
        return max(1, round(duration_ms / 1000))

    @classmethod
    def _join_text_blocks(cls, *parts: Any) -> str | None:
        normalized_parts: list[str] = []
        for part in parts:
            normalized = cls._normalize_optional_text(part)
            if normalized:
                normalized_parts.append(normalized)
        if not normalized_parts:
            return None
        return "\n\n".join(normalized_parts)

    @classmethod
    def _format_mapping(cls, value: Any) -> str | None:
        if isinstance(value, dict):
            formatted_items: list[str] = []
            for key, item in value.items():
                item_text = cls._normalize_optional_text(item)
                if item_text:
                    formatted_items.append(f"{key}={item_text}")
            return ", ".join(formatted_items) or None
        if isinstance(value, list):
            formatted_items = [cls._normalize_optional_text(item) for item in value]
            return ", ".join(item for item in formatted_items if item) or None
        return cls._normalize_optional_text(value)


class RuntimeBackedExecutor(BaseProviderExecutor):
    def _load_runtime_payload(self, *, project_id: str, runtime_version: str) -> tuple[CompiledRuntime, dict]:
        db = SessionLocal()
        try:
            runtime = (
                db.query(CompiledRuntime)
                .filter(
                    CompiledRuntime.project_id == UUID(project_id),
                    CompiledRuntime.runtime_version == runtime_version,
                )
                .order_by(CompiledRuntime.created_at.desc())
                .first()
            )
        finally:
            db.close()

        if not runtime:
            raise ProviderExecutorError(
                "runtime_not_found",
                f"Compiled runtime not found for project_id={project_id}, runtime_version={runtime_version}.",
            )

        runtime_payload = runtime.runtime_payload or {}
        if not isinstance(runtime_payload, dict) or not runtime_payload:
            raise ProviderExecutorError(
                "runtime_payload_missing",
                f"Compiled runtime payload is empty for project_id={project_id}, runtime_version={runtime_version}.",
            )
        return runtime, runtime_payload

    def _resolve_runtime_context(self, *, project_id: str, runtime_version: str) -> tuple[CompiledRuntime, dict, dict, list]:
        runtime, runtime_payload = self._load_runtime_payload(
            project_id=project_id,
            runtime_version=runtime_version,
        )
        compile_options = self._coerce_dict(runtime_payload.get("compile_options"))
        sequences = self._coerce_list(runtime_payload.get("sequences"))
        return runtime, runtime_payload, compile_options, sequences


class CompileRuntimeExecutor(RuntimeBackedExecutor):
    provider_name = "runtime_payload"

    def execute(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
        task_name: str,
        asset_plan: dict | None = None,
    ) -> dict:
        runtime, runtime_payload, compile_options, sequences = self._resolve_runtime_context(
            project_id=project_id,
            runtime_version=runtime_version,
        )
        sequence_count = len(sequences)
        spu_count = sum(
            len(self._coerce_list(self._coerce_dict(sequence).get("spus")))
            for sequence in sequences
        )
        vbu_count = sum(
            len(self._coerce_list(self._coerce_dict(sequence).get("vbus")))
            for sequence in sequences
        )
        text_payload = "\n".join(
            [
                "compile runtime execution materialized from persisted runtime payload",
                f"project_id={project_id}",
                f"runtime_version={runtime_version}",
                f"job_id={job.id}",
                f"runtime_id={runtime.id}",
                f"sequence_count={sequence_count}",
                f"spu_count={spu_count}",
                f"vbu_count={vbu_count}",
            ]
        )
        return ProviderExecutionResult(
            status="succeeded",
            provider=self.provider_name,
            output_filename=asset_plan.get("filename") if asset_plan else None,
            provider_payload={
                "job_type": job.job_type,
                "task_name": task_name,
                "runtime_version": runtime_version,
                "provider_name": self.provider_name,
                "runtime_id": str(runtime.id),
                "runtime_compile_status": getattr(runtime, "compile_status", None),
                "runtime_dispatch_status": getattr(runtime, "dispatch_status", None),
                "payload_project_id": runtime_payload.get("project_id"),
                "compile_options_keys": sorted(compile_options.keys()),
                "sequence_count": sequence_count,
                "spu_count": spu_count,
                "vbu_count": vbu_count,
            },
            text_payload=text_payload,
            content_type="text/plain; charset=utf-8",
        ).to_dict()


class StubProviderExecutor(BaseProviderExecutor):
    provider_name = "stub"


class GoogleExecutorMixin(RuntimeBackedExecutor):
    provider_name = "google"

    @staticmethod
    def _build_google_client() -> GoogleProviderClient:
        return GoogleProviderClient(
            api_key=settings.google_api_key,
            video_model=settings.google_video_model,
            image_model=settings.google_image_model,
            tts_model=settings.google_tts_model,
        )


class GoogleImagenExecutor(GoogleExecutorMixin):
    def execute(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
        task_name: str,
        asset_plan: dict | None = None,
    ) -> dict:
        output_filename = asset_plan.get("filename") if asset_plan else None
        prompt, negative_prompt, generation_options = self._resolve_prompt_inputs(job)
        client = self._build_google_client()

        try:
            generated = client.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                sample_count=generation_options.get("sample_count", 1),
                aspect_ratio=generation_options.get("aspect_ratio"),
                safety_setting=generation_options.get("safety_setting"),
                person_generation=generation_options.get("person_generation"),
            )
        except GoogleProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise GoogleProviderError(
                "google_image_generation_failed",
                f"Unexpected Google image generation error: {exc}",
            ) from exc

        return ProviderExecutionResult(
            status="succeeded",
            provider=self.provider_name,
            output_filename=output_filename,
            provider_payload={
                "job_type": job.job_type,
                "task_name": task_name,
                "runtime_version": runtime_version,
                "provider_name": self.provider_name,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "generation_options": generation_options,
                "google": generated.provider_payload,
            },
            binary_payload=generated.image_bytes,
            content_type=generated.content_type,
        ).to_dict()

    def _resolve_prompt_inputs(self, job: Job) -> tuple[str, str | None, dict]:
        payload = job.payload or {}
        provider_inputs = self._coerce_dict(payload.get("provider_inputs"))
        prompt = provider_inputs.get("prompt") or payload.get("prompt")
        if not prompt or not str(prompt).strip():
            raise GoogleProviderError(
                "google_image_prompt_missing",
                f"render_image job {job.id} is missing provider_inputs.prompt / prompt",
            )

        negative_prompt = provider_inputs.get("negative_prompt") or payload.get("negative_prompt")
        generation_options = {
            "sample_count": provider_inputs.get("sample_count") or 1,
            "aspect_ratio": provider_inputs.get("aspect_ratio"),
            "safety_setting": provider_inputs.get("safety_setting"),
            "person_generation": provider_inputs.get("person_generation"),
        }
        return str(prompt).strip(), self._normalize_optional_text(negative_prompt), generation_options


class GoogleVideoExecutor(GoogleExecutorMixin):
    def execute(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
        task_name: str,
        asset_plan: dict | None = None,
    ) -> dict:
        output_filename = asset_plan.get("filename") if asset_plan else None
        prompt, negative_prompt, generation_options, selection_payload = self._resolve_video_inputs(
            job=job,
            project_id=project_id,
            runtime_version=runtime_version,
        )
        client = self._build_google_client()

        try:
            generated = client.generate_video(
                prompt=prompt,
                negative_prompt=negative_prompt,
                sample_count=generation_options.get("sample_count", 1),
                aspect_ratio=generation_options.get("aspect_ratio"),
                duration_seconds=generation_options.get("duration_seconds"),
                fps=generation_options.get("fps"),
                seed=generation_options.get("seed"),
                resolution=generation_options.get("resolution"),
                person_generation=generation_options.get("person_generation"),
                output_gcs_uri=generation_options.get("output_gcs_uri"),
                enhance_prompt=generation_options.get("enhance_prompt"),
                compression_quality=generation_options.get("compression_quality"),
                last_frame=generation_options.get("last_frame"),
                mask=generation_options.get("mask"),
                reference_images=generation_options.get("reference_images"),
                poll_interval_seconds=generation_options.get("poll_interval_seconds"),
                max_polls=generation_options.get("max_polls"),
            )
        except GoogleProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise GoogleProviderError(
                "google_video_generation_failed",
                f"Unexpected Google video generation error: {exc}",
            ) from exc

        return ProviderExecutionResult(
            status="succeeded",
            provider=self.provider_name,
            output_filename=output_filename,
            provider_payload={
                "job_type": job.job_type,
                "task_name": task_name,
                "runtime_version": runtime_version,
                "provider_name": self.provider_name,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "generation_options": generation_options,
                "selection": selection_payload,
                "google": generated.provider_payload,
            },
            binary_payload=generated.video_bytes,
            content_type=generated.content_type,
        ).to_dict()

    def _resolve_video_inputs(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
    ) -> tuple[str, str | None, dict, dict]:
        payload = job.payload or {}
        provider_inputs = self._coerce_dict(payload.get("provider_inputs"))
        _, runtime_payload, compile_options, sequences = self._resolve_runtime_context(
            project_id=project_id,
            runtime_version=runtime_version,
        )
        primary_sequence, primary_spu = self._select_primary_spu(sequences)

        prompt = (
            self._normalize_optional_text(provider_inputs.get("prompt"))
            or self._normalize_optional_text(payload.get("prompt"))
            or self._build_video_prompt(
                runtime_payload=runtime_payload,
                compile_options=compile_options,
                sequence=primary_sequence,
                spu=primary_spu,
            )
        )
        if not prompt:
            raise GoogleProviderError(
                "google_video_prompt_missing",
                f"render_video job {job.id} could not derive a prompt from runtime payload",
            )

        negative_prompt = self._build_video_negative_prompt(
            provider_inputs=provider_inputs,
            payload=payload,
            compile_options=compile_options,
            spu=primary_spu,
        )

        visual_constraints = self._coerce_dict(primary_spu.get("visual_constraints"))
        generation_options = {
            "sample_count": self._coerce_positive_int(provider_inputs.get("sample_count"), default=1) or 1,
            "aspect_ratio": (
                self._normalize_optional_text(provider_inputs.get("aspect_ratio"))
                or self._normalize_optional_text(payload.get("aspect_ratio"))
                or self._normalize_optional_text(compile_options.get("aspect_ratio"))
            ),
            "duration_seconds": (
                self._coerce_positive_int(provider_inputs.get("duration_seconds"))
                or self._duration_ms_to_seconds(primary_spu.get("duration_ms"))
            ),
            "fps": self._coerce_positive_int(provider_inputs.get("fps")),
            "seed": self._coerce_positive_int(provider_inputs.get("seed")),
            "resolution": (
                self._normalize_optional_text(provider_inputs.get("resolution"))
                or self._normalize_optional_text(visual_constraints.get("resolution"))
            ),
            "person_generation": (
                self._normalize_optional_text(provider_inputs.get("person_generation"))
                or self._normalize_optional_text(visual_constraints.get("person_generation"))
            ),
            "output_gcs_uri": self._normalize_optional_text(provider_inputs.get("output_gcs_uri")),
            "enhance_prompt": self._coerce_bool(provider_inputs.get("enhance_prompt")),
            "compression_quality": self._normalize_optional_text(provider_inputs.get("compression_quality")),
            "last_frame": provider_inputs.get("last_frame"),
            "mask": provider_inputs.get("mask"),
            "reference_images": provider_inputs.get("reference_images"),
            "poll_interval_seconds": provider_inputs.get("poll_interval_seconds"),
            "max_polls": self._coerce_positive_int(provider_inputs.get("max_polls")),
        }
        selection_payload = {
            "sequence_id": primary_sequence.get("sequence_id"),
            "sequence_code": primary_sequence.get("sequence_code"),
            "sequence_index": primary_sequence.get("sequence_index"),
            "spu_id": primary_spu.get("spu_id"),
            "spu_code": primary_spu.get("spu_code"),
            "display_name": primary_spu.get("display_name"),
            "prompt_source": "job_payload" if provider_inputs.get("prompt") or payload.get("prompt") else "runtime_spu",
        }
        return prompt, negative_prompt, generation_options, selection_payload

    def _select_primary_spu(self, sequences: list) -> tuple[dict, dict]:
        for sequence in sequences:
            sequence_dict = self._coerce_dict(sequence)
            for spu in self._coerce_list(sequence_dict.get("spus")):
                spu_dict = self._coerce_dict(spu)
                if self._normalize_optional_text(spu_dict.get("prompt_text")):
                    return sequence_dict, spu_dict
        raise ProviderExecutorError(
            "runtime_spu_missing",
            "Compiled runtime does not contain any SPU with prompt_text for render_video.",
        )

    def _build_video_prompt(
        self,
        *,
        runtime_payload: dict,
        compile_options: dict,
        sequence: dict,
        spu: dict,
    ) -> str | None:
        base_prompt = self._normalize_optional_text(spu.get("prompt_text"))
        if not base_prompt:
            return None

        style_tags = self._format_mapping(compile_options.get("style_tags"))
        reference = self._coerce_dict(compile_options.get("reference"))
        reference_summary = self._join_text_blocks(
            self._normalize_optional_text(reference.get("structural_goal")),
            self._format_mapping(reference.get("retained_axes")),
            self._format_mapping(reference.get("reference_beats")),
            self._normalize_optional_text(reference.get("notes")),
        )
        prompt_context = self._join_text_blocks(
            f"Project ID: {runtime_payload.get('project_id')}" if runtime_payload.get("project_id") else None,
            f"Sequence type: {sequence.get('sequence_type')}" if sequence.get("sequence_type") else None,
            f"Persuasive goal: {sequence.get('persuasive_goal')}" if sequence.get("persuasive_goal") else None,
            f"SPU display name: {spu.get('display_name')}" if spu.get("display_name") else None,
            f"Style tags: {style_tags}" if style_tags else None,
            f"Visual constraints: {self._format_mapping(spu.get('visual_constraints'))}" if spu.get("visual_constraints") else None,
            f"Reference mapping: {self._format_mapping(spu.get('reference_mapping'))}" if spu.get("reference_mapping") else None,
            f"Reference guidance: {reference_summary}" if reference_summary else None,
        )
        return self._join_text_blocks(base_prompt, prompt_context)

    def _build_video_negative_prompt(
        self,
        *,
        provider_inputs: dict,
        payload: dict,
        compile_options: dict,
        spu: dict,
    ) -> str | None:
        explicit_negative_prompt = (
            self._normalize_optional_text(provider_inputs.get("negative_prompt"))
            or self._normalize_optional_text(payload.get("negative_prompt"))
            or self._normalize_optional_text(spu.get("negative_prompt_text"))
        )
        banned_elements = self._format_mapping(compile_options.get("banned_elements"))
        if not banned_elements:
            return explicit_negative_prompt
        return self._join_text_blocks(
            explicit_negative_prompt,
            f"Avoid these elements: {banned_elements}",
        )


class GoogleVoiceExecutor(GoogleExecutorMixin):
    def execute(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
        task_name: str,
        asset_plan: dict | None = None,
    ) -> dict:
        output_filename = asset_plan.get("filename") if asset_plan else None
        text, voice_name, language_code, speech_config, selection_payload = self._resolve_voice_inputs(
            job=job,
            project_id=project_id,
            runtime_version=runtime_version,
        )
        client = self._build_google_client()

        try:
            generated = client.generate_voice(
                text=text,
                voice_name=voice_name,
                language_code=language_code,
                speech_config=speech_config,
            )
        except GoogleProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise GoogleProviderError(
                "google_tts_generation_failed",
                f"Unexpected Google TTS generation error: {exc}",
            ) from exc

        return ProviderExecutionResult(
            status="succeeded",
            provider=self.provider_name,
            output_filename=output_filename,
            provider_payload={
                "job_type": job.job_type,
                "task_name": task_name,
                "runtime_version": runtime_version,
                "provider_name": self.provider_name,
                "voice_name": voice_name,
                "language_code": language_code,
                "selection": selection_payload,
                "google": generated.provider_payload,
            },
            binary_payload=generated.audio_bytes,
            content_type=generated.content_type,
        ).to_dict()

    def _resolve_voice_inputs(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
    ) -> tuple[str, str | None, str | None, Any | None, dict]:
        payload = job.payload or {}
        provider_inputs = self._coerce_dict(payload.get("provider_inputs"))
        _, _, _, sequences = self._resolve_runtime_context(
            project_id=project_id,
            runtime_version=runtime_version,
        )
        primary_sequence, primary_vbu = self._select_primary_vbu(sequences)
        tts_params = self._coerce_dict(primary_vbu.get("tts_params"))

        text = (
            self._normalize_optional_text(provider_inputs.get("text"))
            or self._normalize_optional_text(payload.get("text"))
            or self._normalize_optional_text(primary_vbu.get("script_text"))
        )
        if not text:
            raise GoogleProviderError(
                "google_tts_text_missing",
                f"render_voice job {job.id} could not derive script text from runtime payload",
            )

        voice_name = (
            self._normalize_optional_text(provider_inputs.get("voice_name"))
            or self._normalize_optional_text(payload.get("voice_name"))
            or self._normalize_optional_text(tts_params.get("voice_name"))
            or self._resolve_voice_profile_name(primary_vbu.get("voice_profile"))
        )
        language_code = (
            self._normalize_optional_text(provider_inputs.get("language_code"))
            or self._normalize_optional_text(payload.get("language_code"))
            or self._normalize_optional_text(tts_params.get("language_code"))
            or self._normalize_optional_text(primary_vbu.get("language"))
            or settings.default_target_language
        )
        speech_config = provider_inputs.get("speech_config")
        if speech_config is None:
            speech_config = payload.get("speech_config")
        if speech_config is None:
            speech_config = tts_params.get("speech_config")

        selection_payload = {
            "sequence_id": primary_sequence.get("sequence_id"),
            "sequence_code": primary_sequence.get("sequence_code"),
            "sequence_index": primary_sequence.get("sequence_index"),
            "vbu_id": primary_vbu.get("vbu_id"),
            "vbu_code": primary_vbu.get("vbu_code"),
            "persuasive_role": primary_vbu.get("persuasive_role"),
            "text_source": "job_payload" if provider_inputs.get("text") or payload.get("text") else "runtime_vbu",
        }
        return text, voice_name, language_code, speech_config, selection_payload

    def _select_primary_vbu(self, sequences: list) -> tuple[dict, dict]:
        for sequence in sequences:
            sequence_dict = self._coerce_dict(sequence)
            for vbu in self._coerce_list(sequence_dict.get("vbus")):
                vbu_dict = self._coerce_dict(vbu)
                if self._normalize_optional_text(vbu_dict.get("script_text")):
                    return sequence_dict, vbu_dict
        raise ProviderExecutorError(
            "runtime_vbu_missing",
            "Compiled runtime does not contain any VBU with script_text for render_voice.",
        )

    def _resolve_voice_profile_name(self, voice_profile: Any) -> str | None:
        if isinstance(voice_profile, dict):
            return (
                self._normalize_optional_text(voice_profile.get("voice_name"))
                or self._normalize_optional_text(voice_profile.get("name"))
            )
        return self._normalize_optional_text(voice_profile)


class FailHardMergeExecutor(RuntimeBackedExecutor):
    provider_name = "merge_fail_hard"

    def execute(
        self,
        *,
        job: Job,
        project_id: str,
        runtime_version: str,
        task_name: str,
        asset_plan: dict | None = None,
    ) -> dict:
        self._load_runtime_payload(project_id=project_id, runtime_version=runtime_version)
        raise ProviderExecutorError(
            "merge_execution_not_ready",
            "merge.runtime real execution chain is not implemented yet: object-read + mux pipeline is required, stub success is disabled.",
        )


class ProviderExecutorRegistry:
    _default_executor = StubProviderExecutor()
    _compile_runtime_executor = CompileRuntimeExecutor()
    _google_imagen_executor = GoogleImagenExecutor()
    _google_video_executor = GoogleVideoExecutor()
    _google_voice_executor = GoogleVoiceExecutor()
    _merge_fail_hard_executor = FailHardMergeExecutor()
    _job_type_executor_map: dict[str, BaseProviderExecutor] = {
        "compile": _compile_runtime_executor,
        "render_image": _google_imagen_executor,
        "render_video": _google_video_executor,
        "render_voice": _google_voice_executor,
        "merge": _merge_fail_hard_executor,
    }

    @classmethod
    def resolve(cls, job_type: str) -> BaseProviderExecutor:
        return cls._job_type_executor_map.get(job_type, cls._default_executor)
