from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AdminResponse(BaseModel):
    
    id: int
    username: str   
    is_active: bool

    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    admin: AdminResponse
