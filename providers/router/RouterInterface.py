from abc import ABC, abstractmethod
from models.chat import ChatIntents

class RouterInterface(ABC):
    
    @abstractmethod
    async def route(self, message: str, **call_context) -> tuple[ChatIntents, float]:
        pass
