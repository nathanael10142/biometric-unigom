from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pytz
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

GOMA_TZ = pytz.timezone(settings.TIMEZONE)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify *plain* against *hashed* using bcrypt."""
    return _pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode a signed JWT access token."""
    payload = data.copy()
    expire = datetime.now(GOMA_TZ) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload["exp"] = expire
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.
    Raises jose.JWTError on invalid/expired tokens.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
