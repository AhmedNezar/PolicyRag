from abc import ABC, abstractmethod
from typing import AsyncGenerator
from models import LLMStreamResponse, LLMUsage
from pydantic import BaseModel
from models import TokenPricing

class LLMInterface(ABC):

    def  __init__(self, *, pricing: TokenPricing):
        self.pricing = pricing

    @abstractmethod
    async def generate(self, system_message: str, user_messages: list[dict], output_schema: type[BaseModel] | None = None, schema_name: str | None = None) -> tuple[str | BaseModel, LLMUsage]:
        pass

    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncGenerator[LLMStreamResponse, None]:
        pass
