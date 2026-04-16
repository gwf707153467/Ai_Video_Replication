from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedUpdatedMixin, UUIDPrimaryKeyMixin
from app.enums.runtime import LeaseStatus
from app.models._public_ids import generate_public_id


class WorkerLease(UUIDPrimaryKeyMixin, CreatedUpdatedMixin, Base):
    __tablename__ = "worker_leases"
    __table_args__ = (
        UniqueConstraint("lease_id", name="uq_worker_leases_lease_id"),
        UniqueConstraint("claim_token", name="uq_worker_leases_claim_token"),
        CheckConstraint("heartbeat_count >= 0", name="heartbeat_count_non_negative"),
        CheckConstraint("extension_count >= 0", name="extension_count_non_negative"),
        CheckConstraint("max_extensions >= 0", name="max_extensions_non_negative"),
    )

    lease_id: Mapped[str] = mapped_column(String(64), nullable=False, default=lambda: generate_public_id("les"))
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("runtime_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worker_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("worker_registry.worker_id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_token: Mapped[str] = mapped_column(String(64), nullable=False)

    lease_status: Mapped[str] = mapped_column(String(50), nullable=False, default=LeaseStatus.ACTIVE.value)

    lease_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    heartbeat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extension_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_extensions: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
