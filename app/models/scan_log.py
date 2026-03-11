

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import LocalBase

if TYPE_CHECKING:
    from app.models.agent_cache import AgentCache


class ScanLog(LocalBase):

    __tablename__ = "scan_logs"
    __table_args__ = (
        UniqueConstraint("serial_no", name="uq_serial_no"),
        Index("ix_scan_agent_uuid", "agent_uuid"),
        Index("ix_scan_scanned_at", "scanned_at"),
        Index("ix_scan_device_id", "device_id"),
        Index("ix_scan_campus_id", "campus_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    agent_uuid: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_cache.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    device_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    campus_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    raw_time: Mapped[str] = mapped_column(String(60), nullable=False, default="")

    serial_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    agent: Mapped["AgentCache"] = relationship("AgentCache", back_populates="scan_logs")

    @property
    def employee_id(self) -> str:
        return self.agent_uuid

    @property
    def employee(self) -> "AgentCache":
        return self.agent

    def __repr__(self) -> str:
        return (
            f"<ScanLog id={self.id} agent_uuid={self.agent_uuid!r} "
            f"serial_no={self.serial_no} scanned_at={self.scanned_at!r}>"
        )
