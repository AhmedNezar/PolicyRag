from abc import ABC, abstractmethod
from typing import AsyncGenerator
from models import LLMResponse, LLMStreamResponse

class LLMInterface(ABC):
    
    @abstractmethod
    async def generate(self, messages: list[dict]) -> LLMResponse:
        pass
    
    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncGenerator[LLMStreamResponse, None]:
        pass
    
    @abstractmethod
    async def generate_title(self, message: str) -> str:
        pass