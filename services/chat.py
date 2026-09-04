from providers.llm.LLMInterface import LLMInterface
from typing import AsyncGenerator
from uuid import UUID
import json
from config import Settings
from .message import MessageService
from .memory import MemoryService
from .conversations import ConversationService
import time
from models import LLMUsage

class ChatService:
    def __init__(self, model: LLMInterface, settings: Settings, memory_service: MemoryService,
                 message_service: MessageService, conversation_service: ConversationService):
        self.model = model
        self.settings = settings
        self.memory_service = memory_service
        self.message_service = message_service
        self.conversation_service = conversation_service

        
    async def chat(self, message: str, conversation_id: UUID | None, user_id: UUID) -> str:
        conversation = await self.conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            conversation = await self.conversation_service.new_chat_conversation(message)
       
        full_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message}
        ]
        response = await self.model.generate(messages=full_messages)
        
        _, _ = await self.save_message(conversation, response, user_id)
        
        return response.response_content
    
    async def stream(self, message: str, conversation_id: UUID | None, user_id: UUID) -> AsyncGenerator[str, None]:
        all_messages = []
        conversation = await self.conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            conversation = await self.conversation_service.new_chat_conversation(message, user_id)
        else:
            all_messages = await self.memory_service.get_messages(conversation_id)
            
        new_message = await self.message_service.create_message(conversation, message)
         
        full_messages = [{"role": "system", "content": "You are a helpful assistant."}] + all_messages + [{"role": "user", "content": message}]
        
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
        