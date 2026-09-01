from pydantic import UUID4
from datetime import datetime
from models import UserBase
    
class UserOut(UserBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime