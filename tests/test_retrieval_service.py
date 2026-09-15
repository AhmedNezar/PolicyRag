from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from infrastructure.prompts import REWRITE_PROMPT
from models.chat import QueryRewrite
from services.rag.retrieval import RetrievalService


@pytest.fixture
def chunk_repo():
    return SimpleNamespace(search=AsyncMock())


@pytest.fixture
def model():
    return SimpleNamespace(generate=AsyncMock())


@pytest.fixture
def retrieval_service(chunk_repo, model):
    return RetrievalService(chunk_repo=chunk_repo, model=model)


@pytest.mark.asyncio
async def test_retrieve_returns_chunk_content(retrieval_service, chunk_repo):
    embeddings = [0.1, 0.2, 0.3]
    chunk_repo.search.return_value = [
        SimpleNamespace(content="First policy section"),
        SimpleNamespace(content="Second policy section"),
    ]

    result = await retrieval_service.retrieve(embeddings)

    assert result == ["First policy section", "Second policy section"]
    chunk_repo.search.assert_awaited_once_with(embeddings)


@pytest.mark.asyncio
async def test_retrieve_returns_empty_list_when_no_chunks_exist(
    retrieval_service,
    chunk_repo,
):
    chunk_repo.search.return_value = []

    result = await retrieval_service.retrieve([0.1, 0.2])

    assert result == []


@pytest.mark.asyncio
async def test_rewrite_returns_generated_query(retrieval_service, model):
    model.generate.return_value = QueryRewrite(query="annual leave policy")
    history = [
        {"role": "user", "content": "Tell me about leave"},
        {"role": "assistant", "content": "Which type of leave?"},
    ]

    result = await retrieval_service.rewrite(history, "Annual leave")

    assert result == "annual leave policy"
    model.generate.assert_awaited_once()
    system_prompt, messages, schema, schema_name = model.generate.await_args.args
    assert system_prompt == REWRITE_PROMPT
    assert schema is QueryRewrite
    assert schema_name == "query_rewrite"
    assert "user: Tell me about leave" in messages[0]["content"]
    assert "assistant: Which type of leave?" in messages[0]["content"]
    assert "Annual leave" in messages[0]["content"]


@pytest.mark.asyncio
async def test_rewrite_uses_only_ten_most_recent_messages(
    retrieval_service,
    model,
):
    model.generate.return_value = QueryRewrite(query="rewritten")
    history = [
        {"role": "user", "content": f"message-{index}"}
        for index in range(12)
    ]

    await retrieval_service.rewrite(history, "latest question")

    conversation = model.generate.await_args.args[1][0]["content"]
    assert "message-0\n" not in conversation
    assert "message-1\n" not in conversation
    for index in range(2, 12):
        assert f"message-{index}" in conversation
