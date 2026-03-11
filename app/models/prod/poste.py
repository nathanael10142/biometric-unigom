
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Integer, String, Text, Numeric, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import ProdBase


class Poste(ProdBase):
    """
    Modèle pour la table posteagents
    Représente un poste/position dans l'organisation
    """
    
    __tablename__ = "posteagents"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # IDENTIFIANT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INFORMATIONS DE BASE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    nom: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True,
        comment="Nom du poste (ex: Directeur Général, Infirmier)"
    )
    
    code_poste: Mapped[Optional[str]] = mapped_column(
        String(50), 
        unique=True, 
        nullable=True,
        comment="Code unique du poste (ex: POST001)"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DESCRIPTION & DÉTAILS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description détaillée du poste et responsabilités"
    )
    
    departement: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Département (RH, IT, Médical, Sécurité, etc)"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HIÉRARCHIE & CLASSIFICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    niveau_hierarchique: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Niveau hiérarchique (1=Directeur, 2=Manager, 3=Agent)"
    )
    
    niveau_grade: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Grade/Niveau (Junior, Senior, Expert, Manager)"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RÉMUNÉRATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    salaire_min: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Salaire minimum du poste"
    )
    
    salaire_max: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Salaire maximum du poste"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STATUT & ÉTAT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    statut: Mapped[str] = mapped_column(
        String(50),
        default="actif",
        nullable=False,
        comment="État du poste: actif, inactif, suspendu, obsolete"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # EFFECTIF & RESSOURCES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    nombre_postes_disponibles: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Nombre de postes disponibles pour cette position"
    )
    
    nombre_postes_pourvus: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Nombre de postes actuellement occupés"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMPÉTENCES & EXIGENCES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    competences_requises: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Compétences requises (format JSON)"
    )
    
    diplomes_requis: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Diplômes/formations requises"
    )
    
    experience_requise: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Années d'expérience minimales requises"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DATES & AUDIT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    date_creation: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Date de création du poste"
    )
    
    date_modification: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Date de dernière modification"
    )
    
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Utilisateur qui a créé le poste"
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Utilisateur qui a modifié le poste"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MÉTADONNÉES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes additionnelles sur le poste"
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONSTRAINT: Vérification du statut valide
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    __table_args__ = (
        CheckConstraint(
            "statut IN ('actif', 'inactif', 'suspendu', 'obsolete')",
            name="check_statut_valid"
        ),
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PROPRIÉTÉS CALCULÉES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    @property
    def salaire_moyen(self) -> Optional[float]:
        """Calcule le salaire moyen entre min et max"""
        if self.salaire_min and self.salaire_max:
            return (float(self.salaire_min) + float(self.salaire_max)) / 2
        return None
    
    @property
    def postes_libres(self) -> int:
        """Nombre de postes libres = disponibles - pourvus"""
        return self.nombre_postes_disponibles - self.nombre_postes_pourvus
    
    @property
    def pourcentage_pourvu(self) -> float:
        """Pourcentage de postes occupés"""
        if self.nombre_postes_disponibles == 0:
            return 0.0
        return (self.nombre_postes_pourvus / self.nombre_postes_disponibles) * 100
    
    @property
    def is_active(self) -> bool:
        """Vérifier si le poste est actif"""
        return self.statut == "actif"
    
    @property
    def is_available(self) -> bool:
        """Vérifier s'il y a des postes libres"""
        return self.postes_libres > 0
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # REPRÉSENTATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def __repr__(self) -> str:
        return (
            f"<Poste id={self.id} nom={self.nom!r} "
            f"dept={self.departement!r} statut={self.statut!r}>"
        )
    
    def __str__(self) -> str:
        return f"{self.nom} ({self.code_poste or 'N/A'})" if self.code_poste else self.nom
