"""add assets table

Revision ID: 20260330_0003
Revises: 20260330_0002
Create Date: 2026-03-30 01:10:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260330_0003"
down_revision = "20260330_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequences.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("asset_role", sa.String(length=50), nullable=False),
        sa.Column("bucket_name", sa.String(length=100), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("asset_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bucket_name", "object_key", name="uq_assets_bucket_object_key"),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_sequence_id", "assets", ["sequence_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])


def downgrade() -> None:
    op.drop_index("ix_assets_asset_type", table_name="assets")
    op.drop_index("ix_assets_sequence_id", table_name="assets")
    op.drop_index("ix_assets_project_id", table_name="assets")
    op.drop_table("assets")
