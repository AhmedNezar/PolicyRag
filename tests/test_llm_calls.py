import asyncio
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from models import LLMStreamResponse, LLMUsage
from models.llm_calls import LLMCallType
from services.llm_calls import LLMCallService, TrackedLLM, TrackedEmbedding


class CallTrackingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = SimpleNamespace(create=AsyncMock())
        self.calls = LLMCallService(self.repo)
        self.usage = LLMUsage(prompt_tokens=309, response_tokens=75, total_tokens=384,
                              input_cost=Decimal("0.00004635"), output_cost=Decimal("0.000045"),
                              total_cost=Decimal("0.00009135"))
        self.provider = SimpleNamespace(provider="groq", model="test-model",
                                        generate=AsyncMock(return_value=("answer", self.usage)))
        self.context = dict(message_id=uuid4(), conversation_id=uuid4())

    async def test_generation_records_usage_and_context_once(self):
        result, usage = await TrackedLLM(self.provider, self.calls).generate(
            "system", [], schema_name="chat_router", **self.context)
        self.assertEqual(result, "answer")
        self.assertEqual(usage, self.usage)
        self.repo.create.assert_awaited_once()
        data = self.repo.create.await_args.args[0]
        self.assertEqual(data["call_type"], LLMCallType.GENERATION)
        self.assertEqual(data["purpose"], "chat_router")
        self.assertEqual(data["total_cost"], Decimal("0.00009135"))
        self.assertEqual(data["message_id"], self.context["message_id"])
        self.assertEqual(data["conversation_id"], self.context["conversation_id"])
        self.provider.generate.assert_awaited_once_with("system", [], None, "chat_router")

    async def test_title_has_conversation_but_no_message(self):
        await TrackedLLM(self.provider, self.calls).generate(
            "system", [], schema_name="title_generation", conversation_id=self.context["conversation_id"])
        data = self.repo.create.await_args.args[0]
        self.assertIsNone(data["message_id"])
        self.assertEqual(data["conversation_id"], self.context["conversation_id"])

    async def test_failure_preserves_available_usage_and_reraises(self):
        error = ValueError("sensitive provider message")
        error.usage = self.usage
        self.provider.generate.side_effect = error
        with self.assertRaises(ValueError):
            await TrackedLLM(self.provider, self.calls).generate("system", [])
        data = self.repo.create.await_args.args[0]
        self.assertFalse(data["is_success"])
        self.assertEqual(data["error_type"], "ValueError")
        self.assertEqual(data["total_cost"], self.usage.total_cost)
        self.assertNotIn("sensitive", str(data))

    async def test_embedding_unknown_usage_stays_null(self):
        provider = SimpleNamespace(provider="gemini", model="embedding-model",
                                   embed_index=AsyncMock(return_value=([[0.1]], LLMUsage())))
        result = await TrackedEmbedding(provider, self.calls).embed_index("doc", ["text"])
        self.assertEqual(result, [[0.1]])
        data = self.repo.create.await_args.args[0]
        self.assertEqual(data["call_type"], LLMCallType.EMBEDDING)
        self.assertEqual(data["purpose"], "document_index")
        for field in ("message_id", "conversation_id", "total_tokens", "total_cost"):
            self.assertIsNone(data[field])

    async def test_query_embedding_has_context(self):
        provider = SimpleNamespace(provider="gemini", model="embedding-model",
                                   embed_retrieve=AsyncMock(return_value=([0.1], LLMUsage(prompt_tokens=3))))
        result = await TrackedEmbedding(provider, self.calls).embed_retrieve("query", **self.context)
        self.assertEqual(result, [0.1])
        data = self.repo.create.await_args.args[0]
        self.assertEqual(data["purpose"], "query_embedding")
        self.assertEqual(data["message_id"], self.context["message_id"])

    async def test_stream_logs_once_before_terminal_is_delivered(self):
        async def stream(messages):
            yield LLMStreamResponse(type="data", content="Hi", raw_content="Hi")
            yield LLMStreamResponse(type="stop", content="", raw_content="", usage=self.usage)
        self.provider.stream = stream
        events = []
        async for chunk in TrackedLLM(self.provider, self.calls).stream([], **self.context):
            events.append(chunk.type)
            if chunk.type == "stop":
                self.repo.create.assert_awaited_once()
        self.assertEqual(events, ["data", "stop"])
        self.assertEqual(self.repo.create.await_args.args[0]["total_tokens"], 384)

    async def test_abrupt_stream_is_failed_not_free_success(self):
        async def stream(messages):
            yield LLMStreamResponse(type="data", content="Hi", raw_content="Hi")
        self.provider.stream = stream
        with self.assertRaises(RuntimeError):
            _ = [chunk async for chunk in TrackedLLM(self.provider, self.calls).stream([])]
        self.repo.create.assert_awaited_once()
        data = self.repo.create.await_args.args[0]
        self.assertFalse(data["is_success"])
        self.assertIsNone(data["total_cost"])

    async def test_stream_close_records_partial_usage(self):
        async def stream(messages):
            yield LLMStreamResponse(type="data", content="Hi", raw_content="Hi", usage=self.usage)
            yield LLMStreamResponse(type="stop", content="", raw_content="", usage=self.usage)
        self.provider.stream = stream
        stream = TrackedLLM(self.provider, self.calls).stream([])
        await anext(stream)
        await stream.aclose()
        self.repo.create.assert_awaited_once()
        data = self.repo.create.await_args.args[0]
        self.assertFalse(data["is_success"])
        self.assertEqual(data["total_tokens"], 384)

    async def test_cancelled_generation_is_recorded(self):
        self.provider.generate.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await TrackedLLM(self.provider, self.calls).generate("system", [])
        data = self.repo.create.await_args.args[0]
        self.assertFalse(data["is_success"])
        self.assertEqual(data["error_type"], "CancelledError")

    async def test_database_failure_is_not_relogged_as_provider_failure(self):
        self.repo.create.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            await TrackedLLM(self.provider, self.calls).generate("system", [])
        self.repo.create.assert_awaited_once()
