from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class EmployeeCreate(BaseModel):
    name: str
    department: str
    position: str

    biometric_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("name", "department", "position")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Ce champ ne peut pas être vide")
        return v.strip()

    @field_validator("biometric_id")
    @classmethod
    def biometric_id_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Allow None, but reject empty strings."""
        if v is not None and not v.strip():
            raise ValueError("L'ID biométrique ne peut pas être une chaîne vide")
        return v.strip() if v else None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    biometric_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeResponse(BaseModel):
    id: int
    name: str
    department: str
    position: str
    biometric_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeePaginated(BaseModel):
    items: List[EmployeeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
