from abc import ABC, abstractmethod

class EmbeddingInterface(ABC):
    
    @abstractmethod
    async def embed_index(self, title: str, content: list[str]) -> list[list[float]]:
        pass
    
    @abstractmethod
    async def embed_retrieve(self, query: str) -> list[float]:
        pass