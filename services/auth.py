from sqlalchemy.ext.asyncio import AsyncSession
from .password import PasswordService
from .token import TokenService
from repositories import UserRepository
from entities import User
from exceptions import AlreadyRegisteredException, UnauthorizedException
from models import UserCreate, UserInDB, UserEncode
from uuid import UUID


class AuthService:
    
    def __init__(self, password_service: PasswordService,
                 token_service: TokenService, user_repo: UserRepository):
        self.password_service = password_service
        self.token_service = token_service
        self.user_repo = user_repo
        
    async def register_user(self, user: UserCreate) -> User:
        if await self.user_repo.get_by_name(user.username):
            raise AlreadyRegisteredException
    
        
        hashed_password = await self.password_service.get_password_hash(password=user.password)
        return await self.user_repo.create(
            UserInDB(username=user.username, hashed_password=hashed_password).model_dump()
        )
    
    async def authenticate_user(self, username: str, password: str) -> str:
        if not (user := await self.user_repo.get_by_name(username)):
            raise UnauthorizedException
        if not await self.password_service.verify_password(password, user.hashed_password):
            raise UnauthorizedException
        
        to_encode = UserEncode.model_validate(user)
        return await self.token_service.create_access_token(to_encode)
    
    async def get_current_user(self, token: str) -> User:
        payload = self.token_service.decode(token)
        token_id = UUID(payload.get("sub"))
        if not await self.token_service.validate(token_id):
            raise UnauthorizedException
        if not (username := payload.get("username")):
            raise UnauthorizedException
        if not (user := await self.user_repo.get_by_name(username)):
            raise UnauthorizedException
        return user
    
    async def logout(self, token: str) -> None:
        payload = self.token_service.decode(token)
        token_id = UUID(payload.get("sub"))
        await self.token_service.deactivate(token_id)