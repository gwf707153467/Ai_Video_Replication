from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.enums.worker import WorkerHealthStatus
from app.models import WorkerRegistry
from app.repositories.base import BaseRepository
from app.schemas.runtime import WorkerRegistrationUpsert


class WorkerRegistryRepository(BaseRepository):
    def get_by_worker_id(self, worker_id: str, *, for_update: bool = False) -> WorkerRegistry | None:
        stmt = select(WorkerRegistry).where(WorkerRegistry.worker_id == worker_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert_worker_registration(self, payload: WorkerRegistrationUpsert) -> WorkerRegistry:
        now = self.utcnow()
        worker = self.get_by_worker_id(payload.worker_id, for_update=True)
        if worker is None:
            worker = WorkerRegistry(
                worker_id=payload.worker_id,
                worker_type=payload.worker_type,
                hostname=payload.hostname,
                pid=payload.pid,
                version=payload.version,
                capability_tags_json=payload.capability_tags_json,
                queue_bindings_json=payload.queue_bindings_json,
                health_status=payload.health_status,
                max_concurrency=payload.max_concurrency,
                started_at=payload.started_at or now,
                last_seen_at=payload.last_seen_at or now,
                metadata_json=payload.metadata_json,
            )
            self.db.add(worker)
            self.db.flush()
            return worker

        worker.worker_type = payload.worker_type
        worker.hostname = payload.hostname
        worker.pid = payload.pid
        worker.version = payload.version
        worker.capability_tags_json = payload.capability_tags_json
        worker.queue_bindings_json = payload.queue_bindings_json
        worker.health_status = payload.health_status
        worker.max_concurrency = payload.max_concurrency
        worker.last_seen_at = payload.last_seen_at or now
        worker.metadata_json = payload.metadata_json
        if payload.health_status != WorkerHealthStatus.DRAINING.value:
            worker.draining_at = None
        if payload.health_status != WorkerHealthStatus.OFFLINE.value:
            worker.offline_at = None
        self.db.flush()
        return worker

    def mark_seen(self, worker_id: str, *, seen_at: datetime | None = None) -> WorkerRegistry:
        worker = self.get_by_worker_id(worker_id, for_update=True)
        if worker is None:
            raise ValueError(f"worker not found: {worker_id}")
        worker.last_seen_at = seen_at or self.utcnow()
        self.db.flush()
        return worker

    def set_health_status(
        self,
        worker_id: str,
        health_status: str,
        *,
        changed_at: datetime | None = None,
    ) -> WorkerRegistry:
        worker = self.get_by_worker_id(worker_id, for_update=True)
        if worker is None:
            raise ValueError(f"worker not found: {worker_id}")

        at = changed_at or self.utcnow()
        worker.health_status = health_status
        worker.last_seen_at = at
        if health_status == WorkerHealthStatus.DRAINING.value:
            worker.draining_at = at
        elif health_status == WorkerHealthStatus.OFFLINE.value:
            worker.offline_at = at
        self.db.flush()
        return worker

    def increment_current_job_count(self, worker_id: str, *, delta: int = 1) -> WorkerRegistry:
        worker = self.get_by_worker_id(worker_id, for_update=True)
        if worker is None:
            raise ValueError(f"worker not found: {worker_id}")
        worker.current_job_count += delta
        self.db.flush()
        return worker

    def decrement_current_job_count(self, worker_id: str, *, delta: int = 1) -> WorkerRegistry:
        worker = self.get_by_worker_id(worker_id, for_update=True)
        if worker is None:
            raise ValueError(f"worker not found: {worker_id}")
        worker.current_job_count = max(0, worker.current_job_count - delta)
        self.db.flush()
        return worker
