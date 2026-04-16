from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedUpdatedMixin, UUIDPrimaryKeyMixin
from app.enums.worker import WorkerHealthStatus
from app.models._public_ids import generate_public_id


class WorkerRegistry(UUIDPrimaryKeyMixin, CreatedUpdatedMixin, Base):
    __tablename__ = "worker_registry"
    __table_args__ = (
        UniqueConstraint("worker_id", name="uq_worker_registry_worker_id"),
        CheckConstraint("current_job_count >= 0", name="current_job_count_non_negative"),
        CheckConstraint("max_concurrency >= 1", name="max_concurrency_positive"),
    )

    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, default=lambda: generate_public_id("wrk"))
    worker_type: Mapped[str] = mapped_column(String(50), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    capability_tags_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    queue_bindings_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    health_status: Mapped[str] = mapped_column(String(50), nullable=False, default=WorkerHealthStatus.STARTING.value)
    current_job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    draining_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
