import asyncio
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from config import load_pricing
from models.chat import ChatIntents
from providers.router.JavRouter import JavRouter
from providers.router.LLMRouter import LLMRouter
from models.chat import ChatRouter
from services.llm_calls import LLMCallService
from services.router import RouterService


class JavRouterTrackingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = SimpleNamespace(create=AsyncMock())
        self.client = AsyncMock()
        self.client.__aenter__.return_value = self.client
        self.response = SimpleNamespace(
            model="jev-1.13.0",
            usage=SimpleNamespace(input_tokens=618, output_tokens=52),
            answers={"intent": SimpleNamespace(choice="policy_question", confidence=0.99)},
        )
        self.client.system_one.return_value = self.response
        with patch("providers.router.JavRouter.AsyncTypeSafeClient", return_value=self.client):
            self.router = JavRouter(
                SimpleNamespace(TYPESAFE_API_KEY="test", TYPESAFE_MODEL="jev-1.13.0"),
                calls=LLMCallService(self.repo),
                pricing=load_pricing()["typesafe"]["jev-1.13.0"],
            )
        self.context = dict(message_id=uuid4(), conversation_id=uuid4())

    async def test_records_tokens_cost_and_context(self):
        result = await self.router.route("Which policy covers emergency access?", **self.context)
        self.assertEqual(result, (ChatIntents.POLICY_QUESTION, 0.99))
        self.repo.create.assert_awaited_once()
        data = self.repo.create.await_args.args[0]
        self.assertEqual(data["provider"], "typesafe")
        self.assertEqual(data["model"], "jev-1.13.0")
        self.assertEqual(data["purpose"], "intent_router")
        self.assertEqual(data["prompt_tokens"], 618)
        self.assertEqual(data["response_tokens"], 52)
        self.assertEqual(data["total_tokens"], 670)
        self.assertEqual(data["input_cost"], Decimal("0.000025956"))
        self.assertEqual(data["output_cost"], Decimal("0"))
        self.assertEqual(data["total_cost"], Decimal("0.000025956"))
        self.assertTrue(data["is_success"])
        for key, value in self.context.items():
            self.assertEqual(data[key], value)
        self.assertEqual(self.client.system_one.await_args.kwargs["model"], "jev-1.13.0")

    async def test_failed_call_keeps_unknown_cost_null(self):
        self.client.system_one.side_effect = RuntimeError("private upstream details")
        with self.assertRaises(RuntimeError):
            await self.router.route("hello", **self.context)
        self.repo.create.assert_awaited_once()
        data = self.repo.create.await_args.args[0]
        self.assertFalse(data["is_success"])
        self.assertEqual(data["error_type"], "RuntimeError")
        self.assertIsNone(data["total_cost"])
        self.assertNotIn("private upstream details", str(data))

    async def test_invalid_choice_preserves_billed_usage(self):
        self.response.answers["intent"].choice = "invalid"
        with self.assertRaises(ValueError):
            await self.router.route("hello")
        data = self.repo.create.await_args.args[0]
        self.assertFalse(data["is_success"])
        self.assertEqual(data["total_cost"], Decimal("0.000025956"))

    async def test_upstream_failure_preserves_available_usage(self):
        error = RuntimeError("upstream failure")
        error.usage = self.response.usage
        self.client.system_one.side_effect = error
        with self.assertRaises(RuntimeError):
            await self.router.route("hello")
        self.assertEqual(self.repo.create.await_args.args[0]["total_cost"], Decimal("0.000025956"))

    async def test_cancelled_call_is_recorded(self):
        self.client.system_one.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.router.route("hello")
        self.assertEqual(self.repo.create.await_args.args[0]["error_type"], "CancelledError")

    async def test_record_failure_is_not_recorded_twice(self):
        self.repo.create.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            await self.router.route("hello")
        self.repo.create.assert_awaited_once()

    async def test_missing_usage_is_not_reported_as_free(self):
        self.response.usage = None
        await self.router.route("hello")
        self.assertIsNone(self.repo.create.await_args.args[0]["total_cost"])

    async def test_service_forwards_context_to_main_and_fallback(self):
        self.response.answers["intent"].confidence = 0.4
        fallback = SimpleNamespace(route=AsyncMock(return_value=(ChatIntents.POLICY_QUESTION, 0.9)))
        await RouterService(self.router, fallback).route("Which policy?", [], **self.context)
        fallback.route.assert_awaited_once_with("Which policy?", **self.context)
        self.assertEqual(self.repo.create.await_args.args[0]["message_id"], self.context["message_id"])

    async def test_confident_route_does_not_call_fallback(self):
        fallback = SimpleNamespace(route=AsyncMock())
        await RouterService(self.router, fallback).route("Which policy?", [], **self.context)
        fallback.route.assert_not_awaited()

    async def test_llm_fallback_forwards_tracking_context(self):
        model = SimpleNamespace(generate=AsyncMock(return_value=(
            ChatRouter(route=ChatIntents.POLICY_QUESTION, confidence=0.9), None,
        )))
        result = await LLMRouter(model).route("Which policy?", **self.context)
        self.assertEqual(result, (ChatIntents.POLICY_QUESTION, 0.9))
        for key, value in self.context.items():
            self.assertEqual(model.generate.await_args.kwargs[key], value)
