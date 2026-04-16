from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from app.enums.runtime import JobStatus
from app.models import RuntimeJob
from app.repositories.base import BaseRepository
from app.schemas.runtime import RuntimeJobCreate


class RuntimeJobRepository(BaseRepository):
    ACTIVE_IDEMPOTENT_STATUSES = {
        JobStatus.CREATED.value,
        JobStatus.QUEUED.value,
        JobStatus.CLAIMED.value,
        JobStatus.RUNNING.value,
        JobStatus.WAITING_RETRY.value,
    }

    CLAIMABLE_STATUSES = (JobStatus.QUEUED.value, JobStatus.WAITING_RETRY.value)
    TERMINAL_STATUSES = {
        JobStatus.SUCCEEDED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
        JobStatus.SUPERSEDED.value,
        JobStatus.STALE.value,
        JobStatus.DEAD_LETTERED.value,
    }

    def create_job(self, payload: RuntimeJobCreate) -> RuntimeJob:
        job = RuntimeJob(**payload.model_dump(exclude_none=True))
        if job.job_status == JobStatus.QUEUED.value and job.queued_at is None:
            job.queued_at = self.utcnow()
        self.db.add(job)
        self.db.flush()
        return job

    def get_by_job_id(self, job_id: str, *, for_update: bool = False) -> RuntimeJob | None:
        stmt = select(RuntimeJob).where(RuntimeJob.job_id == job_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def get_claimable_job_for_update(
        self,
        *,
        queue_name: str | None = None,
        routing_key: str | None = None,
        worker_capability_tags: Sequence[str] | None = None,
        candidate_window: int = 25,
    ) -> RuntimeJob | None:
        stmt = (
            select(RuntimeJob)
            .where(RuntimeJob.job_status.in_(self.CLAIMABLE_STATUSES))
            .where(RuntimeJob.cancel_requested_at.is_(None))
            .order_by(RuntimeJob.priority.desc(), RuntimeJob.created_at.asc())
            .limit(candidate_window)
            .with_for_update(skip_locked=True)
        )

        if queue_name:
            stmt = stmt.where(RuntimeJob.queue_name == queue_name)
        if routing_key:
            stmt = stmt.where(RuntimeJob.routing_key == routing_key)

        candidates = list(self.db.execute(stmt).scalars())
        if not candidates:
            return None
        if not worker_capability_tags:
            return candidates[0]

        capability_set = set(worker_capability_tags)
        for candidate in candidates:
            required = set(candidate.worker_capability_tags_json or [])
            if required.issubset(capability_set):
                return candidate
        return None

    def mark_claimed(
        self,
        *,
        job: RuntimeJob,
        worker_id: str,
        claim_token: str,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> RuntimeJob:
        if job.job_status not in self.CLAIMABLE_STATUSES:
            raise ValueError(f"job {job.job_id} is not claimable: {job.job_status}")

        job.job_status = JobStatus.CLAIMED.value
        job.claimed_by_worker_id = worker_id
        job.active_claim_token = claim_token
        job.claimed_at = claimed_at
        job.lease_expires_at = lease_expires_at
        job.attempt_count += 1
        self.db.flush()
        return job

    def mark_running(
        self,
        *,
        job_id: str,
        claim_token: str,
        worker_id: str,
        started_at: datetime | None = None,
    ) -> RuntimeJob:
        job = self.get_by_job_id(job_id, for_update=True)
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        self._assert_claim_owner(job=job, claim_token=claim_token, worker_id=worker_id)

        if job.job_status not in {JobStatus.CLAIMED.value, JobStatus.RUNNING.value}:
            raise ValueError(f"job {job.job_id} cannot enter RUNNING from {job.job_status}")

        job.job_status = JobStatus.RUNNING.value
        job.started_at = job.started_at or started_at or self.utcnow()
        self.db.flush()
        return job

    def mark_succeeded(
        self,
        *,
        job_id: str,
        claim_token: str,
        worker_id: str,
        finished_at: datetime | None = None,
        terminal_reason_code: str | None = None,
        terminal_reason_message: str | None = None,
    ) -> RuntimeJob:
        job = self.get_by_job_id(job_id, for_update=True)
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        self._assert_claim_owner(job=job, claim_token=claim_token, worker_id=worker_id)

        job.job_status = JobStatus.SUCCEEDED.value
        job.finished_at = finished_at or self.utcnow()
        job.lease_expires_at = None
        job.terminal_reason_code = terminal_reason_code
        job.terminal_reason_message = terminal_reason_message
        self.db.flush()
        return job

    def mark_failed(
        self,
        *,
        job_id: str,
        claim_token: str,
        worker_id: str,
        next_status: str = JobStatus.FAILED.value,
        finished_at: datetime | None = None,
        terminal_reason_code: str | None = None,
        terminal_reason_message: str | None = None,
    ) -> RuntimeJob:
        if next_status not in {JobStatus.FAILED.value, JobStatus.WAITING_RETRY.value, JobStatus.STALE.value}:
            raise ValueError(f"unsupported failure next_status: {next_status}")

        job = self.get_by_job_id(job_id, for_update=True)
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        self._assert_claim_owner(job=job, claim_token=claim_token, worker_id=worker_id)

        job.job_status = next_status
        job.finished_at = finished_at if next_status == JobStatus.FAILED.value else job.finished_at
        job.lease_expires_at = None if next_status == JobStatus.FAILED.value else job.lease_expires_at
        job.terminal_reason_code = terminal_reason_code
        job.terminal_reason_message = terminal_reason_message
        self.db.flush()
        return job

    def mark_cancel_requested(
        self,
        *,
        job_id: str,
        cancel_reason: str | None = None,
        requested_at: datetime | None = None,
    ) -> RuntimeJob:
        job = self.get_by_job_id(job_id, for_update=True)
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        if job.job_status in self.TERMINAL_STATUSES:
            return job

        job.job_status = JobStatus.CANCEL_REQUESTED.value
        job.cancel_requested_at = requested_at or self.utcnow()
        job.cancel_reason = cancel_reason
        self.db.flush()
        return job

    def mark_cancelled(
        self,
        *,
        job_id: str,
        claim_token: str | None = None,
        worker_id: str | None = None,
        finished_at: datetime | None = None,
        terminal_reason_code: str | None = None,
        terminal_reason_message: str | None = None,
    ) -> RuntimeJob:
        job = self.get_by_job_id(job_id, for_update=True)
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        if claim_token and worker_id:
            self._assert_claim_owner(job=job, claim_token=claim_token, worker_id=worker_id)

        job.job_status = JobStatus.CANCELLED.value
        job.finished_at = finished_at or self.utcnow()
        job.lease_expires_at = None
        job.terminal_reason_code = terminal_reason_code
        job.terminal_reason_message = terminal_reason_message
        self.db.flush()
        return job

    def mark_superseded(
        self,
        *,
        job_id: str,
        superseded_by_job_id: str,
        finished_at: datetime | None = None,
        terminal_reason_code: str | None = None,
        terminal_reason_message: str | None = None,
    ) -> RuntimeJob:
        job = self.get_by_job_id(job_id, for_update=True)
        if job is None:
            raise ValueError(f"job not found: {job_id}")

        job.job_status = JobStatus.SUPERSEDED.value
        job.superseded_by_job_id = superseded_by_job_id
        job.finished_at = finished_at or self.utcnow()
        job.lease_expires_at = None
        job.terminal_reason_code = terminal_reason_code
        job.terminal_reason_message = terminal_reason_message
        self.db.flush()
        return job

    @staticmethod
    def _assert_claim_owner(*, job: RuntimeJob, claim_token: str, worker_id: str) -> None:
        if job.active_claim_token != claim_token:
            raise ValueError(f"job {job.job_id} claim_token mismatch")
        if job.claimed_by_worker_id != worker_id:
            raise ValueError(f"job {job.job_id} claimed_by_worker_id mismatch")
