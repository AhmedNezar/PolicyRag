from config import Settings
from .Groq import Groq

class LLMFactory:
    def __init__(self, settings: Settings):
        self.settings = settings
        
    def create(self):
        if self.settings.MODEL_PROVIDER == "groq":
            return Groq(settings=self.settings)