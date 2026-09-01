from repositories import MessageRepository
from entities import Message, Conversation
from models import LLMResponse, LLMUsage
from uuid import UUID
from models import MessageStatus

class MessageService:
    
    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo
        
    async def create_message(self, conversation: Conversation, prompt: str) -> Message:
        new_message = LLMResponse(
            prompt_content=prompt,
            response_content="",
            usage=LLMUsage()
        )
        
        message = await self.message_repo.create(new_message, conversation.id)
        return message
    
    async def update_message(self, message_id: UUID, response: str) -> Message:
        message = await self.message_repo.update(
            message_id, {"response_content": response, "status": MessageStatus.STREAMING}
        )
        return message
    
    
    async def complete_message(self, message_id: UUID, response: str, usage: LLMUsage) -> Message:            
        completed_message = {
            "response_content": response,
            "prompt_tokens": usage.prompt_tokens,
            "response_tokens": usage.response_tokens,
            "total_tokens": usage.total_tokens,
            "status": MessageStatus.COMPLETED,
            "is_success": True
        }
        
        message = await self.message_repo.update(message_id, completed_message)
        return message
    
    async def fail_message(self, message_id: UUID, response: str) -> Message:
        message = await self.message_repo.update(message_id, {
            "response_content": response, 
            "status": MessageStatus.FAILED, 
            "is_success": False
        })
        return message