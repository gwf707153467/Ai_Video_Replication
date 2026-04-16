import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SPU(Base):
    __tablename__ = "spus"
    __table_args__ = (
        UniqueConstraint("project_id", "spu_code", name="uq_spus_project_spu_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sequence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="SET NULL"), nullable=True)
    spu_code: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_role: Mapped[str] = mapped_column(String(50), default="primary_visual", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(50), default="veo_segment", nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    negative_prompt_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    visual_constraints: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
