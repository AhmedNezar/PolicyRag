from pydantic_settings import BaseSettings

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
    
def get_settings():
    return Settings()