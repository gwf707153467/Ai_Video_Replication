import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompiledRuntime(Base):
    __tablename__ = "compiled_runtimes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    runtime_version: Mapped[str] = mapped_column(String(50), nullable=False)
    compile_status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    runtime_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dispatch_status: Mapped[str] = mapped_column(String(50), default="not_dispatched", nullable=False)
    dispatch_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    compile_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    compile_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
