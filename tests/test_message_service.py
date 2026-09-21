from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from models import LLMLatency, MessageStatus
from services.message import MessageService


@pytest.fixture
def message_repo():
    return SimpleNamespace(
        create=AsyncMock(),
        update=AsyncMock(),
    )


@pytest.fixture
def message_service(message_repo):
    return MessageService(message_repo)


@pytest.mark.asyncio
async def test_create_message(message_service, message_repo):
    conversation = SimpleNamespace(id=uuid4())

    await message_service.create_message(conversation, "Hello")

    message, conversation_id = message_repo.create.await_args.args

    assert conversation_id == conversation.id
    assert message.prompt_content == "Hello"
    assert message.response_content == ""
    assert message.usage is None


@pytest.mark.asyncio
async def test_update_message_marks_it_as_streaming(
    message_service,
    message_repo,
):
    message_id = uuid4()

    await message_service.update_message(
        message_id,
        "Partial response",
    )

    message_repo.update.assert_awaited_once_with(
        message_id,
        {
            "response_content": "Partial response",
            "status": MessageStatus.STREAMING,
        },
    )


@pytest.mark.asyncio
async def test_complete_message_saves_latency_without_usage(
    message_service,
    message_repo,
):
    message_id = uuid4()
    latency = LLMLatency(ttft=0.1, total_time=0.3)

    await message_service.complete_message(
        message_id,
        "Complete response",
        latency,
    )

    message_repo.update.assert_awaited_once_with(
        message_id,
        {
            "response_content": "Complete response",
            "ttft": 0.1,
            "total_time": 0.3,
            "status": MessageStatus.COMPLETED,
            "is_success": True,
        },
    )


@pytest.mark.asyncio
async def test_fail_message_preserves_partial_response(
    message_service,
    message_repo,
):
    message_id = uuid4()

    await message_service.fail_message(
        message_id,
        "Partial response",
        LLMLatency(ttft=None, total_time=0.2),
    )

    message_repo.update.assert_awaited_once_with(
        message_id,
        {
            "response_content": "Partial response",
            "ttft": None,
            "total_time": 0.2,
            "status": MessageStatus.FAILED,
            "is_success": False,
        },
    )
