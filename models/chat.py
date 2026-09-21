from pydantic import BaseModel
from enum import Enum

class ChatIntents(str, Enum):
    SMALL_TALK = "small_talk"
    POLICY_QUESTION = "policy_question"
    POLICY_FOLLOWUP = "policy_followup"
    UNSUPPORTED = "unsupported"

class ChatRouter(BaseModel):
    route: ChatIntents
    confidence: float
    
class QueryRewrite(BaseModel):
    query: str