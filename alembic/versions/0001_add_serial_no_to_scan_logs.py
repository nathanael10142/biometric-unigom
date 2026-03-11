

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Add serial_no column if missing ────────────────────────────────────
    result = conn.execute(
        sa.text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'scan_logs' AND column_name = 'serial_no'
            """
        )
    )
    if result.fetchone() is None:
        op.add_column(
            "scan_logs",
            sa.Column("serial_no", sa.Integer(), nullable=True),
        )

    # ── 2. Add partial unique index if missing ────────────────────────────────
    result2 = conn.execute(
        sa.text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'scan_logs'
              AND indexname = 'ix_scan_serial_no_unique'
            """
        )
    )
    if result2.fetchone() is None:
        op.create_index(
            "ix_scan_serial_no_unique",
            "scan_logs",
            ["serial_no"],
            unique=True,
            postgresql_where=sa.text("serial_no IS NOT NULL"),
        )


def downgrade() -> None:
    op.drop_index("ix_scan_serial_no_unique", table_name="scan_logs")
    op.drop_column("scan_logs", "serial_no")
