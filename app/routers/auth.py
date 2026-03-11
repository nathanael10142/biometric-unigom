

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_admin
from app.core.security import create_access_token, verify_password
from app.database import get_db, get_prod_db
from app.models.login_attempt import LoginAttempt
from app.models.prod.user_prod import UserProd
from app.schemas.admin import AdminResponse, TokenResponse
from app.utils.time_utils import now_goma

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _get_or_create_attempt(db: Session, email: str) -> LoginAttempt:
    attempt = db.query(LoginAttempt).filter(LoginAttempt.email == email).first()
    if attempt is None:
        attempt = LoginAttempt(email=email, failed_attempts=0)
        db.add(attempt)
        db.flush()
    return attempt


@router.post("/token", response_model=TokenResponse, summary="Connexion administrateur")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    prod_db: Session = Depends(get_prod_db),
    local_db: Session = Depends(get_db),
) -> TokenResponse:
    """
    OAuth2 password-grant — returns a signed JWT on success.
    Email is used as the username field.
    Lockout is tracked locally after MAX_FAILED_ATTEMPTS.
    """
    email = form_data.username.strip().lower()

    # ── Lockout check (local presence DB) ─────────────────────────────────────
    attempt = _get_or_create_attempt(local_db, email)
    if attempt.locked_until is not None:
        now = now_goma()
        locked_until = attempt.locked_until
        if locked_until.tzinfo is None:
            import pytz
            locked_until = pytz.utc.localize(locked_until)
        if now < locked_until:
            logger.warning("[AUTH] Account %r is locked until %s", email, locked_until)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Compte verrouillé suite à trop de tentatives. "
                    f"Réessayez après {locked_until.strftime('%H:%M:%S')} (heure de Goma)."
                ),
            )
        else:
            attempt.failed_attempts = 0
            attempt.locked_until = None
            local_db.commit()

    # ── Look up user in production DB ─────────────────────────────────────────
    user: UserProd | None = (
        prod_db.query(UserProd)
        .filter(
            UserProd.email == email,
            UserProd.isActive == True,
            UserProd.deletedAt == None,
        )
        .first()
    )

    # ── Credential validation ──────────────────────────────────────────────────
    if user is None or not verify_password(form_data.password, user.password):
        attempt.failed_attempts = (attempt.failed_attempts or 0) + 1
        if attempt.failed_attempts >= settings.MAX_FAILED_ATTEMPTS:
            attempt.locked_until = now_goma() + timedelta(minutes=settings.LOCKOUT_MINUTES)
            logger.warning(
                "[AUTH] Account %r locked after %d failed attempts",
                email, attempt.failed_attempts,
            )
        local_db.commit()

        logger.warning("[AUTH] Failed login attempt for email=%r", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects. Vérifiez votre email et mot de passe.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Success ────────────────────────────────────────────────────────────────
    attempt.failed_attempts = 0
    attempt.locked_until = None
    local_db.commit()

    token = create_access_token({"sub": user.email})
    logger.info("[AUTH] User %r logged in successfully", user.email)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        admin=AdminResponse(
            id=user.id,
            username=user.email,
            is_active=user.is_active_bool,
            created_at=None,
            last_login=user.lastLogin,
        ),
    )


@router.get("/me", response_model=AdminResponse, summary="Profil utilisateur courant")
def get_me(current_user: UserProd = Depends(get_current_admin)) -> AdminResponse:
    """Return the authenticated user's profile."""
    return AdminResponse(
        id=current_user.id,
        username=current_user.email,
        is_active=current_user.is_active_bool,
        created_at=None,
        last_login=current_user.lastLogin,
    )
