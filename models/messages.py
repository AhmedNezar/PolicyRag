from typing import Literal
from pydantic import BaseModel
from enum import Enum
from decimal import Decimal

class LLMUsage(BaseModel):
    prompt_tokens: int | None = None
    response_tokens: int | None = None
    total_tokens: int | None = None
    input_cost: Decimal | None = None
    output_cost: Decimal | None = None
    total_cost: Decimal | None = None

class LLMResponse(BaseModel):
    prompt_content: str
    response_content: str
    usage: LLMUsage | None = None
    is_success: bool | None = None
    
class LLMStreamResponse(BaseModel):
    type: Literal["data", "stop"]
    content: str
    raw_content: str
    usage: LLMUsage | None = None
    done: bool = False
    
class MessageStatus(Enum):
    PENDING = "pending"
    STREAMING = "streaming"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"