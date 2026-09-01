from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from entities import Conversation, Message
from uuid import UUID

class ConversationRepository:
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def list(self, user_id: UUID, skip: int, take: int) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(Conversation.user_id == user_id).offset(skip).limit(take)
        )
        return result.scalars().all()
        
    async def get(self, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalars().first()
        
    async def create(self, conversation_data: dict) -> Conversation:
        new_conversation = Conversation(**conversation_data)
        self.session.add(new_conversation)
        await self.session.commit()
        await self.session.refresh(new_conversation)
        return new_conversation
    
    async def update(self, conversation: Conversation, update_data: dict) -> Conversation:
        for key, value in update_data.items():
            setattr(conversation, key, value)
            
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation
    
    async def delete(self, conversation: Conversation) -> None:
        await self.session.delete(conversation)
        await self.session.commit()