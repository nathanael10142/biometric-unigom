

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import ProdBase


class AffectationProd(ProdBase):
    __tablename__ = "affectations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<AffectationProd id={self.id} nom={self.nom!r}>"
