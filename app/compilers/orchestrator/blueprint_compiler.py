from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from app.schemas.blueprint import (
    BlueprintBridgeV0,
    BlueprintSPUV0,
    BlueprintSequenceV0,
    BlueprintV0,
    BlueprintVBUV0,
)
from app.schemas.compile import RuntimePacket, RuntimeSequencePacket


BLUEPRINT_UUID_NAMESPACE = uuid5(NAMESPACE_URL, "ai-videos-replication/blueprint-v0")


def compile_blueprint_v0_to_runtime_packet(blueprint: BlueprintV0) -> RuntimePacket:
    project_uuid = _stable_uuid("project", blueprint.blueprint_id)
    ordered_sequences = sorted(blueprint.sequences, key=lambda item: item.sequence_index)
    sequences = [
        _compile_sequence(sequence=sequence, blueprint=blueprint)
        for sequence in ordered_sequences
    ]

    visual_track_count = sum(len(sequence.spus) for sequence in blueprint.sequences)
    audio_track_count = sum(len(sequence.vbus) for sequence in blueprint.sequences)
    bridge_count = sum(len(sequence.bridges) for sequence in blueprint.sequences)

    compile_options: dict[str, Any] = dict(blueprint.compile_preferences.compile_options)
    compile_options.setdefault("blueprint_id", blueprint.blueprint_id)
    compile_options.setdefault("blueprint_version", blueprint.blueprint_version)
    compile_options.setdefault("aspect_ratio", blueprint.global_constraints.aspect_ratio)
    compile_options.setdefault("style_tags", list(blueprint.global_constraints.style_tags))
    compile_options.setdefault("banned_elements", list(blueprint.global_constraints.banned_elements))
    compile_options.setdefault("target_duration_ms", blueprint.global_constraints.target_duration_ms)
    compile_options.setdefault("reference", _build_reference_payload(blueprint))

    return RuntimePacket(
        project_id=project_uuid,
        runtime_version=(
            blueprint.compile_preferences.requested_runtime_version
            or f"{blueprint.blueprint_id}.stub"
        ),
        compile_reason=blueprint.compile_preferences.compile_reason,
        compile_options=compile_options,
        visual_track_count=visual_track_count,
        audio_track_count=audio_track_count,
        bridge_count=bridge_count,
        sequences=sequences,
    )


def _compile_sequence(sequence: BlueprintSequenceV0, blueprint: BlueprintV0) -> RuntimeSequencePacket:
    sequence_uuid = _stable_uuid("sequence", blueprint.blueprint_id, sequence.sequence_code)

    return RuntimeSequencePacket(
        sequence_id=sequence_uuid,
        sequence_index=sequence.sequence_index,
        sequence_type=sequence.sequence_type,
        persuasive_goal=sequence.persuasive_goal,
        spus=[
            _compile_spu(sequence=sequence, spu=spu, blueprint=blueprint)
            for spu in sequence.spus
        ],
        vbus=[
            _compile_vbu(sequence=sequence, vbu=vbu, blueprint=blueprint)
            for vbu in sequence.vbus
        ],
        bridges=[
            _compile_bridge(sequence=sequence, bridge=bridge, blueprint=blueprint)
            for bridge in sorted(sequence.bridges, key=lambda item: item.execution_order)
        ],
    )


def _compile_spu(
    sequence: BlueprintSequenceV0,
    spu: BlueprintSPUV0,
    blueprint: BlueprintV0,
) -> dict[str, Any]:
    return {
        "spu_id": str(_stable_uuid("spu", blueprint.blueprint_id, sequence.sequence_code, spu.spu_code)),
        "spu_code": spu.spu_code,
        "display_name": spu.display_name,
        "asset_role": spu.asset_role,
        "duration_ms": spu.duration_ms,
        "generation_mode": spu.generation_mode,
        "prompt_text": spu.prompt_text,
        "negative_prompt_text": spu.negative_prompt_text,
        "visual_constraints": spu.visual_constraints,
        "status": spu.status,
        "reference_mapping": spu.reference_mapping.model_dump(mode="python"),
        "sequence_code": sequence.sequence_code,
    }


def _compile_vbu(
    sequence: BlueprintSequenceV0,
    vbu: BlueprintVBUV0,
    blueprint: BlueprintV0,
) -> dict[str, Any]:
    return {
        "vbu_id": str(_stable_uuid("vbu", blueprint.blueprint_id, sequence.sequence_code, vbu.vbu_code)),
        "vbu_code": vbu.vbu_code,
        "persuasive_role": vbu.persuasive_role,
        "script_text": vbu.script_text,
        "voice_profile": vbu.voice_profile,
        "language": vbu.language or blueprint.project.source_language,
        "duration_ms": vbu.duration_ms,
        "tts_params": vbu.tts_params,
        "status": vbu.status,
        "reference_mapping": vbu.reference_mapping.model_dump(mode="python"),
        "sequence_code": sequence.sequence_code,
    }


def _compile_bridge(
    sequence: BlueprintSequenceV0,
    bridge: BlueprintBridgeV0,
    blueprint: BlueprintV0,
) -> dict[str, Any]:
    return {
        "bridge_id": str(
            _stable_uuid("bridge", blueprint.blueprint_id, sequence.sequence_code, bridge.bridge_code)
        ),
        "bridge_code": bridge.bridge_code,
        "bridge_type": bridge.bridge_type,
        "execution_order": bridge.execution_order,
        "spu_id": (
            str(_stable_uuid("spu", blueprint.blueprint_id, sequence.sequence_code, bridge.spu_code))
            if bridge.spu_code
            else None
        ),
        "vbu_id": (
            str(_stable_uuid("vbu", blueprint.blueprint_id, sequence.sequence_code, bridge.vbu_code))
            if bridge.vbu_code
            else None
        ),
        "spu_code": bridge.spu_code,
        "vbu_code": bridge.vbu_code,
        "transition_policy": bridge.transition_policy,
        "status": bridge.status,
        "sequence_code": sequence.sequence_code,
    }


def _build_reference_payload(blueprint: BlueprintV0) -> dict[str, Any]:
    return {
        "source_kind": blueprint.reference.source_kind,
        "source_uri": blueprint.reference.source_uri,
        "structural_goal": blueprint.reference.structural_goal,
        "retained_axes": list(blueprint.reference.retained_axes),
        "swappable_axes": list(blueprint.reference.swappable_axes),
        "reference_beats": [
            beat.model_dump(mode="python") for beat in blueprint.reference.reference_beats
        ],
        "notes": list(blueprint.reference.notes),
    }


def _stable_uuid(kind: str, *parts: str) -> UUID:
    stable_name = "::".join([kind, *parts])
    return uuid5(BLUEPRINT_UUID_NAMESPACE, stable_name)


__all__ = ["compile_blueprint_v0_to_runtime_packet"]
