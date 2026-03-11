import logging
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import LocalBase, local_engine, ProdSessionLocal, LocalSessionLocal

import app.models.agent_cache
import app.models.attendance
import app.models.scan_log
import app.models.sync_cursor
import app.models.login_attempt

import app.models.prod.agent
import app.models.prod.user_prod
import app.models.prod.poste
import app.models.prod.affectation_prod

from app.routers import auth, attendance, dashboard, employees

from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.ehome_listener import start_ehome_server

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("unigom")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("══════════════════════════════════════════════════")
    logger.info("  UNIGOM Biométrie v%s — Démarrage", settings.APP_VERSION)
    logger.info("  Prod DB  : %s", settings.DATABASE_PROD_URL.split("@")[-1])
    logger.info("  Local DB : %s", settings.DATABASE_PRESENCE_URL.split("@")[-1])
    logger.info("══════════════════════════════════════════════════")

    LocalBase.metadata.create_all(bind=local_engine)
    logger.info("[DB] Tables présence synchronisées (rhunigom_presence)")

    try:
        from app.services.agent_sync_service import sync_agents
        prod_db = ProdSessionLocal()
        local_db = LocalSessionLocal()
        try:
            summary = sync_agents(prod_db, local_db)
            logger.info("[STARTUP] Agent cache initialisé — %s", summary)
        finally:
            prod_db.close()
            local_db.close()
    except Exception as exc:
        logger.warning("[STARTUP] Agent sync failed (will retry on next sync): %s", exc)

    start_scheduler()

    ehome_task = None
    try:
        ehome_task = asyncio.create_task(start_ehome_server())
    except Exception as exc:
        logger.warning("[EHOME] Failed to start EHome server: %s", exc)

    yield

    if ehome_task is not None:
        ehome_task.cancel()
        try:
            await ehome_task
        except asyncio.CancelledError:
            pass

    stop_scheduler()
    logger.info("[UNIGOM] Arrêt du système")

_PREFIX = "/api/v1"

app = FastAPI(
    title="UNIGOM — Système Biométrique",
    version=settings.APP_VERSION,
    description=(
        "API de gestion de présence biométrique pour l'Université de Goma. "
        "Intégration terminaux Hikvision · Base HR production (lecture) · "
        "Base présence (écriture) · Heure de Goma (UTC+2)."
    ),
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur. Consultez les logs."},
    )

app.include_router(auth.router, prefix=_PREFIX)
app.include_router(employees.router, prefix=_PREFIX)
app.include_router(attendance.router, prefix=_PREFIX)
app.include_router(dashboard.router, prefix=_PREFIX)

@app.get("/health", tags=["System"], include_in_schema=False)
def health_check():
    from app.utils.time_utils import now_goma
    return {
        "status": "ok",
        "service": "unigom-biometrie",
        "version": settings.APP_VERSION,
        "goma_time": now_goma().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "databases": {
            "prod":  settings.DATABASE_PROD_URL.split("@")[-1],
            "local": settings.DATABASE_PRESENCE_URL.split("@")[-1],
        },
    }
