from datetime import datetime, UTC, timedelta
from exceptions import UnauthorizedException
from jose import JWTError, jwt
from uuid import UUID
from repositories import TokenRepository
from config import Settings
from models import UserEncode

class TokenService:
    def __init__(self, token_repo: TokenRepository, settings: Settings):
        self.secret_key = settings.PASSWORD_SECRET
        self.algorithm = settings.PASSWORD_ALGORITHM
        self.expires_in_minutes = 60
        self.token_repo = token_repo
        
    async def create_access_token(self, data: UserEncode, expires_delta: timedelta | None = None) -> str:
        to_encode = data.model_dump(mode="json")
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=self.expires_in_minutes)
        
        token = await self.token_repo.create(
            token_data={
                "user_id": data.id,
                "expires_at": expire
            }
        )
        
        to_encode.update({
            "exp": expire,
            "iss": "chatbot",
            "sub": str(token.id)
        })
        
        encoded_jwt = jwt.encode(
            to_encode, self.secret_key, algorithm=self.algorithm
        )
        
        return encoded_jwt
    
    async def deactivate(self, token_id: UUID) -> None:
        await self.token_repo.update(token_id, {
            "is_active": False
        })
    
    def decode(self, encoded_token: str) -> dict:
        try:
            return jwt.decode(
                encoded_token, self.secret_key, algorithms=[self.algorithm]
            )
        except JWTError:
            raise UnauthorizedException
        
    async def validate(self, token_id: UUID) -> bool:
        return (token := await self.token_repo.get(token_id)) is not None and token.is_active
    