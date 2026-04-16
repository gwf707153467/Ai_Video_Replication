"""add spus vbus bridges

Revision ID: 20260330_0002
Revises: 20260330_0001
Create Date: 2026-03-30 00:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260330_0002"
down_revision = "20260330_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequences.id", ondelete="SET NULL"), nullable=True),
        sa.Column("spu_code", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("asset_role", sa.String(length=50), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("generation_mode", sa.String(length=50), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("negative_prompt_text", sa.Text(), nullable=True),
        sa.Column("visual_constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "spu_code", name="uq_spus_project_spu_code"),
    )
    op.create_index("ix_spus_project_id", "spus", ["project_id"])
    op.create_index("ix_spus_sequence_id", "spus", ["sequence_id"])

    op.create_table(
        "vbus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequences.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vbu_code", sa.String(length=100), nullable=False),
        sa.Column("persuasive_role", sa.String(length=50), nullable=False),
        sa.Column("script_text", sa.Text(), nullable=False),
        sa.Column("voice_profile", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tts_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "vbu_code", name="uq_vbus_project_vbu_code"),
    )
    op.create_index("ix_vbus_project_id", "vbus", ["project_id"])
    op.create_index("ix_vbus_sequence_id", "vbus", ["sequence_id"])

    op.create_table(
        "bridges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spu_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("spus.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vbu_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vbus.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bridge_code", sa.String(length=100), nullable=False),
        sa.Column("bridge_type", sa.String(length=50), nullable=False),
        sa.Column("execution_order", sa.Integer(), nullable=False),
        sa.Column("transition_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "bridge_code", name="uq_bridges_project_bridge_code"),
    )
    op.create_index("ix_bridges_project_id", "bridges", ["project_id"])
    op.create_index("ix_bridges_sequence_id", "bridges", ["sequence_id"])
    op.create_index("ix_bridges_spu_id", "bridges", ["spu_id"])
    op.create_index("ix_bridges_vbu_id", "bridges", ["vbu_id"])


def downgrade() -> None:
    op.drop_index("ix_bridges_vbu_id", table_name="bridges")
    op.drop_index("ix_bridges_spu_id", table_name="bridges")
    op.drop_index("ix_bridges_sequence_id", table_name="bridges")
    op.drop_index("ix_bridges_project_id", table_name="bridges")
    op.drop_table("bridges")
    op.drop_index("ix_vbus_sequence_id", table_name="vbus")
    op.drop_index("ix_vbus_project_id", table_name="vbus")
    op.drop_table("vbus")
    op.drop_index("ix_spus_sequence_id", table_name="spus")
    op.drop_index("ix_spus_project_id", table_name="spus")
    op.drop_table("spus")
