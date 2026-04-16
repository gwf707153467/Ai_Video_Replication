from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.enums.runtime import LeaseStatus
from app.models import WorkerLease
from app.repositories.base import BaseRepository
from app.schemas.runtime import WorkerLeaseCreate


class WorkerLeaseRepository(BaseRepository):
    def create_lease(self, payload: WorkerLeaseCreate) -> WorkerLease:
        lease = WorkerLease(**payload.model_dump(exclude_none=True))
        self.db.add(lease)
        self.db.flush()
        return lease

    def get_active_lease_by_job_id(self, job_id: str, *, for_update: bool = False) -> WorkerLease | None:
        stmt = select(WorkerLease).where(
            WorkerLease.job_id == job_id,
            WorkerLease.lease_status == LeaseStatus.ACTIVE.value,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_lease_by_claim_token(self, claim_token: str, *, for_update: bool = False) -> WorkerLease | None:
        stmt = select(WorkerLease).where(
            WorkerLease.claim_token == claim_token,
            WorkerLease.lease_status == LeaseStatus.ACTIVE.value,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def extend_lease(
        self,
        *,
        claim_token: str,
        worker_id: str,
        lease_expires_at: datetime,
        heartbeat_at: datetime | None = None,
    ) -> WorkerLease:
        lease = self.get_active_lease_by_claim_token(claim_token, for_update=True)
        if lease is None:
            raise ValueError(f"active lease not found for claim_token: {claim_token}")
        if lease.worker_id != worker_id:
            raise ValueError(f"lease {lease.lease_id} worker_id mismatch")
        if lease.extension_count >= lease.max_extensions:
            raise ValueError(f"lease {lease.lease_id} max_extensions exceeded")

        lease.lease_expires_at = lease_expires_at
        lease.last_heartbeat_at = heartbeat_at or self.utcnow()
        lease.heartbeat_count += 1
        lease.extension_count += 1
        self.db.flush()
        return lease

    def release_lease(
        self,
        *,
        claim_token: str,
        worker_id: str,
        released_at: datetime | None = None,
    ) -> WorkerLease:
        lease = self.get_active_lease_by_claim_token(claim_token, for_update=True)
        if lease is None:
            raise ValueError(f"active lease not found for claim_token: {claim_token}")
        if lease.worker_id != worker_id:
            raise ValueError(f"lease {lease.lease_id} worker_id mismatch")

        lease.lease_status = LeaseStatus.RELEASED.value
        lease.last_heartbeat_at = released_at or self.utcnow()
        self.db.flush()
        return lease

    def expire_lease(
        self,
        *,
        claim_token: str,
        expired_at: datetime | None = None,
    ) -> WorkerLease:
        lease = self.get_active_lease_by_claim_token(claim_token, for_update=True)
        if lease is None:
            raise ValueError(f"active lease not found for claim_token: {claim_token}")

        lease.lease_status = LeaseStatus.EXPIRED.value
        lease.lease_expires_at = expired_at or self.utcnow()
        self.db.flush()
        return lease

    def revoke_lease(
        self,
        *,
        claim_token: str,
        revoked_reason: str,
        revoked_at: datetime | None = None,
    ) -> WorkerLease:
        lease = self.get_active_lease_by_claim_token(claim_token, for_update=True)
        if lease is None:
            raise ValueError(f"active lease not found for claim_token: {claim_token}")

        lease.lease_status = LeaseStatus.REVOKED.value
        lease.revoked_at = revoked_at or self.utcnow()
        lease.revoked_reason = revoked_reason
        self.db.flush()
        return lease
