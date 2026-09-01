from entities import Token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

class TokenRepository:
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def list(self, skip: int, take: int) -> list[Token]:
        result = await self.session.execute(
            select(Token).offset(skip).limit(take)
        )
        return result.scalars().all()
        
    async def get(self, token_id: UUID) -> Token | None:
        result = await self.session.execute(
            select(Token).where(Token.id == token_id)
        )
        return result.scalars().first()
        
    async def create(self, token_data: dict) -> Token:
        new_token = Token(**token_data)
        self.session.add(new_token)
        await self.session.commit()
        await self.session.refresh(new_token)
        return new_token
    
    async def update(self, token_id: UUID, update_data: dict) -> Token | None:
        token = await self.get(token_id)
        if not token:
            return None
        
        for key, value in update_data.items():
            setattr(token, key, value)
            
        await self.session.commit()
        await self.session.refresh(token)
        return token
    
    async def delete(self, token_id: UUID) -> None:
        token = await self.get(token_id)
        if not token:
            return None
        
        await self.session.delete(token)
        await self.session.commit()
    