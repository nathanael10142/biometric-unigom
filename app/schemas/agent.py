

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class AgentResponse(BaseModel):
    """Full agent profile returned to the frontend."""
    uuid: str
    matricule: str
    full_name: str
    department: str
    position: str
    email: str
    telephone: Optional[str] = None
    biometric_id: Optional[str] = None
    statut: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AgentPaginated(BaseModel):
    items: List[AgentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BiometricIdUpdate(BaseModel):
    """Payload to assign or clear a biometric ID for an agent."""
    biometric_id: Optional[str] = None

    @field_validator("biometric_id")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("L'ID biométrique ne peut pas être une chaîne vide.")
        return v.strip() if v else None
