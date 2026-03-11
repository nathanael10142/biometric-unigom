"""add sync_cursors table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-10

Creates the sync_cursors table which stores the dual-cursor state for the
Hikvision ISAPI incremental sync:
  • last_position — searchResultPosition to resume from on the next sync
  • last_serial   — highest serialNo processed (deduplication safety net)
"""

from alembic import op
import sqlalchemy as sa

revision      = "0002"
down_revision = "0001"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    conn = op.get_bind()

    # Only create if the table does not already exist
    result = conn.execute(
        sa.text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = 'sync_cursors'
            """
        )
    )
    if result.fetchone() is not None:
        return  # already exists — nothing to do

    op.create_table(
        "sync_cursors",
        sa.Column("id",            sa.Integer(),     nullable=False, primary_key=True),
        sa.Column("key",           sa.String(50),    nullable=False, unique=True),
        sa.Column("last_position", sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("last_serial",   sa.Integer(),     nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_sync_cursors_key", "sync_cursors", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sync_cursors_key", table_name="sync_cursors")
    op.drop_table("sync_cursors")
