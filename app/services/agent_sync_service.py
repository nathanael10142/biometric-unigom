

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agent_cache import AgentCache
from app.models.prod.affectation_prod import AffectationProd
from app.models.prod.agent import Agent
from app.models.prod.poste import Poste
from app.utils.time_utils import now_goma

logger = logging.getLogger(__name__)


def sync_agents(prod_db: Session, local_db: Session) -> dict:
    inserted = updated = deactivated = 0

    try:
        prod_agents = prod_db.query(Agent).all()
    except Exception as exc:
        logger.error("[AGENT-SYNC] Cannot query production DB: %s", exc)
        raise

    postes = {p.id: p.nom for p in prod_db.query(Poste).all()}
    affectations = {a.id: a.nom for a in prod_db.query(AffectationProd).all()}

    synced_at = now_goma()
    prod_uuids = {a.id for a in prod_agents}

    for agent in prod_agents:
        parts = [agent.nom]
        if agent.postnom:
            parts.append(agent.postnom)
        if agent.prenom:
            parts.append(agent.prenom)
        full_name = " ".join(parts)

        department = affectations.get(agent.affectationId, "N/A")
        position = postes.get(agent.posteId, "N/A")
        is_active = agent.statut == "actif"

        cache: Optional[AgentCache] = (
            local_db.query(AgentCache).filter(AgentCache.uuid == agent.id).first()
        )

        if cache is None:
            cache = AgentCache(
                uuid=agent.id,
                matricule=agent.matricule or "NU",
                full_name=full_name,
                department=department,
                position=position,
                email=agent.email,
                telephone=agent.telephone,
                biometric_id=agent.biometric_id,
                statut=agent.statut,
                is_active=is_active,
                last_synced_at=synced_at,
            )
            local_db.add(cache)
            inserted += 1
        else:
            cache.matricule = agent.matricule or "NU"
            cache.full_name = full_name
            cache.department = department
            cache.position = position
            cache.email = agent.email
            cache.telephone = agent.telephone
            cache.statut = agent.statut
            cache.is_active = is_active
            cache.last_synced_at = synced_at
            updated += 1

    stale = (
        local_db.query(AgentCache)
        .filter(AgentCache.uuid.notin_(prod_uuids), AgentCache.is_active == True)
        .all()
    )
    for s in stale:
        s.is_active = False
        deactivated += 1

    local_db.commit()

    summary = {
        "inserted": inserted,
        "updated": updated,
        "deactivated": deactivated,
        "total": len(prod_agents),
    }
    logger.info("[AGENT-SYNC] Done — %s", summary)
    return summary
