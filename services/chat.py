from services.llm_calls import TrackedLLM
from typing import AsyncGenerator
from uuid import UUID
import json
from config import Settings
from .message import MessageService
from .memory import MemoryService
from .conversations import ConversationService
from .guardrail import GuardrailService
from .rag.retrieval import RetrievalService
from infrastructure.prompts import CONTEXT_PROMPT
from services.llm_calls import TrackedEmbedding
from providers.cache import RedisCache
import time
from contextlib import aclosing
from asyncio import CancelledError
from models import LLMLatency
from .router import RouterService

class ChatService:
    def __init__(self, model: TrackedLLM, settings: Settings, memory_service: MemoryService,
                 message_service: MessageService, conversation_service: ConversationService,
                 guardrail: GuardrailService, retrieval_service: RetrievalService, embedding_model: TrackedEmbedding,
                 cache: RedisCache, router: RouterService):
        self.model = model
        self.settings = settings
        self.memory_service = memory_service
        self.message_service = message_service
        self.conversation_service = conversation_service
        self.guardrail = guardrail
        self.retrieval_service = retrieval_service
        self.embedding_model = embedding_model
        self.cache = cache
        self.router = router

    async def stream(self, message: str, conversation_id: UUID | None, user_id: UUID) -> AsyncGenerator[str, None]:
        start_time = time.monotonic()
        history = []
        conversation = await self.conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            conversation = await self.conversation_service.new_chat_conversation(message, user_id)
        else:
            history = await self.memory_service.get_messages(conversation_id)
            
        is_safe = await self.guardrail.guard(message, conversation_id=conversation.id)
        if not is_safe:
            yield self.sse_event("token", "Sorry, but I can't help you with that.")
            conversation_data = json.dumps({
                "title": conversation.title,
                "conversation_id": str(conversation.id)
            })
            yield self.sse_event("conversation", conversation_data)
            yield self.sse_event("done", "[DONE]")
            return

        new_message = await self.message_service.create_message(conversation, message)
        call_context = {"message_id": new_message.id, "conversation_id": conversation.id}
        full_response = ""
        ttft = None
        completed = False
        try:
            system_message, followup, needs_retrieval = await self.router.route(message, history[-4:], **call_context)
            
            if history and followup:
                message = await self.retrieval_service.rewrite(history, message, **call_context)
            embeddings = None
            if needs_retrieval:
                embeddings = await self.embedding_model.embed_retrieve(query=message, **call_context)
                cached_response = await self.cache.retrieve(embeddings)
                if cached_response:
                    total_time = time.monotonic() - start_time
                    latency = LLMLatency(ttft=total_time, total_time=total_time)
                    yield self.sse_event("token", cached_response)
                    _ = await self.message_service.complete_message(new_message.id, cached_response, latency)
                    completed = True
                    conversation_data = json.dumps({
                        "title": conversation.title,
                        "conversation_id": str(conversation.id)
                    })
                    yield self.sse_event("conversation", conversation_data)
                    yield self.sse_event("done", "[DONE]")
                    return

            context_chunks = await self.retrieval_service.retrieve(embeddings) if embeddings else []

            full_messages = [{"role": "system", "content": system_message}]
            if context_chunks:
                context = "\n".join(context_chunks)
                full_messages.append({"role": "system", "content": CONTEXT_PROMPT.format(context=context)})
            if history:
                full_messages.extend(history)
            full_messages.append({"role": "user", "content": message})

            last_saved_time = time.monotonic()
            async with aclosing(self.model.stream(messages=full_messages, **call_context)) as answer_stream:
                async for chunk in answer_stream:
                    if chunk.type == "data":
                        if not chunk.raw_content:
                            continue

                        if ttft is None:
                            ttft = time.monotonic() - start_time

                        full_response += chunk.raw_content
                        yield self.sse_event("token", chunk.raw_content)

                        if time.monotonic() - last_saved_time >= self.settings.STREAM_UPDATE_SEC:
                            _ = await self.message_service.update_message(new_message.id, full_response)
                            last_saved_time = time.monotonic()

                    else:
                        total_time = time.monotonic() - start_time
                        latency = LLMLatency(ttft=ttft, total_time=total_time)
                        _ = await self.message_service.complete_message(new_message.id, full_response, latency)
                        completed = True

                        if needs_retrieval and context_chunks:
                            await self.cache.add(message, full_response, embeddings)

                        conversation_data = json.dumps({
                            "title": conversation.title,
                            "conversation_id": str(conversation.id)
                        })
                        yield self.sse_event("conversation", conversation_data)
                        yield self.sse_event("done", "[DONE]")
        except (CancelledError, GeneratorExit):
            if not completed:
                await self.message_service.cancel_message(
                    new_message.id, full_response,
                    LLMLatency(ttft=ttft, total_time=time.monotonic() - start_time))
            raise
        except Exception as e:
            print(e)
            total_time = time.monotonic() - start_time
            latency = LLMLatency(ttft=ttft, total_time=total_time)
            _ = await self.message_service.fail_message(new_message.id, full_response, latency)
            yield self.sse_event("error", "Provider failed")

    def sse_event(self, event: str, data: str) -> str:
        lines = str(data).splitlines()

        if not lines:
            return f"event: {event}\ndata:\n\n"

        data_block = "\n".join(f"data: {line}" for line in lines)
        return f"event: {event}\n{data_block}\n\n"
