

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import LocalBase

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.scan_log import ScanLog


class AgentCache(LocalBase):
    __tablename__ = "agent_cache"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True)

    matricule: Mapped[str] = mapped_column(String(20), nullable=False, default="NU")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    biometric_id: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, index=True, nullable=True, default=None
    )

    statut: Mapped[str] = mapped_column(String(50), nullable=False, default="actif")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    attendances: Mapped[List["Attendance"]] = relationship(
        "Attendance", back_populates="agent", cascade="all, delete-orphan"
    )
    scan_logs: Mapped[List["ScanLog"]] = relationship(
        "ScanLog", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<AgentCache uuid={self.uuid!r} "
            f"name={self.full_name!r} bio={self.biometric_id!r}>"
        )
