"""
Presence DB initial schema — dual-database migration

Creates the following tables in rhunigom_presence:
  - agent_cache      (local snapshot of prod agents)
  - attendances      (daily attendance records, references agent_cache.uuid)
  - scan_logs        (raw Hikvision events, references agent_cache.uuid)
  - sync_cursors     (Hikvision pagination cursor)
  - login_attempts   (brute-force lockout, keyed by email)

Revision ID: b4e8f3d2c961
Revises: (none — fresh presence DB)
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa

revision = "b4e8f3d2c961"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agent_cache ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_cache",
        sa.Column("uuid", sa.String(36), primary_key=True),
        sa.Column("matricule", sa.String(20), nullable=False, server_default="NU"),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=False),
        sa.Column("position", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("telephone", sa.String(50), nullable=True),
        sa.Column("biometric_id", sa.String(50), nullable=True, unique=True),
        sa.Column("statut", sa.String(50), nullable=False, server_default="actif"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_cache_biometric_id", "agent_cache", ["biometric_id"])
    op.create_index("ix_agent_cache_is_active", "agent_cache", ["is_active"])

    # ── attendances ───────────────────────────────────────────────────────────
    op.create_table(
        "attendances",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_uuid", sa.String(36),
                  sa.ForeignKey("agent_cache.uuid", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("time_in",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("agent_uuid", "date", name="uq_agent_date"),
    )
    op.create_index("ix_att_date", "attendances", ["date"])
    op.create_index("ix_att_date_status", "attendances", ["date", "status"])
    op.create_index("ix_att_agent_uuid", "attendances", ["agent_uuid"])

    # ── scan_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "scan_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_uuid", sa.String(36),
                  sa.ForeignKey("agent_cache.uuid", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_time", sa.String(60), nullable=False, server_default=""),
        sa.Column("serial_no", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("agent_uuid", "scanned_at", name="uq_scan_agent_time"),
    )
    op.create_index("ix_scan_agent_uuid", "scan_logs", ["agent_uuid"])
    op.create_index("ix_scan_scanned_at", "scan_logs", ["scanned_at"])
    op.create_index("ix_scan_serial_no_unique", "scan_logs", ["serial_no"], unique=True)

    # ── sync_cursors ──────────────────────────────────────────────────────────
    op.create_table(
        "sync_cursors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(50), unique=True, nullable=False),
        sa.Column("last_position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_serial", sa.Integer, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── login_attempts ────────────────────────────────────────────────────────
    op.create_table(
        "login_attempts",
        sa.Column("email", sa.String(255), primary_key=True),
        sa.Column("failed_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("sync_cursors")
    op.drop_table("scan_logs")
    op.drop_table("attendances")
    op.drop_table("agent_cache")
