from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.enums.runtime import AttemptStatus, AttemptType
from app.enums.worker import WorkerHealthStatus
from app.repositories import (
    JobAttemptRepository,
    RuntimeJobRepository,
    WorkerLeaseRepository,
    WorkerRegistryRepository,
)
from app.schemas.runtime import (
    ClaimJobRequest,
    ClaimJobResult,
    JobAttemptCreate,
    WorkerLeaseCreate,
    WorkerRegistrationUpsert,
)
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError


class RuntimeClaimService:
    BLOCKED_HEALTH_STATUSES = {
        WorkerHealthStatus.DRAINING.value,
        WorkerHealthStatus.OFFLINE.value,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.runtime_jobs = RuntimeJobRepository(db)
        self.job_attempts = JobAttemptRepository(db)
        self.worker_leases = WorkerLeaseRepository(db)
        self.worker_registry = WorkerRegistryRepository(db)

    def claim_job(self, request: ClaimJobRequest) -> ClaimJobResult | None:
        now = self.runtime_jobs.utcnow()

        with self.db.begin():
            try:
                existing_worker = self.worker_registry.get_by_worker_id(request.worker_id, for_update=True)
                worker = self.worker_registry.upsert_worker_registration(
                    WorkerRegistrationUpsert(
                        worker_id=request.worker_id,
                        worker_type=request.worker_type,
                        hostname=request.hostname,
                        pid=request.pid,
                        version=request.version,
                        capability_tags_json=request.worker_capability_tags,
                        queue_bindings_json=request.queue_bindings,
                        health_status=(
                            existing_worker.health_status
                            if existing_worker is not None
                            else WorkerHealthStatus.HEALTHY.value
                        ),
                        max_concurrency=request.max_concurrency,
                        last_seen_at=now,
                        metadata_json=request.metadata_json,
                    )
                )
                self._assert_worker_claimable(worker)

                job = self.runtime_jobs.get_claimable_job_for_update(
                    queue_name=request.queue_name,
                    routing_key=request.routing_key,
                    worker_capability_tags=request.worker_capability_tags,
                )
                if job is None:
                    self.worker_registry.mark_seen(request.worker_id, seen_at=now)
                    return None

                claim_token = str(uuid4())
                lease_expires_at = now + timedelta(
                    seconds=request.lease_timeout_seconds_override or job.lease_timeout_seconds
                )
                job = self.runtime_jobs.mark_claimed(
                    job=job,
                    worker_id=request.worker_id,
                    claim_token=claim_token,
                    claimed_at=now,
                    lease_expires_at=lease_expires_at,
                )
                attempt = self.job_attempts.create_attempt(
                    JobAttemptCreate(
                        job_id=job.job_id,
                        attempt_index=job.attempt_count,
                        attempt_type=self._derive_attempt_type(job),
                        attempt_status=AttemptStatus.CLAIMED.value,
                        worker_id=request.worker_id,
                        claim_token=claim_token,
                        queue_wait_ms=self._derive_queue_wait_ms(job, now),
                        metadata_json=request.metadata_json,
                    )
                )
                lease = self.worker_leases.create_lease(
                    WorkerLeaseCreate(
                        job_id=job.job_id,
                        attempt_id=attempt.attempt_id,
                        worker_id=request.worker_id,
                        claim_token=claim_token,
                        lease_started_at=now,
                        lease_expires_at=lease_expires_at,
                        max_extensions=request.lease_max_extensions,
                        metadata_json=request.metadata_json,
                    )
                )
                worker = self.worker_registry.increment_current_job_count(request.worker_id)
                self.worker_registry.mark_seen(request.worker_id, seen_at=now)

                return ClaimJobResult(
                    job_id=job.job_id,
                    attempt_id=attempt.attempt_id,
                    lease_id=lease.lease_id,
                    claim_token=claim_token,
                    job_status=job.job_status,
                    attempt_status=attempt.attempt_status,
                    lease_status=lease.lease_status,
                    queue_name=job.queue_name,
                    priority=job.priority,
                    attempt_index=attempt.attempt_index,
                    lease_expires_at=lease.lease_expires_at,
                )
            except ValueError as exc:
                raise self._map_repository_value_error(exc) from exc

    def _assert_worker_claimable(self, worker) -> None:
        if worker.health_status in self.BLOCKED_HEALTH_STATUSES:
            raise RuntimeStateConflictError(
                f"worker {worker.worker_id} health_status does not allow claim: {worker.health_status}"
            )
        if worker.current_job_count >= worker.max_concurrency:
            raise RuntimeStateConflictError(
                f"worker {worker.worker_id} has no remaining capacity: "
                f"{worker.current_job_count}/{worker.max_concurrency}"
            )

    @staticmethod
    def _derive_attempt_type(job) -> str:
        return AttemptType.PRIMARY.value if job.attempt_count <= 1 else AttemptType.RETRY.value

    @staticmethod
    def _derive_queue_wait_ms(job, now) -> int | None:
        queued_at = job.queued_at or job.created_at
        if queued_at is None:
            return None
        return max(0, int((now - queued_at).total_seconds() * 1000))

    @staticmethod
    def _map_repository_value_error(exc: ValueError) -> RuntimeLeaseConflictError | RuntimeStateConflictError:
        message = str(exc)
        if "claim_token mismatch" in message or "claimed_by_worker_id mismatch" in message:
            return RuntimeLeaseConflictError(message)
        return RuntimeStateConflictError(message)
