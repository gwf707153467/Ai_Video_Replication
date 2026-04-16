from sqlalchemy.orm import Session

from app.db.models import CompiledRuntime, Job, Project
from app.schemas.export import ExportCreate


class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def create_export_job(self, payload: ExportCreate) -> Job:
        project = self.db.get(Project, payload.project_id)
        if not project:
            raise ValueError("project_not_found")

        runtime = None
        if payload.runtime_id:
            runtime = self.db.get(CompiledRuntime, payload.runtime_id)
        elif payload.runtime_version:
            runtime = (
                self.db.query(CompiledRuntime)
                .filter(
                    CompiledRuntime.project_id == payload.project_id,
                    CompiledRuntime.runtime_version == payload.runtime_version,
                )
                .order_by(CompiledRuntime.created_at.desc())
                .first()
            )
        else:
            runtime = (
                self.db.query(CompiledRuntime)
                .filter(CompiledRuntime.project_id == payload.project_id)
                .order_by(CompiledRuntime.created_at.desc())
                .first()
            )

        if not runtime:
            raise ValueError("runtime_not_found")

        job = Job(
            project_id=payload.project_id,
            job_type="export",
            status="queued",
            provider_name=payload.provider_name,
            payload={
                "export_type": payload.export_type,
                "export_options": payload.export_options,
                "runtime_id": str(runtime.id),
                "runtime_version": runtime.runtime_version,
            },
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
