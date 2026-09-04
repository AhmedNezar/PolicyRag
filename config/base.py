from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    GROQ_KEY: str = None
    MODEL_PROVIDER: str
    MODEL_NAME: str
    PASSWORD_SECRET: str
    PASSWORD_ALGORITHM: str = "HS256"
    REDIS_PASSWORD: str
    STREAM_UPDATE_SEC: int = 4
    CUTOFF_SEC: int = 30
    READ_FILE_CHUNK: int = 52428800
    EMBEDDING_VECTOR_SIZE: int = 768
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str
    EMBEDDING_PROVIDER: str
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int
    
    BASE_DIR: Path = Path(__file__).parent.parent
    
def get_settings():
    return Settings()