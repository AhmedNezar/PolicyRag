from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import json
from models import TokenPricing

pricing_path = Path(__file__).resolve().parent / "llm_pricing.json"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = ".env"
    )
        
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    GROQ_KEY: str = None
    MODEL_PROVIDER: str
    MODEL_NAME: str
    SMALL_MODEL_NAME: str
    GUARD_MODEL_NAME: str
    PASSWORD_SECRET: str
    PASSWORD_ALGORITHM: str = "HS256"
    REDIS_PASSWORD: str
    REDIS_HOST: str
    STREAM_UPDATE_SEC: int = 4
    CUTOFF_SEC: int = 30
    READ_FILE_CHUNK: int = 52428800
    EMBEDDING_VECTOR_SIZE: int = 768
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str
    EMBEDDING_PROVIDER: str
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int
    GUARD_THRESHOLD: float = 0.7
    TYPESAFE_API_KEY: str
    TYPESAFE_MODEL: str = "jev-1.13.0"
    ROUTER_PROVIDER: str = "jav"
    ROUTER_PROVIDER_FALLBACK: str = "llm"
    
    BASE_DIR: Path = Path(__file__).parent.parent
    
def get_settings():
    return Settings()

def load_pricing() -> dict[str, dict[str, TokenPricing]]:
    raw = json.loads(pricing_path.read_text(encoding="utf-8"))
    
    pricing = {
        provider: {
            model: TokenPricing.model_validate(model_pricing)
            for model, model_pricing in models.items()
        }
        for provider, models in raw.items()
    }
    
    return pricing
