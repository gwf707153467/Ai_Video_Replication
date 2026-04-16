from __future__ import annotations

from sqlalchemy.orm import Session

from app.enums.runtime import AttemptStatus, JobStatus
from app.repositories import (
    JobAttemptRepository,
    RuntimeJobRepository,
    WorkerLeaseRepository,
    WorkerRegistryRepository,
)
from app.schemas.runtime import FailJobRequest, FailJobResult
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError


class RuntimeFailService:
    ACTIVE_ATTEMPT_STATUSES = {
        AttemptStatus.CLAIMED.value,
        AttemptStatus.STARTED.value,
        AttemptStatus.PROVIDER_RUNNING.value,
        AttemptStatus.ARTIFACT_COLLECTING.value,
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

    def fail_job(self, request: FailJobRequest) -> FailJobResult:
        now = self.runtime_jobs.utcnow()

        with self.db.begin():
            try:
                lease = self.worker_leases.get_active_lease_by_claim_token(request.claim_token, for_update=True)
                if lease is None:
                    raise RuntimeLeaseConflictError(
                        f"active lease not found for claim_token={request.claim_token}"
                    )
                self._assert_lease_matches(lease=lease, request=request)

                job = self.runtime_jobs.get_by_job_id(request.job_id, for_update=True)
                if job is None:
                    raise RuntimeStateConflictError(f"job not found: {request.job_id}")
                self._assert_active_claim(job=job, request=request)
                if job.job_status in self.TERMINAL_JOB_STATUSES:
                    raise RuntimeStateConflictError(
                        f"job {job.job_id} already terminal: {job.job_status}"
                    )

                attempt = self.job_attempts.get_attempt_by_attempt_id(request.attempt_id, for_update=True)
                if attempt is None:
                    raise RuntimeStateConflictError(f"attempt not found: {request.attempt_id}")
                self._assert_attempt_matches(attempt=attempt, request=request)
                if attempt.attempt_status not in self.ACTIVE_ATTEMPT_STATUSES:
                    raise RuntimeStateConflictError(
                        f"attempt {attempt.attempt_id} cannot fail from {attempt.attempt_status}"
                    )

                if request.attempt_terminal_status == AttemptStatus.TIMED_OUT.value:
                    attempt = self.job_attempts.mark_timed_out(
                        attempt_id=request.attempt_id,
                        error_code=request.error_code or "ATTEMPT_TIMEOUT",
                        error_message=request.error_message,
                        finished_at=now,
                    )
                elif request.attempt_terminal_status == AttemptStatus.STALE.value:
                    attempt = self.job_attempts.mark_stale(
                        attempt_id=request.attempt_id,
                        error_code=request.error_code or "ATTEMPT_STALE",
                        error_message=request.error_message,
                        error_payload_json=request.error_payload_json,
                        finished_at=now,
                    )
                else:
                    attempt = self.job_attempts.mark_failed(
                        attempt_id=request.attempt_id,
                        error_code=request.error_code,
                        error_message=request.error_message,
                        error_payload_json=request.error_payload_json,
                        finished_at=now,
                    )

                job = self.runtime_jobs.mark_failed(
                    job_id=request.job_id,
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    next_status=request.next_job_status,
                    finished_at=now,
                    terminal_reason_code=request.error_code or request.next_job_status,
                    terminal_reason_message=request.terminal_reason or request.error_message,
                )

                if request.expire_lease:
                    lease = self.worker_leases.expire_lease(
                        claim_token=request.claim_token,
                        expired_at=now,
                    )
                else:
                    lease = self.worker_leases.release_lease(
                        claim_token=request.claim_token,
                        worker_id=request.worker_id,
                        released_at=now,
                    )

                worker = self.worker_registry.decrement_current_job_count(request.worker_id)
                self.worker_registry.mark_seen(request.worker_id, seen_at=now)

                # TODO(runtime-events): append job_events after event repository is available.
                return FailJobResult(
                    job_id=job.job_id,
                    attempt_id=attempt.attempt_id,
                    lease_id=lease.lease_id,
                    job_status=job.job_status,
                    attempt_status=attempt.attempt_status,
                    lease_status=lease.lease_status,
                    worker_id=request.worker_id,
                    current_job_count=worker.current_job_count,
                    finished_at=job.finished_at or attempt.finished_at or now,
                    metadata_json=request.metadata_json,
                )
            except ValueError as exc:
                raise self._map_repository_value_error(exc) from exc

    @staticmethod
    def _assert_lease_matches(*, lease, request: FailJobRequest) -> None:
        if lease.job_id != request.job_id:
            raise RuntimeLeaseConflictError("lease.job_id mismatch")
        if lease.worker_id != request.worker_id:
            raise RuntimeLeaseConflictError("lease.worker_id mismatch")
        if lease.attempt_id != request.attempt_id:
            raise RuntimeLeaseConflictError("lease.attempt_id mismatch")

    @staticmethod
    def _assert_active_claim(*, job, request: FailJobRequest) -> None:
        if job.active_claim_token != request.claim_token:
            raise RuntimeLeaseConflictError("job.active_claim_token mismatch")
        if job.claimed_by_worker_id != request.worker_id:
            raise RuntimeLeaseConflictError("job.claimed_by_worker_id mismatch")

    @staticmethod
    def _assert_attempt_matches(*, attempt, request: FailJobRequest) -> None:
        if attempt.job_id != request.job_id:
            raise RuntimeLeaseConflictError("attempt.job_id mismatch")
        if attempt.claim_token != request.claim_token:
            raise RuntimeLeaseConflictError("attempt.claim_token mismatch")
        if attempt.worker_id != request.worker_id:
            raise RuntimeLeaseConflictError("attempt.worker_id mismatch")

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
            or message == "attempt.job_id mismatch"
        ):
            return RuntimeLeaseConflictError(message)
        return RuntimeStateConflictError(message)
