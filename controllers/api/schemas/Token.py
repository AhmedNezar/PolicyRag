from pydantic import BaseModel
from datetime import datetime
from pydantic import UUID4

class TokenBase(BaseModel):
    user_id: UUID4
    expires_at: datetime
    is_active: bool = True
    ip_address: str | None = None
    
class TokenCreate(TokenBase):
    pass

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "Bearer"