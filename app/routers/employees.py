

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database import get_db, get_prod_db
from app.models.agent_cache import AgentCache
from app.models.prod.agent import Agent
from app.models.prod.user_prod import UserProd
from app.schemas.agent import (
    AgentPaginated,
    AgentResponse,
    BiometricIdUpdate,
)
from app.schemas.attendance import AgentSyncResponse
from app.services.agent_sync_service import sync_agents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employees", tags=["Agents"])


# ── Helper: AgentCache → AgentResponse ───────────────────────────────────────


def _cache_to_response(a: AgentCache) -> AgentResponse:
    return AgentResponse(
        uuid=a.uuid,
        matricule=a.matricule,
        full_name=a.full_name,
        department=a.department,
        position=a.position,
        email=a.email,
        telephone=a.telephone,
        biometric_id=a.biometric_id,
        statut=a.statut,
        is_active=a.is_active,
    )


# ── List ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=AgentPaginated, summary="Liste des agents")
def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    search: Optional[str] = Query(None, description="Recherche par nom, email ou ID bio"),
    department: Optional[str] = Query(None, description="Filtrer par direction/service"),
    active_only: bool = Query(True, description="Afficher seulement les agents actifs"),
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> AgentPaginated:
    """List agents from the local cache (fast, no cross-DB query)."""
    query = db.query(AgentCache)

    if active_only:
        query = query.filter(AgentCache.is_active == True)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                AgentCache.full_name.ilike(term),
                AgentCache.biometric_id.ilike(term),
                AgentCache.email.ilike(term),
                AgentCache.matricule.ilike(term),
            )
        )
    if department:
        query = query.filter(AgentCache.department == department)

    total: int = query.count()
    items = (
        query.order_by(AgentCache.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return AgentPaginated(
        items=[_cache_to_response(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


# ── Get one ───────────────────────────────────────────────────────────────────


@router.get("/{agent_uuid}", response_model=AgentResponse, summary="Détail d'un agent")
def get_agent(
    agent_uuid: str,
    db: Session = Depends(get_db),
    _: UserProd = Depends(get_current_admin),
) -> AgentResponse:
    agent = db.get(AgentCache, agent_uuid)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent introuvable.")
    return _cache_to_response(agent)


# ── Assign / clear biometric ID ───────────────────────────────────────────────


@router.put(
    "/{agent_uuid}/biometric",
    response_model=AgentResponse,
    summary="Assigner ou supprimer l'ID biométrique d'un agent",
)
def set_biometric_id(
    agent_uuid: str,
    data: BiometricIdUpdate,
    db: Session = Depends(get_db),
    prod_db: Session = Depends(get_prod_db),
    admin: UserProd = Depends(get_current_admin),
) -> AgentResponse:
    """
    Write biometric_id to BOTH databases:
      1. Production agents table (canonical source for HR system).
      2. Local agent_cache (used for fast attendance resolution).
    """
    # Validate in local cache first
    cache: Optional[AgentCache] = db.get(AgentCache, agent_uuid)
    if cache is None:
        raise HTTPException(status_code=404, detail="Agent introuvable dans le cache local. Lancez une synchronisation.")

    # Uniqueness check in local cache
    new_bio = data.biometric_id
    if new_bio is not None:
        conflict = (
            db.query(AgentCache)
            .filter(
                AgentCache.biometric_id == new_bio,
                AgentCache.uuid != agent_uuid,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'ID biométrique « {new_bio} » est déjà attribué à {conflict.full_name}.",
            )

    # ── 1. Write to production DB ─────────────────────────────────────────────
    prod_agent: Optional[Agent] = prod_db.get(Agent, agent_uuid)
    if prod_agent is not None:
        prod_agent.biometric_id = new_bio
        try:
            prod_db.commit()
        except Exception as exc:
            prod_db.rollback()
            logger.error("[EMPLOYEES] Failed to update prod DB biometric_id: %s", exc)
            raise HTTPException(
                status_code=500,
                detail=f"Impossible d'écrire dans la base de production: {exc}",
            )
    else:
        logger.warning(
            "[EMPLOYEES] Agent uuid=%r not found in prod DB — updating cache only", agent_uuid
        )

    # ── 2. Write to local cache ───────────────────────────────────────────────
    cache.biometric_id = new_bio
    db.commit()

    action = f"set biometric_id={new_bio!r}" if new_bio else "cleared biometric_id"
    logger.info(
        "[EMPLOYEES] Admin %r %s for agent %r",
        admin.email, action, cache.full_name,
    )
    return _cache_to_response(cache)


# ── Sync agents from production ───────────────────────────────────────────────


@router.post(
    "/sync",
    response_model=AgentSyncResponse,
    summary="Synchroniser les agents depuis la base de production",
)
def sync_agents_endpoint(
    prod_db: Session = Depends(get_prod_db),
    db: Session = Depends(get_db),
    admin: UserProd = Depends(get_current_admin),
) -> AgentSyncResponse:
    """
    Pull all agents from the production DB into the local agent_cache.
    Should be called whenever HR makes changes to the agents table.
    """
    try:
        summary = sync_agents(prod_db, db)
        logger.info("[EMPLOYEES] Admin %r triggered agent sync — %s", admin.email, summary)
        return AgentSyncResponse(
            message=f"Synchronisation réussie — {summary['total']} agent(s) traité(s).",
            **summary,
        )
    except Exception as exc:
        logger.error("[EMPLOYEES] Agent sync failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Échec de la synchronisation agents: {exc}",
        )
