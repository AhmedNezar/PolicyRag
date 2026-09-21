from config import Settings
from .Groq import Groq

class LLMFactory:
    def __init__(self, model_name: str, settings: Settings, pricing_catalog: dict):
        self.settings = settings
        self.pricing_catalog = pricing_catalog
        self.model_name = model_name
        
    def create(self):
        
        try:
            pricing = self.pricing_catalog[self.settings.MODEL_PROVIDER][self.model_name]
        except Exception:
            raise ValueError(f"{self.settings.MODEL_PROVIDER}/{self.model_name} pricing does not exist.")

        if self.settings.MODEL_PROVIDER == "groq":
            return Groq(self.model_name, settings=self.settings, pricing=pricing)