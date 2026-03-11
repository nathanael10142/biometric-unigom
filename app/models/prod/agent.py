

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import ProdBase


class Agent(ProdBase):
    

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    matricule: Mapped[str] = mapped_column(String(20), nullable=False, default="NU")
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    postnom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prenom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # statut: actif | suspendu | retraité | fin de contract | revoquer
    statut: Mapped[str] = mapped_column(String(50), nullable=False, default="actif")
    posteId: Mapped[int] = mapped_column(Integer, nullable=False)
    affectationId: Mapped[int] = mapped_column(Integer, nullable=False)
    # biometric_id — added via: ALTER TABLE agents ADD COLUMN biometric_id VARCHAR(50) NULL UNIQUE;
    biometric_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    @property
    def full_name(self) -> str:
        """Nom complet: NOM Postnom Prénom."""
        parts = [self.nom]
        if self.postnom:
            parts.append(self.postnom)
        if self.prenom:
            parts.append(self.prenom)
        return " ".join(parts)

    @property
    def is_active(self) -> bool:
        return self.statut == "actif"

    def __repr__(self) -> str:
        return f"<Agent id={self.id!r} nom={self.nom!r} bio={self.biometric_id!r}>"
