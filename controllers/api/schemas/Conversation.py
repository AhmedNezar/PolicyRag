from datetime import datetime
from pydantic import BaseModel, ConfigDict, UUID4

class ConversationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    title: str
    model_type: str
    
class ConversationCreate(ConversationBase):
    pass

class ConversationUpdate(ConversationBase):
    pass

class ConversationOut(ConversationBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime