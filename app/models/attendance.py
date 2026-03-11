

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import LocalBase

if TYPE_CHECKING:
    from app.models.agent_cache import AgentCache


class Attendance(LocalBase):
    """
    Daily attendance record — one row per agent per day.
    Status values: PRESENT | LATE | ABSENT | REFUSED
    """

    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("agent_uuid", "date", name="uq_agent_date"),
        Index("ix_att_date", "date"),
        Index("ix_att_date_status", "date", "status"),
        Index("ix_att_agent_uuid", "agent_uuid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # References agent_cache.uuid (same presence DB — FK works)
    agent_uuid: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_cache.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_in: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    time_out: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # PRESENT | LATE | ABSENT | REFUSED
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    agent: Mapped["AgentCache"] = relationship("AgentCache", back_populates="attendances")

    # ── Convenience aliases for backward-compatible code ──────────────────────
    @property
    def employee_id(self) -> str:
        return self.agent_uuid

    @property
    def employee(self) -> "AgentCache":
        return self.agent

    def __repr__(self) -> str:
        return (
            f"<Attendance id={self.id} agent_uuid={self.agent_uuid!r} "
            f"date={self.date} status={self.status!r}>"
        )
