import pytest
from types import SimpleNamespace
from uuid import uuid4

from services.chat import ChatService
from services.conversations import ConversationService
from services.memory import MemoryService
from services.message import MessageService
from repositories import ConversationRepository, MessageRepository
from infrastructure.database import Database
from config import get_settings
from entities import Message, User
from models import LLMStreamResponse, LLMUsage, MessageStatus
from sqlalchemy import select


class FailingProvider:
    async def generate_title(self, message):
        return "Failure Test Conversation"

    async def stream(self, messages):
        yield LLMStreamResponse(
            type="data",
            content="data: Hello\n\n",
            raw_content="Hello",
            done=False,
        )

        yield LLMStreamResponse(
            type="data",
            content="data: world\n\n",
            raw_content=" world",
            done=False,
        )

        raise RuntimeError("Provider crashed")


class FakeConversationService:
    async def get_conversation(self, conversation_id, user_id):
        return SimpleNamespace(id=conversation_id, title="Test Conversation")

    async def new_chat_conversation(self, message, user_id):
        return SimpleNamespace(id=uuid4(), title="New Conversation")


class FakeMemoryService:
    async def get_messages(self, conversation_id):
        return []


class FakeMessageService:
    def __init__(self):
        self.created_message_id = uuid4()
        self.failed = None
        self.updated = []
        self.completed = []

    async def create_message(self, conversation, prompt):
        return SimpleNamespace(id=self.created_message_id)

    async def update_message(self, message_id, response):
        self.updated.append((message_id, response))

    async def complete_message(self, message_id, response, usage):
        self.completed.append((message_id, response, usage))

    async def fail_message(self, message_id, response):
        self.failed = (message_id, response)


@pytest.mark.asyncio
async def test_stream_marks_message_failed_when_provider_crashes():
    message_service = FakeMessageService()

    chat_service = ChatService(
        model=FailingProvider(),
        settings=SimpleNamespace(STREAM_UPDATE_SEC=999),
        memory_service=FakeMemoryService(),
        message_service=message_service,
        conversation_service=FakeConversationService(),
    )

    events = []

    async for event in chat_service.stream(
        message="hello",
        conversation_id=uuid4(),
        user_id=uuid4(),
    ):
        events.append(event)

    assert "data: Hello" in events[0]
    assert "data: world" in events[1]
    assert events[-1] == "event: error\ndata: Provider failed\n\n"

    assert message_service.failed == (
        message_service.created_message_id,
        "Hello world",
    )
    assert message_service.completed == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stream_provider_failure_is_saved_in_database():
    settings = get_settings()
    db = Database(settings)
    user = None

    try:
        async with db.async_session() as session:
            user = User(
                username=f"stream_failure_{uuid4()}",
                hashed_password="not-used-in-this-test",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            message_repo = MessageRepository(session)
            conversation_repo = ConversationRepository(session)

            conversation_service = ConversationService(
                conversation_repo,
                message_repo,
                settings,
                FailingProvider(),
            )
            message_service = MessageService(message_repo)
            memory_service = MemoryService(conversation_service)

            chat_service = ChatService(
                model=FailingProvider(),
                settings=settings,
                memory_service=memory_service,
                message_service=message_service,
                conversation_service=conversation_service,
            )

            events = [
                event
                async for event in chat_service.stream(
                    message="hello",
                    conversation_id=None,
                    user_id=user.id,
                )
            ]

            result = await session.execute(
                select(Message).where(Message.prompt_content == "hello")
            )
            saved_message = result.scalars().one()

            assert events[-1] == "event: error\ndata: Provider failed\n\n"
            assert saved_message.response_content == "Hello world"
            assert saved_message.status == MessageStatus.FAILED
            assert saved_message.is_success is False
            assert saved_message.prompt_tokens is None
            assert saved_message.response_tokens is None
            assert saved_message.total_tokens is None
    finally:
        if user:
            async with db.async_session() as cleanup_session:
                user_in_db = await cleanup_session.get(User, user.id)
                if user_in_db:
                    await cleanup_session.delete(user_in_db)
                    await cleanup_session.commit()

        await db.dispose()
