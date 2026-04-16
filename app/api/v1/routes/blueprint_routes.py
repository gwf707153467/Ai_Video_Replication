from fastapi import APIRouter

from app.compilers.orchestrator.blueprint_compiler import compile_blueprint_v0_to_runtime_packet
from app.schemas import (
    BlueprintCompilePreviewRead,
    BlueprintV0,
    BlueprintValidationCountsV0,
    BlueprintValidationRead,
)

router = APIRouter()


def _build_validation_counts(blueprint: BlueprintV0) -> BlueprintValidationCountsV0:
    return BlueprintValidationCountsV0(
        sequences=len(blueprint.sequences),
        spus=sum(len(sequence.spus) for sequence in blueprint.sequences),
        vbus=sum(len(sequence.vbus) for sequence in blueprint.sequences),
        bridges=sum(len(sequence.bridges) for sequence in blueprint.sequences),
        reference_beats=len(blueprint.reference.reference_beats),
    )


@router.post("/validate", response_model=BlueprintValidationRead)
def validate_blueprint(payload: BlueprintV0) -> BlueprintValidationRead:
    effective_runtime_version = (
        payload.compile_preferences.requested_runtime_version or f"{payload.blueprint_id}.stub"
    )
    return BlueprintValidationRead(
        blueprint_id=payload.blueprint_id,
        blueprint_version=payload.blueprint_version,
        is_valid=True,
        counts=_build_validation_counts(payload),
        requested_runtime_version=payload.compile_preferences.requested_runtime_version,
        effective_runtime_version=effective_runtime_version,
        dispatch_jobs=payload.compile_preferences.dispatch_jobs,
    )


@router.post("/compile-preview", response_model=BlueprintCompilePreviewRead)
def compile_blueprint_preview(payload: BlueprintV0) -> BlueprintCompilePreviewRead:
    runtime_packet = compile_blueprint_v0_to_runtime_packet(payload)
    return BlueprintCompilePreviewRead(
        blueprint_id=payload.blueprint_id,
        blueprint_version=payload.blueprint_version,
        runtime_packet=runtime_packet,
    )


__all__ = ["router", "validate_blueprint", "compile_blueprint_preview"]
