from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from entities import LLMCall


class LLMCallRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> LLMCall:
        call = LLMCall(**data)
        self.session.add(call)
        await self.session.commit()
        await self.session.refresh(call)
        return call

    async def list(self, *, message_id: UUID | None = None,
                   conversation_id: UUID | None = None,
                   skip: int = 0, take: int = 100) -> list[LLMCall]:
        statement = select(LLMCall)
        if message_id is not None:
            statement = statement.where(LLMCall.message_id == message_id)
        if conversation_id is not None:
            statement = statement.where(LLMCall.conversation_id == conversation_id)
        result = await self.session.execute(
            statement.order_by(LLMCall.created_at, LLMCall.id).offset(skip).limit(take))
        return list(result.scalars().all())
