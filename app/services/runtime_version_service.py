from sqlalchemy.orm import Session

from app.db.models import CompiledRuntime


class RuntimeVersionService:
    def __init__(self, db: Session):
        self.db = db

    def next_version(self, project_id) -> str:
        runtimes = (
            self.db.query(CompiledRuntime)
            .filter(CompiledRuntime.project_id == project_id)
            .order_by(CompiledRuntime.created_at.asc())
            .all()
        )
        return f"v{len(runtimes) + 1}"
