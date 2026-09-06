from slowapi import Limiter
from fastapi import Request
from config import get_settings
from jose import jwt, JWTError

settings = get_settings()

def get_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    
    if not auth.lower().startswith("bearer "):
        return request.client.host if request.client else "anonymous"
    
    token = auth.split(" ", 1)[1].strip()
    
    try:
        decoded_token = jwt.decode(
            token, settings.PASSWORD_SECRET, algorithms=[settings.PASSWORD_ALGORITHM]
        )
        
        user_id = str(decoded_token["id"])
        return user_id
    except (JWTError, KeyError):
        return request.client.host if request.client else "anonymous"

limiter = Limiter(
    default_limits=["200 per day", "60 per hour", "2/5seconds"],
    key_func=get_user_id,
    storage_uri=f"redis://:{settings.REDIS_PASSWORD}@localhost:6379/0",
    key_prefix="ratelimit"
)