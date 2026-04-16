from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.compile import RuntimePacket

CODE_PATTERN = r"^[a-z0-9][a-z0-9._-]{1,63}$"


class BlueprintBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BlueprintReferenceMappingV0(BlueprintBaseModel):
    source_moments: list[str] = Field(default_factory=list)
    preserved_elements: list[str] = Field(default_factory=list)
    rewrite_axes: list[str] = Field(default_factory=list)


class BlueprintReferenceBeatV0(BlueprintBaseModel):
    beat_code: str = Field(min_length=2, max_length=64, pattern=CODE_PATTERN)
    sequence_code: str = Field(min_length=2, max_length=64, pattern=CODE_PATTERN)
    structural_function: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=1, max_length=1000)
    rewrite_notes: list[str] = Field(default_factory=list)


class BlueprintReferenceV0(BlueprintBaseModel):
    source_kind: Literal["uploaded_video", "url", "manual_notes", "mixed"] = "manual_notes"
    source_uri: str | None = None
    structural_goal: str = Field(min_length=1, max_length=500)
    retained_axes: list[str] = Field(default_factory=list)
    swappable_axes: list[str] = Field(default_factory=list)
    reference_beats: list[BlueprintReferenceBeatV0] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BlueprintProjectV0(BlueprintBaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_market: str = Field(default="US", min_length=2, max_length=32)
    source_language: str = Field(default="en-US", min_length=2, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)


class BlueprintCompilePreferencesV0(BlueprintBaseModel):
    requested_runtime_version: str | None = Field(default=None, min_length=1, max_length=128)
    compile_reason: str = Field(default="blueprint_stub", min_length=1, max_length=64)
    compile_options: dict[str, Any] = Field(default_factory=dict)
    dispatch_jobs: bool = False


class BlueprintGlobalConstraintsV0(BlueprintBaseModel):
    aspect_ratio: str = Field(default="9:16", min_length=3, max_length=16)
    target_duration_ms: int | None = Field(default=None, gt=0)
    style_tags: list[str] = Field(default_factory=list)
    banned_elements: list[str] = Field(default_factory=list)


class BlueprintSPUV0(BlueprintBaseModel):
    spu_code: str = Field(min_length=2, max_length=64, pattern=CODE_PATTERN)
    display_name: str = Field(min_length=1, max_length=200)
    asset_role: str = Field(default="primary_visual", min_length=1, max_length=64)
    duration_ms: int = Field(default=5000, gt=0)
    generation_mode: str = Field(default="veo_segment", min_length=1, max_length=64)
    prompt_text: str | None = Field(default=None, max_length=4000)
    negative_prompt_text: str | None = Field(default=None, max_length=4000)
    visual_constraints: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="draft", min_length=1, max_length=32)
    reference_mapping: BlueprintReferenceMappingV0 = Field(default_factory=BlueprintReferenceMappingV0)


class BlueprintVBUV0(BlueprintBaseModel):
    vbu_code: str = Field(min_length=2, max_length=64, pattern=CODE_PATTERN)
    persuasive_role: str = Field(default="benefit", min_length=1, max_length=64)
    script_text: str = Field(min_length=1, max_length=4000)
    voice_profile: str | None = Field(default=None, max_length=128)
    language: str | None = Field(default=None, min_length=2, max_length=32)
    duration_ms: int | None = Field(default=None, gt=0)
    tts_params: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="draft", min_length=1, max_length=32)
    reference_mapping: BlueprintReferenceMappingV0 = Field(default_factory=BlueprintReferenceMappingV0)


class BlueprintBridgeV0(BlueprintBaseModel):
    bridge_code: str = Field(min_length=2, max_length=64, pattern=CODE_PATTERN)
    bridge_type: str = Field(default="sequence_unit_binding", min_length=1, max_length=64)
    execution_order: int = Field(default=0, ge=0)
    spu_code: str | None = Field(default=None, min_length=2, max_length=64, pattern=CODE_PATTERN)
    vbu_code: str | None = Field(default=None, min_length=2, max_length=64, pattern=CODE_PATTERN)
    transition_policy: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="draft", min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_target_binding(self) -> "BlueprintBridgeV0":
        if not self.spu_code and not self.vbu_code:
            raise ValueError("bridge_requires_spu_or_vbu_binding")
        return self


class BlueprintSequenceV0(BlueprintBaseModel):
    sequence_code: str = Field(min_length=2, max_length=64, pattern=CODE_PATTERN)
    sequence_index: int = Field(ge=0)
    sequence_type: str = Field(min_length=1, max_length=64)
    persuasive_goal: str | None = Field(default=None, max_length=500)
    target_duration_ms: int = Field(gt=0)
    structural_role: str | None = Field(default=None, max_length=128)
    spus: list[BlueprintSPUV0] = Field(default_factory=list)
    vbus: list[BlueprintVBUV0] = Field(default_factory=list)
    bridges: list[BlueprintBridgeV0] = Field(default_factory=list)


class BlueprintV0(BlueprintBaseModel):
    blueprint_version: Literal["blueprint.v0"] = "blueprint.v0"
    blueprint_id: str = Field(min_length=3, max_length=128, pattern=CODE_PATTERN)
    project: BlueprintProjectV0
    reference: BlueprintReferenceV0
    global_constraints: BlueprintGlobalConstraintsV0 = Field(default_factory=BlueprintGlobalConstraintsV0)
    compile_preferences: BlueprintCompilePreferencesV0 = Field(default_factory=BlueprintCompilePreferencesV0)
    sequences: list[BlueprintSequenceV0] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_consistency(self) -> "BlueprintV0":
        sequence_codes: set[str] = set()
        sequence_indexes: set[int] = set()
        spu_codes: set[str] = set()
        vbu_codes: set[str] = set()
        bridge_codes: set[str] = set()
        total_spus = 0

        for sequence in self.sequences:
            if sequence.sequence_code in sequence_codes:
                raise ValueError(f"duplicate_sequence_code:{sequence.sequence_code}")
            sequence_codes.add(sequence.sequence_code)

            if sequence.sequence_index in sequence_indexes:
                raise ValueError(f"duplicate_sequence_index:{sequence.sequence_index}")
            sequence_indexes.add(sequence.sequence_index)

            if not sequence.spus and not sequence.vbus:
                raise ValueError(f"sequence_requires_spu_or_vbu:{sequence.sequence_code}")

            local_spu_codes = {item.spu_code for item in sequence.spus}
            local_vbu_codes = {item.vbu_code for item in sequence.vbus}

            if len(local_spu_codes) != len(sequence.spus):
                raise ValueError(f"duplicate_sequence_spu_code:{sequence.sequence_code}")
            if len(local_vbu_codes) != len(sequence.vbus):
                raise ValueError(f"duplicate_sequence_vbu_code:{sequence.sequence_code}")

            total_spus += len(sequence.spus)

            for spu in sequence.spus:
                if spu.spu_code in spu_codes:
                    raise ValueError(f"duplicate_spu_code:{spu.spu_code}")
                spu_codes.add(spu.spu_code)

            for vbu in sequence.vbus:
                if vbu.vbu_code in vbu_codes:
                    raise ValueError(f"duplicate_vbu_code:{vbu.vbu_code}")
                vbu_codes.add(vbu.vbu_code)

            bridge_orders: set[int] = set()
            for bridge in sequence.bridges:
                if bridge.bridge_code in bridge_codes:
                    raise ValueError(f"duplicate_bridge_code:{bridge.bridge_code}")
                bridge_codes.add(bridge.bridge_code)

                if bridge.execution_order in bridge_orders:
                    raise ValueError(
                        f"duplicate_bridge_execution_order:{sequence.sequence_code}:{bridge.execution_order}"
                    )
                bridge_orders.add(bridge.execution_order)

                if bridge.spu_code and bridge.spu_code not in local_spu_codes:
                    raise ValueError(f"bridge_spu_missing:{bridge.bridge_code}:{bridge.spu_code}")
                if bridge.vbu_code and bridge.vbu_code not in local_vbu_codes:
                    raise ValueError(f"bridge_vbu_missing:{bridge.bridge_code}:{bridge.vbu_code}")

        if total_spus == 0:
            raise ValueError("blueprint_requires_at_least_one_spu")

        if self.reference.reference_beats:
            beat_codes: set[str] = set()
            for beat in self.reference.reference_beats:
                if beat.beat_code in beat_codes:
                    raise ValueError(f"duplicate_reference_beat_code:{beat.beat_code}")
                beat_codes.add(beat.beat_code)
                if beat.sequence_code not in sequence_codes:
                    raise ValueError(f"reference_beat_sequence_missing:{beat.beat_code}:{beat.sequence_code}")

        return self


class BlueprintValidationCountsV0(BlueprintBaseModel):
    sequences: int = Field(ge=0)
    spus: int = Field(ge=0)
    vbus: int = Field(ge=0)
    bridges: int = Field(ge=0)
    reference_beats: int = Field(ge=0)


class BlueprintValidationRead(BlueprintBaseModel):
    blueprint_id: str = Field(min_length=3, max_length=128, pattern=CODE_PATTERN)
    blueprint_version: Literal["blueprint.v0"] = "blueprint.v0"
    is_valid: bool
    counts: BlueprintValidationCountsV0
    requested_runtime_version: str | None = Field(default=None, min_length=1, max_length=128)
    effective_runtime_version: str = Field(min_length=1, max_length=128)
    dispatch_jobs: bool = False


class BlueprintCompilePreviewRead(BlueprintBaseModel):
    blueprint_id: str = Field(min_length=3, max_length=128, pattern=CODE_PATTERN)
    blueprint_version: Literal["blueprint.v0"] = "blueprint.v0"
    runtime_packet: RuntimePacket


__all__ = [
    "BlueprintBridgeV0",
    "BlueprintCompilePreferencesV0",
    "BlueprintCompilePreviewRead",
    "BlueprintGlobalConstraintsV0",
    "BlueprintProjectV0",
    "BlueprintReferenceBeatV0",
    "BlueprintReferenceMappingV0",
    "BlueprintReferenceV0",
    "BlueprintSequenceV0",
    "BlueprintSPUV0",
    "BlueprintV0",
    "BlueprintVBUV0",
    "BlueprintValidationCountsV0",
    "BlueprintValidationRead",
]
