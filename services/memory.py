from .conversations import ConversationService
from uuid import UUID

class MemoryService:
    
    def __init__(self, conversation_service: ConversationService):
        self.conversation_service = conversation_service
        
    async def get_messages(self, conversation_id: UUID):
        messages = await self.conversation_service.list_messages(conversation_id)
        all_messages = []
        for message in messages:
            all_messages.append({"role": "user", "content": message.prompt_content})
            all_messages.append({"role": "assistant", "content": message.response_content})
        return all_messages