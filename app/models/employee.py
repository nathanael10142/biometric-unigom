from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


from app.database import Base

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.scan_log import ScanLog


class Employee(Base):
    """Personnel member registered in the biometric system."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    # Nullable until the production `agents` table gets the biometric_id column
    # and all agents are enrolled on the terminal.  Employees without an ID are
    # tracked for absence but will never match a Hikvision scan event.
    biometric_id: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, index=True, nullable=True, default=None
    )
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    # NOTE: attendances and scan_logs used to be modeled directly against the
    # employees table, but the current presence schema links through
    # ``agent_cache`` instead.  keeping these properties here caused SQLAlchemy
    # startup to raise ``InvalidRequestError`` (no foreign key exists), so we
    # simply drop them.  If you ever need to traverse from an employee ID to
    # attendance/scan data, query ``AgentCache`` instead.

    def __repr__(self) -> str:
        return f"<Employee id={self.id} name={self.name!r} biometric={self.biometric_id!r}>"

