from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db, get_prod_db
from app.models.prod.user_prod import UserProd

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_admin(
    token: str = Depends(oauth2_scheme),
    prod_db: Session = Depends(get_prod_db),
) -> UserProd:
    """
    FastAPI dependency — validates the Bearer JWT and returns the active user
    from the production DB users table.
    Raises HTTP 401 on any authentication failure.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise — token invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub", "")
        if not email:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user: UserProd | None = (
        prod_db.query(UserProd)
        .filter(
            UserProd.email == email,
            UserProd.isActive == True,
            UserProd.deletedAt == None,
        )
        .first()
    )
    if user is None:
        raise credentials_exc

    return user
