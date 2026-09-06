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
import time
from models import LLMUsage

class ChatService:
    def __init__(self, model: LLMInterface, settings: Settings, memory_service: MemoryService,
                 message_service: MessageService, conversation_service: ConversationService,
                 guardrail: GuardrailService, retrieval_service: RetrievalService):
        self.model = model
        self.settings = settings
        self.memory_service = memory_service
        self.message_service = message_service
        self.conversation_service = conversation_service
        self.guardrail = guardrail
        self.retrieval_service = retrieval_service
    
    async def stream(self, message: str, conversation_id: UUID | None, user_id: UUID) -> AsyncGenerator[str, None]:
        history = []
        conversation = await self.conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            conversation = await self.conversation_service.new_chat_conversation(message, user_id)
        else:
            history = await self.memory_service.get_messages(conversation_id)
            
        new_message = await self.message_service.create_message(conversation, message)
        
        system_message, user_message, needs_retrieval, followup = await self.guardrail.route(message,  history[-4:])
        context_chunks = await self.retrieval_service.retrieve(user_message, history=history, rewrite=followup) if needs_retrieval else []
        
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
                        yield "event: token\n" + chunk.content
                        full_response += chunk.raw_content
                        
                        if time.monotonic() - last_saved_time >= self.settings.STREAM_UPDATE_SEC:
                            _ = await self.message_service.update_message(new_message.id, full_response)
                            last_saved_time = time.monotonic()
                        
                else:
                    usage = chunk.usage if chunk.usage else LLMUsage()
                    _ = await self.message_service.complete_message(new_message.id, full_response, usage)

                    conversation_data = json.dumps({
                        "title": conversation.title,
                        "conversation_id": str(conversation.id)
                    })
                    yield f"event: conversation\ndata: {conversation_data}\n\n"
                    yield "event: done\ndata: [DONE]\n\n"
        except Exception:
            _ = await self.message_service.fail_message(new_message.id, full_response)
            yield f"event: error\ndata: Provider failed\n\n"
        