"""
Service pour la gestion des postes
CRUD operations et business logic
"""

from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.prod.poste import Poste
from app.schemas.poste import PosteCreate, PosteUpdate, PosteStatistics


class PosteService:
    """Service pour gérer les postes"""

    @staticmethod
    def create(db: Session, poste_create: PosteCreate, created_by: str) -> Poste:
        """Créer un nouveau poste"""
        poste = Poste(
            **poste_create.model_dump(exclude_unset=True),
            created_by=created_by,
            updated_by=created_by
        )
        db.add(poste)
        db.commit()
        db.refresh(poste)
        return poste

    @staticmethod
    def get_by_id(db: Session, poste_id: int) -> Optional[Poste]:
        """Récupérer un poste par son ID"""
        stmt = select(Poste).where(Poste.id == poste_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_nom(db: Session, nom: str) -> Optional[Poste]:
        """Récupérer un poste par son nom"""
        stmt = select(Poste).where(Poste.nom == nom)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_code(db: Session, code_poste: str) -> Optional[Poste]:
        """Récupérer un poste par son code"""
        stmt = select(Poste).where(Poste.code_poste == code_poste)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        statut: Optional[str] = None,
        departement: Optional[str] = None
    ) -> tuple[List[Poste], int]:
        """Lister tous les postes avec filtres optionnels"""
        stmt = select(Poste)
        
        if statut:
            stmt = stmt.where(Poste.statut == statut)
        
        if departement:
            stmt = stmt.where(Poste.departement == departement)
        
        # Compter le total
        count_stmt = select(func.count(Poste.id))
        if statut:
            count_stmt = count_stmt.where(Poste.statut == statut)
        if departement:
            count_stmt = count_stmt.where(Poste.departement == departement)
        
        total = db.execute(count_stmt).scalar()
        
        # Récupérer les postes paginés
        postes = db.execute(
            stmt.offset(skip).limit(limit)
        ).scalars().all()
        
        return postes, total

    @staticmethod
    def update(
        db: Session,
        poste_id: int,
        poste_update: PosteUpdate,
        updated_by: str
    ) -> Optional[Poste]:
        """Mettre à jour un poste"""
        poste = PosteService.get_by_id(db, poste_id)
        if not poste:
            return None
        
        update_data = poste_update.model_dump(exclude_unset=True)
        update_data['updated_by'] = updated_by
        
        for key, value in update_data.items():
            setattr(poste, key, value)
        
        db.commit()
        db.refresh(poste)
        return poste

    @staticmethod
    def delete(db: Session, poste_id: int) -> bool:
        """Supprimer un poste"""
        poste = PosteService.get_by_id(db, poste_id)
        if not poste:
            return False
        
        db.delete(poste)
        db.commit()
        return True

    @staticmethod
    def get_by_departement(db: Session, departement: str) -> List[Poste]:
        """Récupérer tous les postes d'un département"""
        stmt = select(Poste).where(
            Poste.departement == departement
        ).order_by(Poste.niveau_hierarchique)
        return db.execute(stmt).scalars().all()

    @staticmethod
    def get_active_postes(db: Session) -> List[Poste]:
        """Récupérer tous les postes actifs"""
        stmt = select(Poste).where(
            Poste.statut == "actif"
        ).order_by(Poste.niveau_hierarchique, Poste.nom)
        return db.execute(stmt).scalars().all()

    @staticmethod
    def get_available_postes(db: Session) -> List[Poste]:
        """Récupérer les postes avec des postes libres"""
        from sqlalchemy import and_
        
        stmt = select(Poste).where(
            and_(
                Poste.statut == "actif",
                Poste.nombre_postes_pourvus < Poste.nombre_postes_disponibles
            )
        ).order_by(Poste.niveau_hierarchique)
        return db.execute(stmt).scalars().all()

    @staticmethod
    def get_statistics(db: Session) -> PosteStatistics:
        """Obtenir les statistiques sur les postes"""
        # Total de postes
        total_postes = db.execute(
            select(func.count(Poste.id))
        ).scalar() or 0
        
        # Postes actifs
        postes_actifs = db.execute(
            select(func.count(Poste.id)).where(Poste.statut == "actif")
        ).scalar() or 0
        
        # Total de positions disponibles
        total_disponibles = db.execute(
            select(func.sum(Poste.nombre_postes_disponibles))
        ).scalar() or 0
        
        # Total de positions pourvues
        total_pourvues = db.execute(
            select(func.sum(Poste.nombre_postes_pourvus))
        ).scalar() or 0
        
        # Pourcentage d'occupation
        pourcentage = (
            (total_pourvues / total_disponibles * 100)
            if total_disponibles > 0
            else 0
        )
        
        # Departements
        departements_data = db.execute(
            select(
                Poste.departement,
                func.count(Poste.id)
            ).group_by(Poste.departement)
        ).all()
        departements = {dept: count for dept, count in departements_data if dept}
        
        # Niveaux hiérarchiques
        niveaux_data = db.execute(
            select(
                Poste.niveau_hierarchique,
                func.count(Poste.id)
            ).where(Poste.niveau_hierarchique.isnot(None))
            .group_by(Poste.niveau_hierarchique)
        ).all()
        niveaux = {str(niveau): count for niveau, count in niveaux_data}
        
        return PosteStatistics(
            total_postes=total_postes,
            postes_actifs=postes_actifs,
            total_positions_disponibles=total_disponibles,
            total_positions_pourvues=total_pourvues,
            pourcentage_occupancy=round(pourcentage, 2),
            departements=departements,
            niveaux_hierarchiques=niveaux
        )

    @staticmethod
    def update_nombre_pourvus(
        db: Session,
        poste_id: int,
        new_count: int
    ) -> Optional[Poste]:
        """Mettre à jour le nombre de postes pourvus"""
        poste = PosteService.get_by_id(db, poste_id)
        if not poste:
            return None
        
        if new_count > poste.nombre_postes_disponibles:
            raise ValueError(
                f"Impossible d'avoir plus de {poste.nombre_postes_disponibles} postes pourvus"
            )
        
        poste.nombre_postes_pourvus = new_count
        db.commit()
        db.refresh(poste)
        return poste

    @staticmethod
    def search(db: Session, query: str) -> List[Poste]:
        """Rechercher des postes par nom ou description"""
        from sqlalchemy import or_
        
        search_pattern = f"%{query}%"
        stmt = select(Poste).where(
            or_(
                Poste.nom.ilike(search_pattern),
                Poste.description.ilike(search_pattern),
                Poste.code_poste.ilike(search_pattern)
            )
        )
        return db.execute(stmt).scalars().all()
