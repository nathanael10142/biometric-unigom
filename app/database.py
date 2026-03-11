

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# ── Production DB engine (agents + users from HR system) ──────────────────────
prod_engine = create_engine(
    settings.DATABASE_PROD_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,  # Never echo prod queries
)

ProdSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=prod_engine,
)


class ProdBase(DeclarativeBase):
    """Base for read-only production DB models (agents, users, postes…)."""
    pass


# ── Presence DB engine (our attendance records) ────────────────────────────────
# Use Supabase PostgreSQL if DATABASE_URL is set, otherwise local MySQL
db_url = settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL else settings.DATABASE_PRESENCE_URL

local_engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

LocalSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=local_engine,
)


class LocalBase(DeclarativeBase):
    """Base for presence DB models (agent_cache, attendances, scan_logs…)."""
    pass


# ── Backward-compatible aliases ────────────────────────────────────────────────
# Keep Base / engine / SessionLocal pointing to the LOCAL presence DB so that
# any code that still imports them works without change.
Base = LocalBase
engine = local_engine
SessionLocal = LocalSessionLocal


# ── FastAPI dependency factories ───────────────────────────────────────────────

def get_db():
    """Local presence DB session (read-write)."""
    db = LocalSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_prod_db():
    """Production HR DB session (read-only except biometric_id writes)."""
    db = ProdSessionLocal()
    try:
        yield db
    finally:
        db.close()
