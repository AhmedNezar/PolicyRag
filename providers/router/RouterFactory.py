from config.base import Settings
from .JavRouter import JavRouter
from .LLMRouter import LLMRouter
from .RouterInterface import RouterInterface
from services.llm_calls import LLMCallService, TrackedLLM
from config import load_pricing

class RouterFactory:
    def __init__(self, settings: Settings, calls: LLMCallService):
        self.settings = settings
        self.calls = calls
        
    def create(self, provider: str, model: TrackedLLM | None = None) -> RouterInterface:
        if provider == "jav":
            pricing = load_pricing()["typesafe"][self.settings.TYPESAFE_MODEL]
            return JavRouter(self.settings, calls=self.calls, pricing=pricing)
        elif provider == "llm":
            return LLMRouter(model)
        else:
            raise ValueError("Router provider doesn't exist.")
