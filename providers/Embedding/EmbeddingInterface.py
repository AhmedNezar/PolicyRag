from abc import ABC, abstractmethod
from models import LLMUsage

class EmbeddingInterface(ABC):

    @abstractmethod
    async def embed_index(self, title: str, content: list[str]) -> tuple[list[list[float]], LLMUsage]:
        pass

    @abstractmethod
    async def embed_retrieve(self, query: str) -> tuple[list[float], LLMUsage]:
        pass
