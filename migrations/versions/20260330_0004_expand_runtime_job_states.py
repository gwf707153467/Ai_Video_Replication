"""expand runtime and job states

Revision ID: 20260330_0004
Revises: 20260330_0003
Create Date: 2026-03-30 02:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260330_0004"
down_revision = "20260330_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jobs", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("jobs", sa.Column("external_task_id", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("error_code", sa.String(length=100), nullable=True))
    op.add_column("jobs", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column(
        "compiled_runtimes",
        sa.Column("dispatch_status", sa.String(length=50), nullable=False, server_default="not_dispatched"),
    )
    op.add_column(
        "compiled_runtimes",
        sa.Column(
            "dispatch_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("compiled_runtimes", sa.Column("last_error_code", sa.String(length=100), nullable=True))
    op.add_column("compiled_runtimes", sa.Column("last_error_message", sa.Text(), nullable=True))
    op.add_column("compiled_runtimes", sa.Column("compile_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("compiled_runtimes", sa.Column("compile_finished_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE jobs SET attempt_count = 0, max_attempts = 3")
    op.execute("UPDATE compiled_runtimes SET dispatch_status = 'not_dispatched', dispatch_summary = '{}'::jsonb")

    op.alter_column("jobs", "attempt_count", server_default=None)
    op.alter_column("jobs", "max_attempts", server_default=None)
    op.alter_column("compiled_runtimes", "dispatch_status", server_default=None)
    op.alter_column("compiled_runtimes", "dispatch_summary", server_default=None)


def downgrade() -> None:
    op.drop_column("compiled_runtimes", "compile_finished_at")
    op.drop_column("compiled_runtimes", "compile_started_at")
    op.drop_column("compiled_runtimes", "last_error_message")
    op.drop_column("compiled_runtimes", "last_error_code")
    op.drop_column("compiled_runtimes", "dispatch_summary")
    op.drop_column("compiled_runtimes", "dispatch_status")

    op.drop_column("jobs", "finished_at")
    op.drop_column("jobs", "started_at")
    op.drop_column("jobs", "error_message")
    op.drop_column("jobs", "error_code")
    op.drop_column("jobs", "external_task_id")
    op.drop_column("jobs", "max_attempts")
    op.drop_column("jobs", "attempt_count")
