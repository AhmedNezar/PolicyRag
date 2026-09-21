import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from services.chat import ChatService


class ChatUsageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.conversation = SimpleNamespace(id=uuid4(), title="Leave")
        self.message = SimpleNamespace(id=uuid4())
        self.model = SimpleNamespace(stream=AsyncMock())
        self.messages = SimpleNamespace(create_message=AsyncMock(return_value=self.message),
                                        complete_message=AsyncMock(), fail_message=AsyncMock(),
                                        cancel_message=AsyncMock())
        self.guardrail = SimpleNamespace(route=AsyncMock(return_value=("system", "leave", True, False)))
        self.embedding = SimpleNamespace(embed_retrieve=AsyncMock(return_value=[0.1]))
        self.cache = SimpleNamespace(retrieve=AsyncMock(return_value="Cached answer"))
        self.service = ChatService(
            self.model, SimpleNamespace(STREAM_UPDATE_SEC=4),
            SimpleNamespace(get_messages=AsyncMock(return_value=[])), self.messages,
            SimpleNamespace(get_conversation=AsyncMock(return_value=self.conversation)),
            self.guardrail, SimpleNamespace(retrieve=AsyncMock()), self.embedding, self.cache)

    async def test_cache_hit_skips_generation_but_links_real_calls(self):
        events = [event async for event in self.service.stream("leave", self.conversation.id, uuid4())]
        self.model.stream.assert_not_called()
        context = dict(message_id=self.message.id, conversation_id=self.conversation.id)
        self.guardrail.route.assert_awaited_once_with("leave", [], **context)
        self.embedding.embed_retrieve.assert_awaited_once_with(query="leave", **context)
        args = self.messages.complete_message.await_args.args
        self.assertEqual(len(args), 3)  # id, content, latency; no usage on messages
        self.assertEqual(args[1], "Cached answer")
        self.assertTrue(any("event: done" in event for event in events))

    async def test_router_failure_marks_message_failed(self):
        self.guardrail.route.side_effect = RuntimeError("router unavailable")
        events = [event async for event in self.service.stream("leave", self.conversation.id, uuid4())]
        self.messages.fail_message.assert_awaited_once()
        self.embedding.embed_retrieve.assert_not_called()
        self.assertTrue(any("event: error" in event for event in events))
