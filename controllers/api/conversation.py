from typing import Annotated
from infrastructure.dependencies import ConversationServiceDep
from entities import Conversation
from fastapi import Depends, HTTPException, status, APIRouter
from .schemas.Conversation import ConversationOut, ConversationCreate, ConversationUpdate
from .schemas.Message import MessageOut
from .auth import AuthenticateUserDep
from uuid import UUID

conversation_router = APIRouter(
    prefix="/conversations"
)


async def get_conversation_by_id(
    conversation_id: UUID,
    service: ConversationServiceDep,
    user: AuthenticateUserDep
) -> Conversation:
    conversation = await service.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation


GetConversationDep = Annotated[Conversation, Depends(get_conversation_by_id)]


@conversation_router.get("/")
async def list_conversations(
    service: ConversationServiceDep,
    user: AuthenticateUserDep,
    skip: int = 0,
    take: int = 100
) -> list[ConversationOut]:
    conversations = await service.list_conversations(skip, take, user.id)
    
    return [
        ConversationOut.model_validate(conversation)
        for conversation in conversations
    ]

@conversation_router.get("/{conversation_id}")
async def get_conversation(conversation: GetConversationDep) -> ConversationOut:
    return ConversationOut.model_validate(conversation)

@conversation_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    service: ConversationServiceDep,
    user: AuthenticateUserDep
) -> ConversationOut:
    conversation_data = conversation.model_dump()
    conversation_data["user_id"] = user.id
    new_conversation = await service.create_conversation(conversation_data)  
    return ConversationOut.model_validate(new_conversation)

@conversation_router.put("/{conversation_id}", status_code=status.HTTP_202_ACCEPTED)
async def update_conversation(
    conversation: GetConversationDep,
    update_conversation: ConversationUpdate,
    service: ConversationServiceDep,
) -> ConversationOut:
    updated_conversation = await service.update_conversation(
        conversation,
        update_conversation.model_dump(exclude_unset=True),
    )
    return ConversationOut.model_validate(updated_conversation) 

@conversation_router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation: GetConversationDep, service: ConversationServiceDep) -> None:
    await service.delete_conversation(conversation)
    
@conversation_router.get("/{conversation_id}/messages")
async def list_conversation_messages_controller(
    conversation: GetConversationDep,
    service: ConversationServiceDep,
) -> list[MessageOut]:
    messages = await service.list_messages(conversation.id)
    return [MessageOut.model_validate(m) for m in messages]

@conversation_router.get("/{conversation_id}/title")
async def get_conversation_title(
    conversation_id: UUID,
    service: ConversationServiceDep,
    user: AuthenticateUserDep
) -> dict:
    title = await service.get_title(conversation_id=conversation_id, user_id=user.id)
    return {"title": title}
