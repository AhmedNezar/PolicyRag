from config import Settings
from .Gemini import Gemini

class EmbeddingFactory:
    def __init__(self, settings: Settings):
        self.settings = settings
        
    def create(self):
        if self.settings.EMBEDDING_PROVIDER == "gemini":
            return Gemini(settings=self.settings)