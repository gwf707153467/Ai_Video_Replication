from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedUpdatedMixin, UUIDPrimaryKeyMixin
from app.enums.runtime import JobStatus
from app.models._public_ids import generate_public_id


class RuntimeJob(UUIDPrimaryKeyMixin, CreatedUpdatedMixin, Base):
    __tablename__ = "runtime_jobs"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_runtime_jobs_job_id"),
        CheckConstraint("priority >= 0", name="priority_non_negative"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        CheckConstraint("infra_rerun_count >= 0", name="infra_rerun_count_non_negative"),
        CheckConstraint("max_attempts >= 1", name="max_attempts_positive"),
        CheckConstraint("max_infra_reruns >= 0", name="max_infra_reruns_non_negative"),
        CheckConstraint("lease_timeout_seconds >= 1", name="lease_timeout_positive"),
        CheckConstraint("heartbeat_interval_seconds >= 1", name="heartbeat_interval_positive"),
        CheckConstraint("stale_after_seconds >= 1", name="stale_after_positive"),
    )

    job_id: Mapped[str] = mapped_column(String(64), nullable=False, default=lambda: generate_public_id("job"))
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    job_status: Mapped[str] = mapped_column(String(50), nullable=False, default=JobStatus.CREATED.value)

    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    segment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_unit_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    compile_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validator_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    parent_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    superseded_by_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_ticket_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    queue_name: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    routing_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    worker_capability_tags_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    claimed_by_worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_claim_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    infra_rerun_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_infra_reruns: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    lease_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    stale_after_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=600)

    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    terminal_reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    terminal_reason_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
