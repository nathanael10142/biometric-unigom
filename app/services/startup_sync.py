"""
Synchronisation automatique des agents au démarrage du backend.

Ce script synchronise les agents depuis la base de production RH
vers la base locale de présence pour assurer que tous les employés
sont disponibles pour le système de pointage.
"""

import logging
from sqlalchemy.orm import Session

from app.database import get_db, get_prod_db
from app.services.agent_sync_service import sync_agents

logger = logging.getLogger(__name__)


def sync_agents_on_startup():
    """
    Synchroniser les agents depuis la base de production
    vers la base locale au démarrage du serveur.
    """
    try:
        logger.info("[STARTUP] Début de la synchronisation des agents...")
        
        # Récupérer les sessions de base de données
        prod_db = next(get_prod_db())
        local_db = next(get_db())
        
        # Lancer la synchronisation
        summary = sync_agents(prod_db, local_db)
        
        logger.info(
            "[STARTUP] Synchronisation terminée — %s",
            summary
        )
        
        # Afficher un résumé dans les logs
        total = summary.get('total', 0)
        inserted = summary.get('inserted', 0)
        updated = summary.get('updated', 0)
        deactivated = summary.get('deactivated', 0)
        
        logger.info(
            "[STARTUP] Résumé: Total=%d, Nouveaux=%d, Mis à jour=%d, Désactivés=%d",
            total, inserted, updated, deactivated
        )
        
        return True
        
    except Exception as exc:
        logger.error(
            "[STARTUP] Échec de la synchronisation automatique: %s",
            exc,
            exc_info=True
        )
        return False
    finally:
        # Fermer les sessions
        try:
            prod_db.close()
            local_db.close()
        except:
            pass


if __name__ == "__main__":
    # Test manuel
    print("Test de synchronisation des agents...")
    success = sync_agents_on_startup()
    if success:
        print("✅ Synchronisation réussie")
    else:
        print("❌ Échec de la synchronisation")
