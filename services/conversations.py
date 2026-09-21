from entities import Conversation, Message
from repositories import ConversationRepository, MessageRepository
import asyncio
from uuid import UUID
from exceptions import UnauthorizedException
from config import Settings
from services.llm_calls import TrackedLLM
from models import TitleSummarization
from datetime import datetime, UTC, timedelta


class ConversationService:
    def __init__(self, repository: ConversationRepository, message_repo: MessageRepository, settings: Settings, model: TrackedLLM):
        self.repository = repository
        self.message_repo = message_repo
        self.settings = settings
        self.model = model

    async def list_conversations(self, skip: int, take: int, user_id: UUID) -> list[Conversation]:
        return await self.repository.list(user_id, skip, take)

    async def get_conversation(self, conversation_id: UUID | None, user_id: UUID) -> Conversation | None:
        if not conversation_id:
            return None
        conversation = await self.repository.get(conversation_id)
        if conversation and conversation.user_id != user_id:
            raise UnauthorizedException
        return conversation

    async def new_chat_conversation(self, message: str, user_id: UUID) -> Conversation:
        conversation = await self.repository.create({
            "title": "New conversation",
            "model_type": self.settings.MODEL_NAME,
            "user_id": user_id,
        })
        result, _ = await self.model.generate(
            system_message="Generate a concise conversation title based on the user's message.",
            user_messages=[{"role": "user", "content": message}],
            output_schema=TitleSummarization,
            schema_name="title_generation",
            conversation_id=conversation.id,
        )
        return await self.repository.update(conversation, {"title": result.title})

    async def create_conversation(self, conversation_data: dict) -> Conversation:
        return await self.repository.create(conversation_data)

    async def update_conversation(
        self,
        conversation: Conversation,
        update_data: dict,
    ) -> Conversation:
        return await self.repository.update(conversation, update_data)

    async def delete_conversation(self, conversation: Conversation) -> None:
        await self.repository.delete(conversation)

    async def list_messages(self, conversation_id: UUID) -> list[Message]:
        cutoff = datetime.now(UTC) - timedelta(seconds=self.settings.CUTOFF_SEC)
        await self.message_repo.resolve_stale_messages(conversation_id, cutoff)
        messages = await self.message_repo.list_conversation_messages(conversation_id)
        return messages

    async def get_title(self, conversation_id: UUID, user_id: UUID) -> str:
        max_retries = 5
        for _ in range(max_retries):
            conversation = await self.get_conversation(conversation_id=conversation_id, user_id=user_id)
            if not conversation:
                await asyncio.sleep(2)
            else:
                return conversation.title
        return "Failed to get title"
