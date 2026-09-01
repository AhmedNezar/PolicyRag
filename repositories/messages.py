from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from entities import Message
from models import LLMResponse, MessageStatus
from uuid import UUID
from datetime import datetime, UTC

class MessageRepository:
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def list(self, skip: int = 0, take: int = 0) -> list[Message]:
        result = await self.session.execute(
            select(Message).offset(skip).limit(take)
        )
        
        return result.scalars().all()
    
    async def list_conversation_messages(self, conversation_id: UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        )
        return result.scalars().all()
    
    async def get(self, message_id: UUID) -> Message | None:
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        
        return result.scalars().first()
    
    async def create(self, llm_response: LLMResponse, conversation_id: UUID) -> Message:
        new_message = Message(
            conversation_id=conversation_id,
            prompt_content=llm_response.prompt_content,
            response_content=llm_response.response_content,
            prompt_tokens=llm_response.usage.prompt_tokens,
            response_tokens=llm_response.usage.response_tokens,
            total_tokens=llm_response.usage.total_tokens,
            is_success=llm_response.is_success,
            status=MessageStatus.PENDING
        )
        self.session.add(new_message)
        await self.session.commit()
        await self.session.refresh(new_message)
        return new_message
    
    async def update(self, id: UUID, updated_message: dict) -> Message:
        message = await self.get(message_id=id)
        if not message:
            return None
        
        for key, value in updated_message.items():
            setattr(message, key, value)
            
        await self.session.commit()
        await self.session.refresh(message)
        return message
    
    async def delete(self, id: UUID) -> None:
        message = await self.get(message_id=id)
        if not message:
            return None
        
        await self.session.delete(message)
        await self.session.commit()
        
    async def resolve_stale_messages(self, conversation_id: UUID, cutoff: datetime) -> None:
        stmt = (
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.updated_at < cutoff,
                Message.status.in_([MessageStatus.STREAMING, MessageStatus.PENDING]),
            )
            .values(
                status=MessageStatus.FAILED,
                is_success=False,
                updated_at=datetime.now(UTC)
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()
        
