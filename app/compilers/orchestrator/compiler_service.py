from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Bridge, CompiledRuntime, Job, Project, Sequence, SPU, VBU
from app.schemas.compile import CompileRequest, RuntimePacket, RuntimeSequencePacket
from app.services.compile_validator_service import CompileValidatorService
from app.services.job_dispatch_service import JobDispatchService
from app.services.runtime_version_service import RuntimeVersionService


class CompilerService:
    def __init__(self, db: Session):
        self.db = db
        self.validator = CompileValidatorService(db)
        self.version_service = RuntimeVersionService(db)
        self.dispatch_service = JobDispatchService()

    def compile_project(self, request: CompileRequest) -> CompiledRuntime:
        project = self.db.get(Project, request.project_id)
        if not project:
            raise ValueError("project_not_found")

        validation_result = self.validator.validate_project(request.project_id)
        if not validation_result["is_valid"]:
            raise ValueError("project_invalid")

        runtime_version = self._resolve_runtime_version(request)
        compile_started_at = datetime.utcnow()

        sequences = (
            self.db.query(Sequence)
            .filter(Sequence.project_id == request.project_id)
            .order_by(Sequence.sequence_index.asc())
            .all()
        )
        spus = self.db.query(SPU).filter(SPU.project_id == request.project_id).all()
        vbus = self.db.query(VBU).filter(VBU.project_id == request.project_id).all()
        bridges = (
            self.db.query(Bridge)
            .filter(Bridge.project_id == request.project_id)
            .order_by(Bridge.execution_order.asc())
            .all()
        )

        spus_by_sequence: dict[UUID | None, list[SPU]] = defaultdict(list)
        for spu in spus:
            spus_by_sequence[spu.sequence_id].append(spu)

        vbus_by_sequence: dict[UUID | None, list[VBU]] = defaultdict(list)
        for vbu in vbus:
            vbus_by_sequence[vbu.sequence_id].append(vbu)

        bridges_by_sequence: dict[UUID, list[Bridge]] = defaultdict(list)
        for bridge in bridges:
            bridges_by_sequence[bridge.sequence_id].append(bridge)

        runtime_sequences: list[RuntimeSequencePacket] = []
        for sequence in sequences:
            runtime_sequences.append(
                RuntimeSequencePacket(
                    sequence_id=sequence.id,
                    sequence_index=sequence.sequence_index,
                    sequence_type=sequence.sequence_type,
                    persuasive_goal=sequence.persuasive_goal,
                    spus=[
                        {
                            "spu_id": str(item.id),
                            "spu_code": item.spu_code,
                            "display_name": item.display_name,
                            "asset_role": item.asset_role,
                            "duration_ms": item.duration_ms,
                            "generation_mode": item.generation_mode,
                            "prompt_text": item.prompt_text,
                            "negative_prompt_text": item.negative_prompt_text,
                            "visual_constraints": item.visual_constraints,
                            "status": item.status,
                        }
                        for item in spus_by_sequence.get(sequence.id, [])
                    ],
                    vbus=[
                        {
                            "vbu_id": str(item.id),
                            "vbu_code": item.vbu_code,
                            "persuasive_role": item.persuasive_role,
                            "script_text": item.script_text,
                            "voice_profile": item.voice_profile,
                            "language": item.language,
                            "duration_ms": item.duration_ms,
                            "tts_params": item.tts_params,
                            "status": item.status,
                        }
                        for item in vbus_by_sequence.get(sequence.id, [])
                    ],
                    bridges=[
                        {
                            "bridge_id": str(item.id),
                            "bridge_code": item.bridge_code,
                            "bridge_type": item.bridge_type,
                            "spu_id": str(item.spu_id) if item.spu_id else None,
                            "vbu_id": str(item.vbu_id) if item.vbu_id else None,
                            "execution_order": item.execution_order,
                            "transition_policy": item.transition_policy,
                            "status": item.status,
                        }
                        for item in bridges_by_sequence.get(sequence.id, [])
                    ],
                )
            )

        packet = RuntimePacket(
            project_id=request.project_id,
            runtime_version=runtime_version,
            compile_reason=request.compile_reason,
            compile_options=request.compile_options,
            visual_track_count=len(spus),
            audio_track_count=len(vbus),
            bridge_count=len(bridges),
            sequences=runtime_sequences,
        )

        runtime = CompiledRuntime(
            project_id=request.project_id,
            runtime_version=runtime_version,
            compile_status="compiled",
            runtime_payload=packet.model_dump(mode="json"),
            dispatch_status="not_dispatched",
            dispatch_summary={},
            compile_started_at=compile_started_at,
            compile_finished_at=datetime.utcnow(),
        )
        self.db.add(runtime)
        self.db.flush()

        if request.dispatch_jobs:
            dispatch_summary = self._create_and_dispatch_jobs(request.project_id, runtime_version)
            runtime.compile_status = "dispatched"
            runtime.dispatch_status = dispatch_summary["dispatch_status"]
            runtime.dispatch_summary = dispatch_summary
        else:
            runtime.dispatch_status = "not_dispatched"
            runtime.dispatch_summary = {
                "runtime_version": runtime_version,
                "job_count": 0,
                "queued_job_count": 0,
                "dispatched_job_count": 0,
                "undispatched_job_count": 0,
                "dispatch_status": "not_dispatched",
                "jobs": [],
            }

        self.db.commit()
        self.db.refresh(runtime)
        return runtime

    def validate_project(self, project_id: UUID) -> dict:
        return self.validator.validate_project(project_id)

    def _resolve_runtime_version(self, request: CompileRequest) -> str:
        if request.runtime_version and not request.auto_version:
            return request.runtime_version
        if request.auto_version or not request.runtime_version:
            return self.version_service.next_version(request.project_id)
        return request.runtime_version

    def _create_and_dispatch_jobs(self, project_id: UUID, runtime_version: str) -> dict:
        job_types = ["compile", "render_image", "render_video", "render_voice", "merge"]
        dispatched_jobs: list[dict] = []
        render_image_payload = self._build_render_image_payload(project_id, runtime_version)

        for job_type in job_types:
            payload = {
                "runtime_version": runtime_version,
                "dispatch_source": "compile_endpoint",
            }
            if job_type == "render_image":
                payload.update(render_image_payload)

            job = Job(
                project_id=project_id,
                job_type=job_type,
                status="queued",
                payload=payload,
            )
            self.db.add(job)
            self.db.flush()

            task_id = self.dispatch_service.dispatch(job, runtime_version)
            job.external_task_id = task_id
            job.result_payload = {"celery_task_id": task_id} if task_id else None
            if task_id:
                job.status = "dispatched"

            dispatched_jobs.append(
                {
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "external_task_id": task_id,
                }
            )

        dispatched_job_count = sum(1 for item in dispatched_jobs if item["external_task_id"])
        queued_job_count = sum(1 for item in dispatched_jobs if item["status"] == "queued")
        dispatch_status = "fully_dispatched" if dispatched_job_count == len(dispatched_jobs) else "partially_dispatched"

        return {
            "runtime_version": runtime_version,
            "job_count": len(dispatched_jobs),
            "queued_job_count": queued_job_count,
            "dispatched_job_count": dispatched_job_count,
            "undispatched_job_count": len(dispatched_jobs) - dispatched_job_count,
            "dispatch_status": dispatch_status,
            "jobs": dispatched_jobs,
        }

    def _build_render_image_payload(self, project_id: UUID, runtime_version: str) -> dict:
        project = self.db.get(Project, project_id)
        sequences = (
            self.db.query(Sequence)
            .filter(Sequence.project_id == project_id)
            .order_by(Sequence.sequence_index.asc())
            .all()
        )
        spus = (
            self.db.query(SPU)
            .filter(SPU.project_id == project_id)
            .order_by(SPU.created_at.asc())
            .all()
        )

        primary_spu = next((spu for spu in spus if (spu.prompt_text or "").strip()), None)
        negative_prompt = None
        prompt_segments: list[str] = []

        if project:
            prompt_segments.append(f"Project: {project.name}")
            prompt_segments.append(f"Target market: {project.source_market}")
            prompt_segments.append(f"Target language: {project.source_language}")
            if project.notes:
                prompt_segments.append(f"Project notes: {project.notes.strip()}")

        if sequences:
            sequence_descriptions = []
            for sequence in sequences:
                sequence_bits = [f"Sequence {sequence.sequence_index}", sequence.sequence_type]
                if sequence.persuasive_goal:
                    sequence_bits.append(sequence.persuasive_goal.strip())
                sequence_descriptions.append(" - ".join(bit for bit in sequence_bits if bit))
            prompt_segments.append("Sequence plan: " + " | ".join(sequence_descriptions))

        if primary_spu:
            prompt_segments.append(f"Primary visual subject: {primary_spu.display_name}")
            prompt_segments.append(primary_spu.prompt_text.strip())
            negative_prompt = self._normalize_optional_text(primary_spu.negative_prompt_text)
            visual_constraints = primary_spu.visual_constraints or {}
        else:
            visual_constraints = {}
            if spus:
                prompt_segments.append(f"Primary visual subject: {spus[0].display_name}")

        if visual_constraints:
            prompt_segments.append(f"Visual constraints: {visual_constraints}")

        prompt = "\n".join(segment for segment in prompt_segments if segment and str(segment).strip()).strip()

        provider_inputs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "sample_count": 1,
            "aspect_ratio": "9:16",
            "source": "compiler_minimal_render_image_prompt_v1",
            "runtime_version": runtime_version,
        }

        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "provider_inputs": provider_inputs,
        }

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
