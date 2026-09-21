from providers.llm.LLMInterface import LLMInterface
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
from providers.embedding import EmbeddingInterface
from providers.cache import RedisCache
import time
from models import LLMUsage

class ChatService:
    def __init__(self, model: LLMInterface, settings: Settings, memory_service: MemoryService,
                 message_service: MessageService, conversation_service: ConversationService,
                 guardrail: GuardrailService, retrieval_service: RetrievalService, embedding_model: EmbeddingInterface,
                 cache: RedisCache):
        self.model = model
        self.settings = settings
        self.memory_service = memory_service
        self.message_service = message_service
        self.conversation_service = conversation_service
        self.guardrail = guardrail
        self.retrieval_service = retrieval_service
        self.embedding_model = embedding_model
        self.cache = cache
    
    async def stream(self, message: str, conversation_id: UUID | None, user_id: UUID) -> AsyncGenerator[str, None]:
        history = []
        conversation = await self.conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            conversation = await self.conversation_service.new_chat_conversation(message, user_id)
        else:
            history = await self.memory_service.get_messages(conversation_id)
        
        system_message, user_message, needs_retrieval, followup = await self.guardrail.route(message,  history[-4:])
        
        if history and followup:
            user_message = await self.retrieval_service.rewrite(history, user_message)
        
        new_message = await self.message_service.create_message(conversation, message)
        print("Message created")
        print(new_message.id)
        
        embeddings = None
        if needs_retrieval:
            embeddings = await self.embedding_model.embed_retrieve(query=user_message)
            cached_response = await self.cache.retrieve(embeddings)
            if cached_response:
                yield self.sse_event("token", cached_response)
                usage = LLMUsage(
                    prompt_tokens=0,
                    response_tokens=0,
                    total_tokens=0,
                    input_cost=0,
                    output_cost=0,
                    total_cost=0
                )
                _ = await self.message_service.complete_message(new_message.id, cached_response, usage)
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
        full_messages.append({"role": "user", "content": user_message})
        
        full_response = ""
        last_saved_time = time.monotonic()
        try:
            async for chunk in self.model.stream(messages=full_messages):
                if chunk.type == "data":     
                    if not chunk.done:
                        yield self.sse_event("token", chunk.raw_content)
                        full_response += chunk.raw_content
                        
                        if time.monotonic() - last_saved_time >= self.settings.STREAM_UPDATE_SEC:
                            _ = await self.message_service.update_message(new_message.id, full_response)
                            last_saved_time = time.monotonic()
                        
                else:
                    usage = chunk.usage if chunk.usage else LLMUsage()
                    _ = await self.message_service.complete_message(new_message.id, full_response, usage)
                    if needs_retrieval and context_chunks:
                        await self.cache.add(user_message, full_response, embeddings)

                    conversation_data = json.dumps({
                        "title": conversation.title,
                        "conversation_id": str(conversation.id)
                    })
                    yield self.sse_event("conversation", conversation_data)
                    yield self.sse_event("done", "[DONE]")
        except Exception as e:
            print(e)
            _ = await self.message_service.fail_message(new_message.id, full_response)
            yield self.sse_event("error", "Provider failed")
        
    def sse_event(self, event: str, data: str) -> str:
        lines = str(data).splitlines()

        if not lines:
            return f"event: {event}\ndata:\n\n"

        data_block = "\n".join(f"data: {line}" for line in lines)
        return f"event: {event}\n{data_block}\n\n"