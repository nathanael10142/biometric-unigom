

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import ProdBase


class UserProd(ProdBase):
    """System user account linked to an agent — used for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # FK → agents.id (char 36)
    agentId: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Bcrypt-hashed password (set by the Node.js HR system)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    roleId: Mapped[int] = mapped_column(Integer, nullable=False)
    isActive: Mapped[bool] = mapped_column(nullable=False, default=True)
    lastLogin: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deletedAt: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    mustChangePassword: Mapped[bool] = mapped_column(nullable=False, default=False)

    @property
    def username(self) -> str:
        """Alias so routers can use admin.username without change."""
        return self.email

    @property
    def is_active_bool(self) -> bool:
        return bool(self.isActive) and self.deletedAt is None

    def __repr__(self) -> str:
        return f"<UserProd id={self.id} email={self.email!r}>"
