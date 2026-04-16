import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Bridge(Base):
    __tablename__ = "bridges"
    __table_args__ = (
        UniqueConstraint("project_id", "bridge_code", name="uq_bridges_project_bridge_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sequence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False)
    spu_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("spus.id", ondelete="SET NULL"), nullable=True)
    vbu_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vbus.id", ondelete="SET NULL"), nullable=True)
    bridge_code: Mapped[str] = mapped_column(String(100), nullable=False)
    bridge_type: Mapped[str] = mapped_column(String(50), default="sequence_unit_binding", nullable=False)
    execution_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transition_policy: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
