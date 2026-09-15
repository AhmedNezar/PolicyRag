from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from models import LLMUsage, MessageStatus
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
    assert message.usage == LLMUsage()


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
async def test_complete_message_saves_usage(
    message_service,
    message_repo,
):
    message_id = uuid4()
    usage = LLMUsage(
        prompt_tokens=5,
        response_tokens=10,
        total_tokens=15,
    )

    await message_service.complete_message(
        message_id,
        "Complete response",
        usage,
    )

    message_repo.update.assert_awaited_once_with(
        message_id,
        {
            "response_content": "Complete response",
            "prompt_tokens": 5,
            "response_tokens": 10,
            "total_tokens": 15,
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
    )

    message_repo.update.assert_awaited_once_with(
        message_id,
        {
            "response_content": "Partial response",
            "status": MessageStatus.FAILED,
            "is_success": False,
        },
    )