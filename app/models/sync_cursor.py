

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class SyncCursor(Base):
    __tablename__ = "sync_cursors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Logical name for the cursor, e.g. "hikvision"
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Hikvision searchResultPosition — always resume from here
    last_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Highest serialNo persisted in scan_logs — deduplication safety net
    last_serial: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<SyncCursor key={self.key!r} "
            f"last_position={self.last_position} "
            f"last_serial={self.last_serial}>"
        )
