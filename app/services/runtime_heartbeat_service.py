from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.enums.runtime import AttemptStatus, JobStatus
from app.repositories import (
    JobAttemptRepository,
    RuntimeJobRepository,
    WorkerLeaseRepository,
    WorkerRegistryRepository,
)
from app.schemas.runtime import HeartbeatRequest, HeartbeatResult
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError


class RuntimeHeartbeatService:
    """Heartbeat / lease extend 骨架。"""

    HEARTBEAT_STARTABLE_ATTEMPT_STATUSES = {
        AttemptStatus.CLAIMED.value,
        AttemptStatus.STARTED.value,
    }
    TERMINAL_JOB_STATUSES = {
        JobStatus.SUCCEEDED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
        JobStatus.SUPERSEDED.value,
        JobStatus.STALE.value,
        JobStatus.DEAD_LETTERED.value,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.runtime_jobs = RuntimeJobRepository(db)
        self.job_attempts = JobAttemptRepository(db)
        self.worker_leases = WorkerLeaseRepository(db)
        self.worker_registry = WorkerRegistryRepository(db)

    def heartbeat(self, request: HeartbeatRequest) -> HeartbeatResult:
        now = self.runtime_jobs.utcnow()

        with self.db.begin():
            try:
                lease = self.worker_leases.get_active_lease_by_claim_token(request.claim_token, for_update=True)
                if lease is None:
                    raise RuntimeLeaseConflictError(
                        f"active lease not found for claim_token={request.claim_token}"
                    )
                if lease.job_id != request.job_id:
                    raise RuntimeLeaseConflictError("lease.job_id mismatch")
                if lease.worker_id != request.worker_id:
                    raise RuntimeLeaseConflictError("lease.worker_id mismatch")
                if request.attempt_id and lease.attempt_id and lease.attempt_id != request.attempt_id:
                    raise RuntimeLeaseConflictError("lease.attempt_id mismatch")
                if lease.lease_expires_at <= now:
                    raise RuntimeLeaseConflictError("lease already expired before heartbeat")

                job = self.runtime_jobs.get_by_job_id(request.job_id, for_update=True)
                if job is None:
                    raise RuntimeStateConflictError(f"job not found: {request.job_id}")
                self._assert_active_claim(job=job, request=request)
                if job.job_status in self.TERMINAL_JOB_STATUSES:
                    raise RuntimeStateConflictError(f"job {job.job_id} already terminal: {job.job_status}")

                next_lease_expires_at = now + timedelta(
                    seconds=request.lease_timeout_seconds_override or job.lease_timeout_seconds
                )
                lease = self.worker_leases.extend_lease(
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    lease_expires_at=next_lease_expires_at,
                    heartbeat_at=now,
                )

                attempt_status = None
                if request.mark_job_running:
                    job = self.runtime_jobs.mark_running(
                        job_id=request.job_id,
                        claim_token=request.claim_token,
                        worker_id=request.worker_id,
                        started_at=now,
                    )
                    if request.attempt_id:
                        attempt = self.job_attempts.get_attempt_by_attempt_id(
                            request.attempt_id,
                            for_update=True,
                        )
                        if attempt is None:
                            raise RuntimeStateConflictError(f"attempt not found: {request.attempt_id}")
                        if attempt.claim_token != request.claim_token:
                            raise RuntimeLeaseConflictError("attempt.claim_token mismatch")
                        if attempt.worker_id != request.worker_id:
                            raise RuntimeLeaseConflictError("attempt.worker_id mismatch")
                        if attempt.attempt_status not in self.HEARTBEAT_STARTABLE_ATTEMPT_STATUSES:
                            raise RuntimeStateConflictError(
                                f"attempt {attempt.attempt_id} cannot enter STARTED from {attempt.attempt_status}"
                            )
                        attempt = self.job_attempts.mark_started(
                            attempt_id=request.attempt_id,
                            claim_token=request.claim_token,
                            worker_id=request.worker_id,
                            started_at=now,
                        )
                        attempt_status = attempt.attempt_status
                    else:
                        attempt_status = AttemptStatus.STARTED.value
                elif request.attempt_id:
                    attempt = self.job_attempts.get_attempt_by_attempt_id(request.attempt_id, for_update=True)
                    if attempt is None:
                        raise RuntimeLeaseConflictError(f"attempt not found: {request.attempt_id}")
                    if attempt.claim_token != request.claim_token:
                        raise RuntimeLeaseConflictError("attempt.claim_token mismatch")
                    if attempt.worker_id != request.worker_id:
                        raise RuntimeLeaseConflictError("attempt.worker_id mismatch")
                    attempt_status = attempt.attempt_status

                self.worker_registry.mark_seen(request.worker_id, seen_at=now)

                return HeartbeatResult(
                    job_id=job.job_id,
                    lease_id=lease.lease_id,
                    claim_token=lease.claim_token,
                    job_status=job.job_status,
                    lease_status=lease.lease_status,
                    attempt_status=attempt_status,
                    heartbeat_count=lease.heartbeat_count,
                    extension_count=lease.extension_count,
                    lease_expires_at=lease.lease_expires_at,
                )
            except ValueError as exc:
                raise self._map_repository_value_error(exc) from exc

    @staticmethod
    def _assert_active_claim(*, job, request: HeartbeatRequest) -> None:
        if job.active_claim_token != request.claim_token:
            raise RuntimeLeaseConflictError("job.active_claim_token mismatch")
        if job.claimed_by_worker_id != request.worker_id:
            raise RuntimeLeaseConflictError("job.claimed_by_worker_id mismatch")

    @staticmethod
    def _map_repository_value_error(exc: ValueError) -> RuntimeLeaseConflictError | RuntimeStateConflictError:
        message = str(exc)
        if (
            message.startswith("active lease not found")
            or message.startswith("lease ")
            or "claim_token mismatch" in message
            or "claimed_by_worker_id mismatch" in message
            or "worker_id mismatch" in message
            or message == "lease.job_id mismatch"
            or message == "lease.worker_id mismatch"
            or message == "lease.attempt_id mismatch"
            or message == "lease already expired before heartbeat"
        ):
            return RuntimeLeaseConflictError(message)
        return RuntimeStateConflictError(message)
