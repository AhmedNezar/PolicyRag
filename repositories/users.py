from entities import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import UserInDB

class UserRepository:
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def list(self, skip: int, take: int) -> list[User]:
        result = await self.session.execute(
            select(User).offset(skip).limit(take)
        )
        return result.scalars().all()
        
    async def get(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()
    
    async def get_by_name(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where((User.username == username))
        )
        return result.scalars().first()
        
    async def create(self, user: dict) -> User:
        new_user = User(**user)
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user
    
    async def update(self, user_id: int, update_data: dict) -> User | None:
        user = await self.get(user_id)
        if not user:
            return None
        
        for key, value in update_data.items():
            setattr(user, key, value)
            
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete(self, user_id: int) -> None:
        user = await self.get(user_id)
        if not user:
            return None
        
        await self.session.delete(user)
        await self.session.commit()
    