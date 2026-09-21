from abc import ABC, abstractmethod
from typing import AsyncGenerator
from models import LLMResponse, LLMStreamResponse
from pydantic import BaseModel
from models import TokenPricing

class LLMInterface(ABC):
    
    def  __init__(self, *, pricing: TokenPricing):
        self.pricing = pricing
    
    @abstractmethod
    async def generate(self, system_message: str, user_messages: list[dict], output_schema: BaseModel | None) -> str | BaseModel:
        pass
    
    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncGenerator[LLMStreamResponse, None]:
        pass
    
    @abstractmethod
    async def generate_title(self, message: str) -> str:
        pass