from datetime import datetime
from uuid import UUID

from app.db.models import Asset, CompiledRuntime, Job, Sequence
from app.db.session import SessionLocal
from app.providers.google.client import GoogleProviderError
from app.services.asset_policy_service import AssetPolicyService
from app.services.runtime_artifact_service import RuntimeArtifactService
from app.services.runtime_state_service import RuntimeStateService
from app.workers.celery_app import celery_app
from app.workers.executors import ProviderExecutorError, ProviderExecutorRegistry


ASSET_NOTES = "sixth_batch_materialization_backbone"
_BINARY_REQUIRED_CONTENT_TYPE_PREFIXES = ("image/", "video/", "audio/")


def _load_runtime(db, project_id: str, runtime_version: str) -> CompiledRuntime | None:
    return (
        db.query(CompiledRuntime)
        .filter(
            CompiledRuntime.project_id == UUID(project_id),
            CompiledRuntime.runtime_version == runtime_version,
        )
        .order_by(CompiledRuntime.created_at.desc())
        .first()
    )


def _update_runtime_status(
    db,
    project_id: str,
    runtime_version: str,
    *,
    compile_status: str | None = None,
    last_error_code: str | None = None,
    last_error_message: str | None = None,
) -> None:
    runtime = _load_runtime(db, project_id, runtime_version)
    if not runtime:
        return

    if compile_status:
        runtime.compile_status = compile_status
    if last_error_code is not None:
        runtime.last_error_code = last_error_code
    if last_error_message is not None:
        runtime.last_error_message = last_error_message


def _refresh_runtime_aggregate(db, project_id: str, runtime_version: str) -> None:
    runtime = _load_runtime(db, project_id, runtime_version)
    if not runtime:
        return
    RuntimeStateService.refresh_runtime_status(db, runtime)


def _mark_job_running(db, job: Job, task_name: str) -> None:
    job.status = "running"
    job.attempt_count = (job.attempt_count or 0) + 1
    job.started_at = datetime.utcnow()
    job.error_code = None
    job.error_message = None

    result_payload = dict(job.result_payload or {})
    result_payload["task"] = task_name
    result_payload["worker_started_at"] = job.started_at.isoformat()
    job.result_payload = result_payload


def _mark_job_succeeded(db, job: Job, payload: dict) -> dict:
    finished_at = datetime.utcnow()
    job.status = "succeeded"
    job.finished_at = finished_at
    job.result_payload = payload
    return payload


def _mark_job_failed(db, job: Job, error_code: str, error_message: str) -> None:
    finished_at = datetime.utcnow()
    job.status = "failed"
    job.finished_at = finished_at
    job.error_code = error_code
    job.error_message = error_message

    result_payload = dict(job.result_payload or {})
    result_payload["error_code"] = error_code
    result_payload["error_message"] = error_message
    result_payload["worker_finished_at"] = finished_at.isoformat()
    job.result_payload = result_payload


def _first_sequence_id(db, project_id: str):
    sequence = (
        db.query(Sequence)
        .filter(Sequence.project_id == UUID(project_id))
        .order_by(Sequence.sequence_index.asc())
        .first()
    )
    return sequence.id if sequence else None


def _runtime_asset_object_key(project_id: str, runtime_version: str, job: Job, filename: str) -> str:
    return AssetPolicyService.build_runtime_asset_object_key(
        project_id=UUID(project_id),
        runtime_version=runtime_version,
        job_type=job.job_type,
        filename=filename,
    )


def _find_existing_runtime_asset(db, *, bucket_name: str, object_key: str) -> Asset | None:
    return (
        db.query(Asset)
        .filter(
            Asset.bucket_name == bucket_name,
            Asset.object_key == object_key,
        )
        .first()
    )


def _register_generated_asset(
    db,
    *,
    project_id: str,
    runtime_version: str,
    job: Job,
    asset_type: str,
    asset_role: str,
    filename: str,
    content_type: str,
    status: str = "registered",
) -> Asset:
    project_uuid = UUID(project_id)
    sequence_id = _first_sequence_id(db, project_id)
    bucket_name = AssetPolicyService.resolve_bucket(asset_type)
    object_key = _runtime_asset_object_key(project_id, runtime_version, job, filename)
    existing_asset = _find_existing_runtime_asset(db, bucket_name=bucket_name, object_key=object_key)
    metadata = {
        "runtime_version": runtime_version,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "external_task_id": job.external_task_id,
        "generated_by": "worker_provider_executor",
    }

    if existing_asset:
        existing_asset.project_id = project_uuid
        existing_asset.sequence_id = sequence_id
        existing_asset.asset_type = asset_type
        existing_asset.asset_role = asset_role
        existing_asset.source_filename = filename
        existing_asset.content_type = content_type
        existing_asset.asset_metadata = {
            **dict(existing_asset.asset_metadata or {}),
            **metadata,
        }
        existing_asset.status = status
        existing_asset.notes = ASSET_NOTES
        db.flush()
        return existing_asset

    asset = Asset(
        project_id=project_uuid,
        sequence_id=sequence_id,
        asset_type=asset_type,
        asset_role=asset_role,
        bucket_name=bucket_name,
        object_key=object_key,
        source_filename=filename,
        content_type=content_type,
        file_size=None,
        asset_metadata=metadata,
        status=status,
        notes=ASSET_NOTES,
    )
    db.add(asset)
    db.flush()
    return asset


def _build_asset_payload(asset: Asset | None) -> dict | None:
    if not asset:
        return None
    return {
        "asset_id": str(asset.id),
        "bucket_name": asset.bucket_name,
        "object_key": asset.object_key,
        "asset_type": asset.asset_type,
        "asset_role": asset.asset_role,
        "status": asset.status,
        "content_type": asset.content_type,
        "file_size": asset.file_size,
    }


def _extract_error_details(exc: Exception) -> tuple[str, str]:
    error_code = getattr(exc, "code", None)
    if not isinstance(error_code, str) or not error_code.strip():
        error_code = "worker_execution_failed"

    error_message = getattr(exc, "message", None)
    if not isinstance(error_message, str) or not error_message.strip():
        error_message = str(exc)
    return error_code, error_message


def _asset_requires_binary_payload(asset_plan: dict | None) -> bool:
    if not asset_plan:
        return False
    content_type = str(asset_plan.get("content_type") or "").strip().lower()
    return content_type.startswith(_BINARY_REQUIRED_CONTENT_TYPE_PREFIXES)


def _resolve_asset_content_type(execution_result: dict, asset_plan: dict) -> str:
    resolved_content_type = str(execution_result.get("content_type") or asset_plan["content_type"]).strip()
    return resolved_content_type or asset_plan["content_type"]


def _validate_execution_result(execution_result: dict, *, task_name: str, asset_plan: dict | None = None) -> None:
    status = str(execution_result.get("status") or "").strip() or "unknown"
    if status == "succeeded_stub":
        raise ProviderExecutorError(
            "provider_stub_result_disallowed",
            f"{task_name} returned succeeded_stub; stub success is forbidden for runtime jobs.",
        )
    if status != "succeeded":
        raise ProviderExecutorError(
            "provider_execution_not_succeeded",
            f"{task_name} returned unsupported execution status: {status}",
        )

    if not _asset_requires_binary_payload(asset_plan):
        return

    binary_payload = execution_result.get("binary_payload")
    if binary_payload is None:
        raise ProviderExecutorError(
            "binary_payload_required",
            f"{task_name} requires binary_payload for {asset_plan.get('content_type')} artifacts.",
        )
    if not isinstance(binary_payload, (bytes, bytearray, memoryview)):
        raise ProviderExecutorError(
            "binary_payload_invalid_type",
            f"{task_name} produced non-bytes binary_payload for {asset_plan.get('content_type')} artifacts.",
        )
    if len(bytes(binary_payload)) == 0:
        raise ProviderExecutorError(
            "binary_payload_empty",
            f"{task_name} produced empty binary_payload for {asset_plan.get('content_type')} artifacts.",
        )


def _resolve_materialization_payload(execution_result: dict, asset_plan: dict) -> bytes:
    if execution_result.get("binary_payload") is not None:
        payload = execution_result["binary_payload"]
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, bytearray):
            return bytes(payload)
        if isinstance(payload, memoryview):
            return payload.tobytes()
        if not _asset_requires_binary_payload(asset_plan) and isinstance(payload, str):
            return payload.encode("utf-8")
        raise ValueError("unsupported_binary_payload_type")

    if _asset_requires_binary_payload(asset_plan):
        raise ValueError("binary_payload_required_for_non_text_asset")

    text_payload = execution_result.get("text_payload")
    if text_payload is None:
        raise ValueError("text_payload_missing_for_text_asset")
    return str(text_payload).encode("utf-8")


def _materialize_generated_asset(
    db,
    *,
    project_id: str,
    runtime_version: str,
    job: Job,
    asset_plan: dict,
    execution_result: dict,
) -> tuple[Asset, dict]:
    filename = execution_result.get("output_filename") or asset_plan["filename"]
    resolved_content_type = _resolve_asset_content_type(execution_result, asset_plan)
    asset = _register_generated_asset(
        db,
        project_id=project_id,
        runtime_version=runtime_version,
        job=job,
        asset_type=asset_plan["asset_type"],
        asset_role=asset_plan["asset_role"],
        filename=filename,
        content_type=resolved_content_type,
        status="registered",
    )

    artifact_service = RuntimeArtifactService()
    materialization = {
        "bucket_name": asset.bucket_name,
        "object_key": asset.object_key,
        "idempotency": "fresh_write",
    }

    if asset.status == "materialized" and artifact_service.object_exists(asset.bucket_name, asset.object_key):
        existing = artifact_service.stat_object(asset.bucket_name, asset.object_key)
        if existing:
            asset.file_size = existing.size
            asset.content_type = existing.content_type or asset.content_type
            asset.asset_metadata = {
                **dict(asset.asset_metadata or {}),
                "materialization_status": "already_present",
                "materialized_etag": existing.etag,
                "materialized_version_id": existing.version_id,
            }
        db.flush()
        materialization.update(
            {
                "idempotency": "asset_already_materialized",
                "status": "materialized",
                "etag": existing.etag if existing else None,
                "version_id": existing.version_id if existing else None,
                "size": existing.size if existing else asset.file_size,
            }
        )
        return asset, materialization

    if artifact_service.object_exists(asset.bucket_name, asset.object_key):
        existing = artifact_service.stat_object(asset.bucket_name, asset.object_key)
        asset.status = "materialized"
        asset.file_size = existing.size if existing else asset.file_size
        asset.content_type = (existing.content_type if existing else None) or asset.content_type
        asset.asset_metadata = {
            **dict(asset.asset_metadata or {}),
            "materialization_status": "reconciled_from_object_store",
            "materialized_etag": existing.etag if existing else None,
            "materialized_version_id": existing.version_id if existing else None,
        }
        db.flush()
        materialization.update(
            {
                "idempotency": "object_store_short_circuit",
                "status": "materialized",
                "etag": existing.etag if existing else None,
                "version_id": existing.version_id if existing else None,
                "size": existing.size if existing else asset.file_size,
            }
        )
        return asset, materialization

    payload = _resolve_materialization_payload(execution_result, asset_plan)
    stored = artifact_service.materialize_bytes(
        bucket_name=asset.bucket_name,
        object_key=asset.object_key,
        payload=payload,
        content_type=asset.content_type or resolved_content_type,
    )
    asset.status = "materialized"
    asset.file_size = stored.size
    asset.content_type = stored.content_type or asset.content_type
    asset.asset_metadata = {
        **dict(asset.asset_metadata or {}),
        "materialization_status": "uploaded_by_worker",
        "materialized_etag": stored.etag,
        "materialized_version_id": stored.version_id,
    }
    db.flush()
    materialization.update(
        {
            "status": "materialized",
            "etag": stored.etag,
            "version_id": stored.version_id,
            "size": stored.size,
        }
    )
    return asset, materialization


def _run_job(job_id: str, project_id: str, runtime_version: str, task_name: str, asset_plan: dict | None = None) -> dict:
    db = SessionLocal()
    try:
        job = db.get(Job, UUID(job_id))
        if not job:
            raise ValueError("job_not_found")

        _mark_job_running(db, job, task_name)
        _update_runtime_status(
            db,
            project_id,
            runtime_version,
            compile_status="running",
            last_error_code=None,
            last_error_message=None,
        )
        _refresh_runtime_aggregate(db, project_id, runtime_version)
        db.commit()

        executor = ProviderExecutorRegistry.resolve(job.job_type)
        execution_result = executor.execute(
            job=job,
            project_id=project_id,
            runtime_version=runtime_version,
            task_name=task_name,
            asset_plan=asset_plan,
        )
        _validate_execution_result(
            execution_result,
            task_name=task_name,
            asset_plan=asset_plan,
        )

        asset = None
        materialization = None
        if asset_plan:
            job = db.get(Job, UUID(job_id))
            if not job:
                raise ValueError("job_not_found_after_execution")
            asset, materialization = _materialize_generated_asset(
                db,
                project_id=project_id,
                runtime_version=runtime_version,
                job=job,
                asset_plan=asset_plan,
                execution_result=execution_result,
            )

        finished_at = datetime.utcnow()
        result = {
            "job_id": job_id,
            "project_id": project_id,
            "runtime_version": runtime_version,
            "status": execution_result.get("status", "succeeded"),
            "task": task_name,
            "provider": execution_result.get("provider", "unknown"),
            "worker_finished_at": finished_at.isoformat(),
            "provider_payload": execution_result.get("provider_payload", {}),
        }
        asset_payload = _build_asset_payload(asset)
        if asset_payload:
            result["asset"] = asset_payload
        if materialization:
            result["materialization"] = materialization

        _mark_job_succeeded(db, job, result)
        _refresh_runtime_aggregate(db, project_id, runtime_version)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()

        error_code, error_message = _extract_error_details(exc)
        job = db.get(Job, UUID(job_id))
        if job and asset_plan:
            failed_filename = asset_plan["filename"]
            failed_asset = _register_generated_asset(
                db,
                project_id=project_id,
                runtime_version=runtime_version,
                job=job,
                asset_type=asset_plan["asset_type"],
                asset_role=asset_plan["asset_role"],
                filename=failed_filename,
                content_type=asset_plan["content_type"],
                status="failed",
            )
            failed_asset.asset_metadata = {
                **dict(failed_asset.asset_metadata or {}),
                "materialization_status": "failed",
                "materialization_error": error_message,
                "materialization_error_code": error_code,
            }
            db.flush()
        if job:
            _mark_job_failed(db, job, error_code, error_message)
        _update_runtime_status(
            db,
            project_id,
            runtime_version,
            compile_status="failed",
            last_error_code=error_code,
            last_error_message=error_message,
        )
        _refresh_runtime_aggregate(db, project_id, runtime_version)
        db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="compile.runtime")
def compile_runtime_task(job_id: str, project_id: str, runtime_version: str) -> dict:
    return _run_job(job_id, project_id, runtime_version, "compile.runtime")


@celery_app.task(name="render.image")
def render_image_task(job_id: str, project_id: str, runtime_version: str) -> dict:
    return _run_job(
        job_id,
        project_id,
        runtime_version,
        "render.image",
        asset_plan={
            "asset_type": "generated_image",
            "asset_role": "render_output",
            "filename": f"{job_id}.png",
            "content_type": "image/png",
        },
    )


@celery_app.task(name="render.video")
def render_video_task(job_id: str, project_id: str, runtime_version: str) -> dict:
    return _run_job(
        job_id,
        project_id,
        runtime_version,
        "render.video",
        asset_plan={
            "asset_type": "generated_video",
            "asset_role": "render_output",
            "filename": f"{job_id}.mp4",
            "content_type": "video/mp4",
        },
    )


@celery_app.task(name="render.voice")
def render_voice_task(job_id: str, project_id: str, runtime_version: str) -> dict:
    return _run_job(
        job_id,
        project_id,
        runtime_version,
        "render.voice",
        asset_plan={
            "asset_type": "audio",
            "asset_role": "voice_output",
            "filename": f"{job_id}.wav",
            "content_type": "audio/wav",
        },
    )


@celery_app.task(name="merge.runtime")
def merge_runtime_task(job_id: str, project_id: str, runtime_version: str) -> dict:
    return _run_job(
        job_id,
        project_id,
        runtime_version,
        "merge.runtime",
        asset_plan={
            "asset_type": "export",
            "asset_role": "merged_output",
            "filename": f"{runtime_version}-{job_id}.mp4",
            "content_type": "video/mp4",
        },
    )
