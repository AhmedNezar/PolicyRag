from repositories import MessageRepository
from entities import Message, Conversation
from models import LLMResponse, LLMLatency, MessageStatus
from uuid import UUID

class MessageService:

    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo

    async def create_message(self, conversation: Conversation, prompt: str) -> Message:
        new_message = LLMResponse(
            prompt_content=prompt,
            response_content="",
        )

        message = await self.message_repo.create(new_message, conversation.id)
        return message

    async def update_message(self, message_id: UUID, response: str) -> Message:
        message = await self.message_repo.update(
            message_id, {"response_content": response, "status": MessageStatus.STREAMING}
        )
        return message


    async def complete_message(self, message_id: UUID, response: str, latency: LLMLatency) -> Message:
        completed_message = {
            "response_content": response,
            "status": MessageStatus.COMPLETED,
            "ttft": latency.ttft,
            "total_time": latency.total_time,
            "is_success": True
        }

        message = await self.message_repo.update(message_id, completed_message)
        return message

    async def fail_message(self, message_id: UUID, response: str, latency: LLMLatency) -> Message:
        message = await self.message_repo.update(message_id, {
            "response_content": response,
            "status": MessageStatus.FAILED,
            "ttft": latency.ttft,
            "total_time": latency.total_time,
            "is_success": False
        })
        return message

    async def cancel_message(self, message_id: UUID, response: str, latency: LLMLatency) -> Message:
        return await self.message_repo.update(message_id, {
            "response_content": response,
            "status": MessageStatus.CANCELLED,
            "ttft": latency.ttft,
            "total_time": latency.total_time,
            "is_success": False,
        })
