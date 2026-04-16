import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VBU(Base):
    __tablename__ = "vbus"
    __table_args__ = (
        UniqueConstraint("project_id", "vbu_code", name="uq_vbus_project_vbu_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sequence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="SET NULL"), nullable=True)
    vbu_code: Mapped[str] = mapped_column(String(100), nullable=False)
    persuasive_role: Mapped[str] = mapped_column(String(50), default="benefit", nullable=False)
    script_text: Mapped[str] = mapped_column(Text(), nullable=False)
    voice_profile: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="en-US", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
