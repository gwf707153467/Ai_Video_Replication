from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedUpdatedMixin, UUIDPrimaryKeyMixin
from app.enums.runtime import AttemptStatus
from app.models._public_ids import generate_public_id


class JobAttempt(UUIDPrimaryKeyMixin, CreatedUpdatedMixin, Base):
    __tablename__ = "job_attempts"
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_job_attempts_attempt_id"),
        UniqueConstraint("job_id", "attempt_index", name="uq_job_attempts_job_id_attempt_index"),
        CheckConstraint("attempt_index >= 1", name="attempt_index_positive"),
        CheckConstraint("queue_wait_ms >= 0", name="queue_wait_non_negative"),
        CheckConstraint("runtime_ms >= 0", name="runtime_non_negative"),
        CheckConstraint("provider_runtime_ms >= 0", name="provider_runtime_non_negative"),
        CheckConstraint("upload_ms >= 0", name="upload_non_negative"),
        CheckConstraint("cost_estimate >= 0", name="cost_estimate_non_negative"),
        CheckConstraint("credit_usage >= 0", name="credit_usage_non_negative"),
    )

    attempt_id: Mapped[str] = mapped_column(String(64), nullable=False, default=lambda: generate_public_id("att"))
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("runtime_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_index: Mapped[int] = mapped_column(Integer, nullable=False)

    attempt_type: Mapped[str] = mapped_column(String(50), nullable=False)
    attempt_status: Mapped[str] = mapped_column(String(50), nullable=False, default=AttemptStatus.CREATED.value)

    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claim_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    completion_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    result_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manifest_artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    queue_wait_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    cost_estimate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    credit_usage: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)

    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
