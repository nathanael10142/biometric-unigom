

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentResponse(BaseModel):
    """Full agent profile returned to the frontend.

    Historically the backend used `uuid`, `full_name` and `telephone`; the
    React UI expects `id`, `name` and `phone` (and treats `id` as a string).
    We keep the original attributes for backwards compatibility in Python but
    expose the renamed fields in the JSON output by setting aliases and
    populating them in the helper function.
    """
    # internal values (used by Python code)
    uuid: str
    matricule: str
    full_name: str
    department: str
    position: str
    email: Optional[str] = None
    telephone: Optional[str] = None
    biometric_id: Optional[str] = None
    statut: str
    is_active: bool

    # fields the frontend actually consumes
    id: str = Field(..., alias="id")
    name: str = Field(..., alias="name")
    phone: Optional[str] = Field(None, alias="phone")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # allow constructing via field names
        json_schema_extra={"example": {"id": "uuid-value", "name": "Jean"}},
    )


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
