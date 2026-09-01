from pydantic import BaseModel, ConfigDict, UUID4
from models import MessageStatus

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    conversation_id: UUID4
    prompt_content: str
    response_content: str
    status: MessageStatus
    
class MessageIn(BaseModel):
    content: str