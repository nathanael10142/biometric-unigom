

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import ProdBase


class Poste(ProdBase):
    __tablename__ = "posteagents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<Poste id={self.id} nom={self.nom!r}>"
