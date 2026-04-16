from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class JobRead(ORMModel):
    id: UUID
    project_id: UUID
    job_type: str
    status: str
    provider_name: str | None = None
    payload: dict
    result_payload: dict | None = None
    attempt_count: int
    max_attempts: int
    external_task_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
