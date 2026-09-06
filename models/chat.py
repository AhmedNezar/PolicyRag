from pydantic import BaseModel
from typing import Literal
from enum import Enum

class ChatIntents(str, Enum):
    SMALL_TALK = "small_talk"
    POLICY_QUESTION = "policy_question"
    POLICY_FOLLOWUP = "policy_followup"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"

class ChatRouter(BaseModel):
    allowed: bool
    route: ChatIntents
    needs_retrieval: bool
    
class QueryRewrite(BaseModel):
    query: str