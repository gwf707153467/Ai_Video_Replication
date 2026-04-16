from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.enums.runtime import AttemptStatus, AttemptType, JobStatus, LeaseStatus
from app.enums.worker import WorkerHealthStatus


class RuntimeJobCreate(BaseModel):
    job_id: str | None = None
    job_type: str
    job_status: str = JobStatus.CREATED.value
    project_id: UUID | None = None
    workflow_run_id: str | None = None
    segment_id: str | None = None
    execution_unit_id: str | None = None
    compile_ref: str | None = None
    validator_ref: str | None = None
    parent_job_id: str | None = None
    superseded_by_job_id: str | None = None
    retry_ticket_ref: str | None = None
    priority: int = 100
    queue_name: str = "default"
    routing_key: str | None = None
    worker_capability_tags_json: list[str] = Field(default_factory=list)
    source_type: str | None = None
    source_ref: str | None = None
    max_attempts: int = 3
    max_infra_reruns: int = 1
    lease_timeout_seconds: int = 300
    heartbeat_interval_seconds: int = 30
    stale_after_seconds: int = 600
    queued_at: datetime | None = None
    idempotency_key: str | None = None
    request_hash: str | None = None
    trace_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class JobAttemptCreate(BaseModel):
    attempt_id: str | None = None
    job_id: str
    attempt_index: int
    attempt_type: str = AttemptType.PRIMARY.value
    attempt_status: str = AttemptStatus.CREATED.value
    worker_id: str | None = None
    claim_token: str | None = None
    provider_name: str | None = None
    provider_model: str | None = None
    provider_run_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    completion_status: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_payload_json: dict[str, Any] = Field(default_factory=dict)
    result_ref: str | None = None
    manifest_artifact_id: str | None = None
    queue_wait_ms: int | None = None
    runtime_ms: int | None = None
    provider_runtime_ms: int | None = None
    upload_ms: int | None = None
    cost_estimate: Decimal | None = None
    credit_usage: Decimal | None = None
    metrics_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkerRegistrationUpsert(BaseModel):
    worker_id: str
    worker_type: str
    hostname: str
    pid: int | None = None
    version: str | None = None
    capability_tags_json: list[str] = Field(default_factory=list)
    queue_bindings_json: list[str] = Field(default_factory=list)
    health_status: str = WorkerHealthStatus.HEALTHY.value
    max_concurrency: int = 1
    started_at: datetime | None = None
    last_seen_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkerLeaseCreate(BaseModel):
    lease_id: str | None = None
    job_id: str
    attempt_id: str | None = None
    worker_id: str
    claim_token: str
    lease_status: str = LeaseStatus.ACTIVE.value
    lease_started_at: datetime
    lease_expires_at: datetime
    last_heartbeat_at: datetime | None = None
    heartbeat_count: int = 0
    extension_count: int = 0
    max_extensions: int = 100
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClaimJobRequest(BaseModel):
    worker_id: str
    worker_type: str
    hostname: str
    pid: int | None = None
    version: str | None = None
    queue_name: str | None = None
    routing_key: str | None = None
    worker_capability_tags: list[str] = Field(default_factory=list)
    queue_bindings: list[str] = Field(default_factory=list)
    max_concurrency: int = 1
    lease_timeout_seconds_override: int | None = None
    lease_max_extensions: int = 100
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClaimJobResult(BaseModel):
    job_id: str
    attempt_id: str
    lease_id: str
    claim_token: str
    job_status: str
    attempt_status: str
    lease_status: str
    queue_name: str
    priority: int
    attempt_index: int
    lease_expires_at: datetime


class HeartbeatRequest(BaseModel):
    job_id: str
    worker_id: str
    claim_token: str
    attempt_id: str | None = None
    mark_job_running: bool = False
    lease_timeout_seconds_override: int | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class HeartbeatResult(BaseModel):
    job_id: str
    lease_id: str
    claim_token: str
    job_status: str
    lease_status: str
    attempt_status: str | None = None
    heartbeat_count: int
    extension_count: int
    lease_expires_at: datetime


class CompleteJobRequest(BaseModel):
    job_id: str
    attempt_id: str
    worker_id: str
    claim_token: str
    completion_status: str | None = None
    terminal_reason: str | None = None
    result_ref: str | None = None
    manifest_artifact_id: UUID | str | None = None
    runtime_ms: int | None = None
    provider_runtime_ms: int | None = None
    upload_ms: int | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CompleteJobResult(BaseModel):
    job_id: str
    attempt_id: str
    lease_id: str
    job_status: str
    attempt_status: str
    lease_status: str
    worker_id: str
    current_job_count: int
    finished_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FailJobRequest(BaseModel):
    ALLOWED_NEXT_JOB_STATUSES: ClassVar[set[str]] = {
        JobStatus.FAILED.value,
        JobStatus.WAITING_RETRY.value,
        JobStatus.STALE.value,
    }
    ALLOWED_ATTEMPT_TERMINAL_STATUSES: ClassVar[set[str]] = {
        AttemptStatus.FAILED.value,
        AttemptStatus.TIMED_OUT.value,
        AttemptStatus.STALE.value,
    }

    job_id: str
    attempt_id: str
    worker_id: str
    claim_token: str
    next_job_status: str
    attempt_terminal_status: str
    terminal_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_payload_json: dict[str, Any] = Field(default_factory=dict)
    expire_lease: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("next_job_status")
    @classmethod
    def validate_next_job_status(cls, value: str) -> str:
        if value not in cls.ALLOWED_NEXT_JOB_STATUSES:
            raise ValueError(f"unsupported next_job_status: {value}")
        return value

    @field_validator("attempt_terminal_status")
    @classmethod
    def validate_attempt_terminal_status(cls, value: str) -> str:
        if value not in cls.ALLOWED_ATTEMPT_TERMINAL_STATUSES:
            raise ValueError(f"unsupported attempt_terminal_status: {value}")
        return value


class FailJobResult(BaseModel):
    job_id: str
    attempt_id: str
    lease_id: str
    job_status: str
    attempt_status: str
    lease_status: str
    worker_id: str
    current_job_count: int
    finished_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RuntimeJobTerminalAttemptView(BaseModel):
    attempt_id: str
    attempt_status: str
    attempt_index: int
    worker_id: str | None = None
    claim_token: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    completion_status: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_payload_json: dict[str, Any] = Field(default_factory=dict)
    result_ref: str | None = None
    manifest_artifact_id: str | None = None
    runtime_ms: int | None = None
    provider_runtime_ms: int | None = None
    upload_ms: int | None = None
    metrics_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RuntimeJobTerminalLeaseView(BaseModel):
    lease_id: str
    job_id: str
    attempt_id: str | None = None
    worker_id: str
    claim_token: str
    lease_status: str
    lease_started_at: datetime
    lease_expires_at: datetime
    last_heartbeat_at: datetime | None = None
    heartbeat_count: int = 0
    extension_count: int = 0
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RuntimeJobTerminalView(BaseModel):
    job_id: str
    job_status: str
    claimed_by_worker_id: str | None = None
    active_claim_token: str | None = None
    attempt_count: int
    queued_at: datetime | None = None
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    lease_expires_at: datetime | None = None
    terminal_reason_code: str | None = None
    terminal_reason_message: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    latest_attempt: RuntimeJobTerminalAttemptView | None = None
    active_lease: RuntimeJobTerminalLeaseView | None = None


class RuntimeTerminalErrorResponse(BaseModel):
    detail: str
    error_type: str
    job_id: str | None = None
    attempt_id: str | None = None
    worker_id: str | None = None
    claim_token: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
