"""make employees.biometric_id nullable

Revision ID: a3f7e2c1d850
Revises:
Create Date: 2026-03-10 10:00:00.000000

Context
-------
The production `agents` table (MariaDB/Sequelize) does not yet carry a
biometric_id column.  Employees will be imported without one and the field
will be populated once:
  1. The production agents table receives the biometric_id column.
  2. Each agent is enrolled on the Hikvision terminal.

Until then, biometric_id is nullable.  Employees without a biometric_id are
still tracked for attendance (marked ABSENT by the scheduler) but will never
match a scan event from the terminal.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a3f7e2c1d850"
down_revision = None   # update once other migrations exist
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow NULL values for biometric_id
    op.alter_column(
        "employees",
        "biometric_id",
        existing_type=sa.String(length=50),
        nullable=True,
    )


def downgrade() -> None:
    # First set a placeholder for any NULLs to allow re-adding NOT NULL
    op.execute(
        "UPDATE employees SET biometric_id = CONCAT('UNSET-', CAST(id AS TEXT)) "
        "WHERE biometric_id IS NULL"
    )
    op.alter_column(
        "employees",
        "biometric_id",
        existing_type=sa.String(length=50),
        nullable=False,
    )
