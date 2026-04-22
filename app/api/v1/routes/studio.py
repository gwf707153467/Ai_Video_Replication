from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.compilers.orchestrator.compiler_service import CompilerService
from app.db.models import Asset, CompiledRuntime, Job, Project, SPU, Sequence, VBU
from app.db.session import get_db
from app.schemas.compile import CompileRequest
from app.services.storage_service import StorageService

router = APIRouter()


class StudioGenerateRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    target_market: str = "US"
    target_language: str = "en-US"
    product_name: str = Field(min_length=1, max_length=255)
    reference_note: str | None = None
    visual_prompt: str = Field(min_length=1)
    voice_script: str = Field(min_length=1)
    negative_prompt: str | None = None
    duration_ms: int = 6000


class StudioGenerateResponse(BaseModel):
    project_id: str
    runtime_id: str
    runtime_version: str


class StudioJobView(BaseModel):
    job_id: str
    job_type: str
    status: str
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class StudioAssetView(BaseModel):
    asset_id: str
    asset_type: str
    asset_role: str
    status: str
    bucket_name: str
    object_key: str
    file_size: int | None = None
    content_type: str | None = None
    download_url: str | None = None


class StudioRuntimeView(BaseModel):
    runtime_id: str
    project_id: str
    runtime_version: str
    compile_status: str
    dispatch_status: str
    last_error_code: str | None = None
    last_error_message: str | None = None
    jobs: list[StudioJobView]
    assets: list[StudioAssetView]
    final_export: StudioAssetView | None = None


def _first_or_404(db: Session, runtime_id: UUID) -> CompiledRuntime:
    runtime = db.get(CompiledRuntime, runtime_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="runtime_not_found")
    return runtime


def _default_negative_prompt() -> str:
    return (
        "blurry, warped product shape, fake logos, watermark, captions, text overlay, "
        "low quality, distorted hands"
    )


def _runtime_jobs(db: Session, runtime: CompiledRuntime) -> list[Job]:
    return (
        db.query(Job)
        .filter(
            Job.project_id == runtime.project_id,
            Job.payload["runtime_version"].astext == runtime.runtime_version,
        )
        .order_by(Job.created_at.asc())
        .all()
    )


def _runtime_assets(db: Session, runtime: CompiledRuntime) -> list[Asset]:
    candidates = (
        db.query(Asset)
        .filter(Asset.project_id == runtime.project_id)
        .order_by(Asset.created_at.asc())
        .all()
    )
    return [
        asset
        for asset in candidates
        if isinstance(asset.asset_metadata, dict)
        and asset.asset_metadata.get("runtime_version") == runtime.runtime_version
    ]


def _asset_view(asset: Asset) -> StudioAssetView:
    download_url = (
        f"/api/v1/studio/assets/download?bucket_name={asset.bucket_name}"
        f"&object_key={asset.object_key}"
    )
    return StudioAssetView(
        asset_id=str(asset.id),
        asset_type=asset.asset_type,
        asset_role=asset.asset_role,
        status=asset.status,
        bucket_name=asset.bucket_name,
        object_key=asset.object_key,
        file_size=asset.file_size,
        content_type=asset.content_type,
        download_url=download_url,
    )


@router.post("/generate", response_model=StudioGenerateResponse)
def generate_video(payload: StudioGenerateRequest, db: Session = Depends(get_db)) -> StudioGenerateResponse:
    project = Project(
        name=payload.project_name.strip(),
        source_market=payload.target_market.strip() or "US",
        source_language=payload.target_language.strip() or "en-US",
        notes=payload.reference_note,
    )
    db.add(project)
    db.flush()

    sequence = Sequence(
        project_id=project.id,
        sequence_index=1,
        sequence_type="hook",
        persuasive_goal=f"Replicate a short-form ecommerce video for {payload.product_name}.",
    )
    db.add(sequence)
    db.flush()

    spu = SPU(
        project_id=project.id,
        sequence_id=sequence.id,
        spu_code="SPU-001",
        display_name=payload.product_name,
        asset_role="primary_visual",
        duration_ms=payload.duration_ms,
        generation_mode="veo_segment",
        prompt_text=payload.visual_prompt.strip(),
        negative_prompt_text=payload.negative_prompt or _default_negative_prompt(),
        visual_constraints={
            "platform": "tiktok_9_16",
            "style": "short_form_ecommerce_replication",
        },
    )
    db.add(spu)

    vbu = VBU(
        project_id=project.id,
        sequence_id=sequence.id,
        vbu_code="VBU-001",
        persuasive_role="hook",
        script_text=payload.voice_script.strip(),
        language=project.source_language,
        duration_ms=payload.duration_ms,
        tts_params={},
    )
    db.add(vbu)
    db.flush()

    runtime = CompilerService(db).compile_project(
        CompileRequest(
            project_id=project.id,
            compile_reason="studio_generate",
            compile_options={
                "source": "studio_minimal_frontend",
                "reference_note": payload.reference_note,
            },
            auto_version=True,
            dispatch_jobs=True,
        )
    )
    return StudioGenerateResponse(
        project_id=str(project.id),
        runtime_id=str(runtime.id),
        runtime_version=runtime.runtime_version,
    )


@router.get("/runtimes/{runtime_id}", response_model=StudioRuntimeView)
def get_runtime(runtime_id: UUID, db: Session = Depends(get_db)) -> StudioRuntimeView:
    runtime = _first_or_404(db, runtime_id)
    jobs = [
        StudioJobView(
            job_id=str(job.id),
            job_type=job.job_type,
            status=job.status,
            error_code=job.error_code,
            error_message=job.error_message,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        for job in _runtime_jobs(db, runtime)
    ]
    assets = [_asset_view(asset) for asset in _runtime_assets(db, runtime)]
    final_export = next(
        (asset for asset in assets if asset.asset_type == "export" and asset.status == "materialized"),
        None,
    )
    return StudioRuntimeView(
        runtime_id=str(runtime.id),
        project_id=str(runtime.project_id),
        runtime_version=runtime.runtime_version,
        compile_status=runtime.compile_status,
        dispatch_status=runtime.dispatch_status,
        last_error_code=runtime.last_error_code,
        last_error_message=runtime.last_error_message,
        jobs=jobs,
        assets=assets,
        final_export=final_export,
    )


@router.get("/runtimes", response_model=list[StudioRuntimeView])
def list_runtimes(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)) -> list[StudioRuntimeView]:
    runtimes = (
        db.query(CompiledRuntime)
        .order_by(CompiledRuntime.created_at.desc())
        .limit(limit)
        .all()
    )
    return [get_runtime(runtime.id, db) for runtime in runtimes]


@router.get("/assets/download")
def download_asset(bucket_name: str, object_key: str) -> Response:
    payload = StorageService().get_bytes(bucket_name, object_key)
    filename = object_key.rsplit("/", 1)[-1] or "asset.bin"
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
