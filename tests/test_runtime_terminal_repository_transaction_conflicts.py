import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.enums.runtime import AttemptStatus, AttemptType, JobStatus, JobType, LeaseStatus
from app.enums.worker import WorkerHealthStatus
from app.models.job_attempt import JobAttempt
from app.models.runtime_job import RuntimeJob
from app.models.worker_lease import WorkerLease
from app.models.worker_registry import WorkerRegistry
from app.schemas.runtime import CompleteJobRequest, FailJobRequest
from app.services.runtime_complete_service import RuntimeCompleteService
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError
from app.services.runtime_fail_service import RuntimeFailService


UTC = timezone.utc


def _resolve_database_url() -> str:
    return (
        os.getenv("RUNTIME_TERMINAL_TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or settings.database_url.replace("@postgres:", "@127.0.0.1:")
    )


class RuntimeTerminalRepositoryTransactionConflictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(_resolve_database_url(), future=True)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False, future=True)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        try:
            self.db.rollback()
            self.db.execute(delete(WorkerLease))
            self.db.execute(delete(JobAttempt))
            self.db.execute(delete(RuntimeJob))
            self.db.execute(delete(WorkerRegistry))
            self.db.commit()
        finally:
            self.db.close()

    def test_complete_job_raises_lease_conflict_when_active_lease_missing(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-missing-lease",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        seeded["lease"].lease_status = LeaseStatus.RELEASED.value
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(
            str(ctx.exception),
            f"active lease not found for claim_token={seeded['lease'].claim_token}",
        )

    def test_complete_job_attempt_claim_token_mismatch_maps_to_lease_conflict(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-attempt-claim-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        seeded["attempt"].claim_token = f"other-{uuid.uuid4().hex[:8]}"
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(str(ctx.exception), "attempt.claim_token mismatch")

    def test_fail_job_attempt_worker_id_mismatch_maps_to_lease_conflict(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-attempt-worker-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        seeded["attempt"].worker_id = f"other-worker-{uuid.uuid4().hex[:8]}"
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), "attempt.worker_id mismatch")

    def test_complete_job_rejects_terminal_job_status(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-terminal-job",
            job_status=JobStatus.SUCCEEDED.value,
            attempt_status=AttemptStatus.STARTED.value,
        )

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeStateConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(
            str(ctx.exception),
            f"job {seeded['job'].job_id} already terminal: {JobStatus.SUCCEEDED.value}",
        )

    def test_fail_job_rejects_terminal_attempt_status(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-terminal-attempt",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.COMPLETED.value,
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeStateConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(
            str(ctx.exception),
            f"attempt {seeded['attempt'].attempt_id} cannot fail from {AttemptStatus.COMPLETED.value}",
        )

    def test_fail_job_rejects_terminal_job_status(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-terminal-job",
            job_status=JobStatus.FAILED.value,
            attempt_status=AttemptStatus.STARTED.value,
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeStateConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(
            str(ctx.exception),
            f"job {seeded['job'].job_id} already terminal: {JobStatus.FAILED.value}",
        )

    def test_complete_job_rejects_attempt_job_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-attempt-job-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        other_job = RuntimeJob(
            job_id=f"job-other-{uuid.uuid4().hex[:8]}",
            job_type=JobType.COMPILE.value,
            job_status=JobStatus.RUNNING.value,
            claimed_by_worker_id=seeded["worker"].worker_id,
            active_claim_token=f"other-claim-{uuid.uuid4().hex[:8]}",
            claimed_at=seeded["job"].claimed_at,
            started_at=seeded["job"].started_at,
            lease_expires_at=seeded["job"].lease_expires_at,
            metadata_json={},
        )
        self.db.add(other_job)
        self.db.flush()
        seeded["attempt"].job_id = other_job.job_id
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(str(ctx.exception), "attempt.job_id mismatch")

    def test_complete_job_raises_state_conflict_when_attempt_missing(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-missing-attempt",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        missing_attempt_id = seeded["attempt"].attempt_id
        self.db.delete(seeded["attempt"])
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=missing_attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeStateConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(str(ctx.exception), f"attempt not found: {missing_attempt_id}")

    def test_complete_job_rejects_non_active_attempt_status(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-created-attempt",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.CREATED.value,
        )

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeStateConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(
            str(ctx.exception),
            f"attempt {seeded['attempt'].attempt_id} cannot complete from {AttemptStatus.CREATED.value}",
        )

    def test_fail_job_raises_state_conflict_when_attempt_missing(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-missing-attempt",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        missing_attempt_id = seeded["attempt"].attempt_id
        self.db.delete(seeded["attempt"])
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=missing_attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeStateConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), f"attempt not found: {missing_attempt_id}")

    def test_complete_job_rejects_lease_attempt_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-lease-attempt-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        seeded["lease"].attempt_id = f"other-attempt-{uuid.uuid4().hex[:8]}"
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(str(ctx.exception), "lease.attempt_id mismatch")

    def test_fail_job_rejects_lease_job_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-lease-job-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        other_job = RuntimeJob(
            job_id=f"job-other-{uuid.uuid4().hex[:8]}",
            job_type=JobType.COMPILE.value,
            job_status=JobStatus.RUNNING.value,
            claimed_by_worker_id=seeded["worker"].worker_id,
            active_claim_token=f"other-claim-{uuid.uuid4().hex[:8]}",
            claimed_at=seeded["job"].claimed_at,
            started_at=seeded["job"].started_at,
            lease_expires_at=seeded["job"].lease_expires_at,
            metadata_json={},
        )
        self.db.add(other_job)
        self.db.flush()
        seeded["lease"].job_id = other_job.job_id
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), "lease.job_id mismatch")

    def test_complete_job_rejects_job_active_claim_token_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-job-claim-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        seeded["job"].active_claim_token = f"other-claim-{uuid.uuid4().hex[:8]}"
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(str(ctx.exception), "job.active_claim_token mismatch")

    def test_fail_job_rejects_job_active_claim_token_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-job-claim-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        seeded["job"].active_claim_token = f"other-claim-{uuid.uuid4().hex[:8]}"
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), "job.active_claim_token mismatch")

    def test_fail_job_rejects_job_claimed_by_worker_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-job-worker-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        other_worker = WorkerRegistry(
            worker_id=f"worker-other-{uuid.uuid4().hex[:8]}",
            worker_type="runtime",
            hostname="localhost",
            health_status=WorkerHealthStatus.HEALTHY.value,
            current_job_count=0,
            max_concurrency=2,
            started_at=seeded["worker"].started_at,
            last_seen_at=seeded["worker"].last_seen_at,
            metadata_json={},
        )
        self.db.add(other_worker)
        self.db.flush()
        seeded["job"].claimed_by_worker_id = other_worker.worker_id
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), "job.claimed_by_worker_id mismatch")

    def test_complete_job_rejects_job_claimed_by_worker_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-job-worker-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        other_worker = WorkerRegistry(
            worker_id=f"worker-other-{uuid.uuid4().hex[:8]}",
            worker_type="runtime",
            hostname="localhost",
            health_status=WorkerHealthStatus.HEALTHY.value,
            current_job_count=0,
            max_concurrency=2,
            started_at=seeded["worker"].started_at,
            last_seen_at=seeded["worker"].last_seen_at,
            metadata_json={},
        )
        self.db.add(other_worker)
        self.db.flush()
        seeded["job"].claimed_by_worker_id = other_worker.worker_id
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(str(ctx.exception), "job.claimed_by_worker_id mismatch")

    def test_fail_job_rejects_lease_worker_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-lease-worker-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        other_worker = WorkerRegistry(
            worker_id=f"worker-other-{uuid.uuid4().hex[:8]}",
            worker_type="runtime",
            hostname="localhost",
            health_status=WorkerHealthStatus.HEALTHY.value,
            current_job_count=0,
            max_concurrency=2,
            started_at=seeded["worker"].started_at,
            last_seen_at=seeded["worker"].last_seen_at,
            metadata_json={},
        )
        self.db.add(other_worker)
        self.db.flush()
        seeded["lease"].worker_id = other_worker.worker_id
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), "lease.worker_id mismatch")

    def test_complete_job_rejects_attempt_worker_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-attempt-worker-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        seeded["attempt"].worker_id = f"other-worker-{uuid.uuid4().hex[:8]}"
        self.db.commit()

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeCompleteService(self.db).complete_job(request)

        self.assertEqual(str(ctx.exception), "attempt.worker_id mismatch")

    def test_fail_job_rejects_attempt_claim_token_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-attempt-claim-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        seeded["attempt"].claim_token = f"other-claim-{uuid.uuid4().hex[:8]}"
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), "attempt.claim_token mismatch")

    def test_fail_job_rejects_attempt_job_id_mismatch(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-attempt-job-mismatch",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
        )
        other_job = RuntimeJob(
            job_id=f"job-other-{uuid.uuid4().hex[:8]}",
            job_type=JobType.COMPILE.value,
            job_status=JobStatus.RUNNING.value,
            claimed_by_worker_id=seeded["worker"].worker_id,
            active_claim_token=f"other-claim-{uuid.uuid4().hex[:8]}",
            claimed_at=seeded["job"].claimed_at,
            started_at=seeded["job"].started_at,
            lease_expires_at=seeded["job"].lease_expires_at,
            metadata_json={},
        )
        self.db.add(other_job)
        self.db.flush()
        seeded["attempt"].job_id = other_job.job_id
        self.db.commit()

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeLeaseConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(str(ctx.exception), "attempt.job_id mismatch")

    def test_fail_job_rejects_non_active_attempt_status(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-created-attempt",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.CREATED.value,
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
        )

        with self.assertRaises(RuntimeStateConflictError) as ctx:
            RuntimeFailService(self.db).fail_job(request)

        self.assertEqual(
            str(ctx.exception),
            f"attempt {seeded['attempt'].attempt_id} cannot fail from {AttemptStatus.CREATED.value}",
        )

    def _seed_active_runtime_graph(
        self,
        *,
        suffix: str,
        job_status: str,
        attempt_status: str,
    ) -> dict[str, object]:
        base_time = datetime(2026, 4, 2, 12, 0, 0, tzinfo=UTC)
        started_at = base_time - timedelta(minutes=5)
        claimed_at = base_time - timedelta(minutes=4)
        lease_expires_at = base_time + timedelta(minutes=5)
        claim_token = f"claim-{suffix}-{uuid.uuid4().hex[:8]}"

        worker = WorkerRegistry(
            worker_id=f"worker-{suffix}-{uuid.uuid4().hex[:8]}",
            worker_type="runtime",
            hostname="localhost",
            health_status=WorkerHealthStatus.HEALTHY.value,
            current_job_count=1,
            max_concurrency=2,
            started_at=base_time - timedelta(hours=1),
            last_seen_at=base_time - timedelta(minutes=10),
            metadata_json={},
        )
        job = RuntimeJob(
            job_id=f"job-{suffix}-{uuid.uuid4().hex[:8]}",
            job_type=JobType.COMPILE.value,
            job_status=job_status,
            claimed_by_worker_id=worker.worker_id,
            active_claim_token=claim_token,
            claimed_at=claimed_at,
            started_at=started_at,
            lease_expires_at=lease_expires_at,
            metadata_json={},
        )
        attempt = JobAttempt(
            attempt_id=f"attempt-{suffix}-{uuid.uuid4().hex[:8]}",
            job_id=job.job_id,
            attempt_index=1,
            attempt_type=AttemptType.PRIMARY.value,
            attempt_status=attempt_status,
            worker_id=worker.worker_id,
            claim_token=claim_token,
            started_at=started_at,
            error_payload_json={},
            metadata_json={},
        )
        lease = WorkerLease(
            lease_id=f"lease-{suffix}-{uuid.uuid4().hex[:8]}",
            job_id=job.job_id,
            attempt_id=attempt.attempt_id,
            worker_id=worker.worker_id,
            claim_token=claim_token,
            lease_status=LeaseStatus.ACTIVE.value,
            lease_started_at=claimed_at,
            lease_expires_at=lease_expires_at,
            last_heartbeat_at=claimed_at,
            metadata_json={},
        )

        self.db.add(worker)
        self.db.add(job)
        self.db.flush()
        self.db.add(attempt)
        self.db.add(lease)
        self.db.commit()

        return {"worker": worker, "job": job, "attempt": attempt, "lease": lease}


if __name__ == "__main__":
    unittest.main()
