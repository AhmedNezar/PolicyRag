from config import Settings
from .Groq import Groq

class LLMFactory:
    def __init__(self, settings: Settings, pricing_catalog: dict):
        self.settings = settings
        self.pricing_catalog = pricing_catalog
        
    def create(self):
        
        try:
            pricing = self.pricing_catalog[self.settings.MODEL_PROVIDER][self.settings.MODEL_NAME]
        except Exception:
            raise ValueError(f"{self.settings.MODEL_PROVIDER}/{self.settings.MODEL_NAME} pricing does not exist.")

        if self.settings.MODEL_PROVIDER == "groq":
            return Groq(settings=self.settings, pricing=pricing)