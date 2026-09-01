from .database import Database
from config import get_settings
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from providers.LLMFactory import LLMFactory
from providers.LLMInterface import LLMInterface
from config import get_settings, Settings
from services import ChatService, PasswordService, TokenService, AuthService, ConversationService, MemoryService, MessageService
from repositories import ConversationRepository, TokenRepository, UserRepository, MessageRepository

_model: LLMInterface | None = None

db = Database(settings=get_settings())
SettingsDep = Annotated[Settings, Depends(get_settings)]

async def get_db_session():
    try:
        async with db.async_session() as session:
            yield session
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()
        
DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
        
def get_model():
    global _model
    if not _model:
        _model = LLMFactory(settings=get_settings()).create()
    return _model

ModelDep = Annotated[LLMInterface, Depends(get_model)]

def get_password_service() -> PasswordService:
    return PasswordService()

PasswordServiceDep = Annotated[PasswordService, Depends(get_password_service)]

def get_token_repo(session: DBSessionDep) -> TokenRepository:
    return TokenRepository(session)

TokenRepoDep = Annotated[TokenRepository, Depends(get_token_repo)]

def get_token_service(token_repo: TokenRepoDep, settings: SettingsDep) -> TokenService:
    return TokenService(token_repo, settings)
    
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]

def get_user_repo(session: DBSessionDep) -> UserRepository:
    return UserRepository(session)

UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]

def get_auth_service(password_service: PasswordServiceDep,
                     token_service: TokenServiceDep, 
                     user_repo: UserRepoDep) -> AuthService:
    return AuthService(password_service, token_service, user_repo)
    
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

def get_conversation_repo(session: DBSessionDep) -> ConversationRepository:
    return ConversationRepository(session)

ConversationRepoDep = Annotated[ConversationRepository, Depends(get_conversation_repo)]

def get_message_repo(session: DBSessionDep) -> MessageRepository:
    return MessageRepository(session)

MessageRepoDep = Annotated[MessageRepository, Depends(get_message_repo)]

def get_message_service(message_repo: MessageRepoDep):
    return MessageService(message_repo)

MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]

def get_conversation_service(conversation_repo: ConversationRepoDep, message_repo: MessageRepoDep, model: ModelDep, settings: SettingsDep) -> ConversationService:
    return ConversationService(
        conversation_repo,
        message_repo,
        settings,
        model
    )

ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]

def get_memory_service(conversation_service: ConversationServiceDep) -> MemoryService:
    return MemoryService(conversation_service)

MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]

def get_chat_service(model: ModelDep, settings: SettingsDep, message_service: MessageServiceDep,
                     conversation_service: ConversationServiceDep,
                     memory_service: MemoryServiceDep) -> ChatService:
    return ChatService(
        model,
        settings,
        memory_service,
        message_service,
        conversation_service
    )

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]