from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from .schemas.Chat import ChatRequest
from .auth import AuthenticateUserDep
from uuid import UUID
from infrastructure.dependencies import ChatServiceDep

chat_router = APIRouter(
    prefix="/chat"
) 


@chat_router.post("/stream_new")
async def stream_new(request: Request, chat_request: ChatRequest, chat_service: ChatServiceDep, user: AuthenticateUserDep) -> StreamingResponse:

    return StreamingResponse(
        chat_service.stream(message=chat_request.message, conversation_id=None, user_id=user.id), media_type="text/event-stream"
    )
    
    
@chat_router.post("/stream/{conversation_id}")
async def stream(request: Request, chat_request: ChatRequest, conversation_id: UUID | None, chat_service: ChatServiceDep, user: AuthenticateUserDep) -> StreamingResponse:

    return StreamingResponse(
        chat_service.stream(message=chat_request.message, conversation_id=conversation_id, user_id=user.id), media_type="text/event-stream"
    )
    
@chat_router.post("/{conversation_id}")
async def generate(request: Request, chat_request: ChatRequest, conversation_id: UUID | None, chat_service: ChatServiceDep, user: AuthenticateUserDep):
    response = await chat_service.chat(message=chat_request.message, conversation_id=conversation_id, user_id=user.id)
    
    return JSONResponse(
        content={
            "response": response
        },
        status_code=status.HTTP_200_OK
    )