from .database import Database
from config import get_settings, load_pricing
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from providers.llm.LLMFactory import LLMFactory
from providers.llm.LLMInterface import LLMInterface
from providers.embedding import EmbeddingInterface, EmbeddingFactory
from providers.cache import RedisCache
from providers.router import RouterFactory, RouterInterface
from config import get_settings, Settings
from services import ChatService, PasswordService, TokenService, AuthService, ConversationService, MemoryService, MessageService, GuardrailService, RouterService
from services.rag import IngestionService, ChunkingService, RetrievalService
from services.llm_calls import LLMCallService, TrackedLLM, TrackedEmbedding
from repositories import ConversationRepository, TokenRepository, UserRepository, MessageRepository, DocumentRepository, ChunkRepository
from repositories.llm_calls import LLMCallRepository

_model: LLMInterface | None = None
_small_model: LLMInterface | None = None
_embedding_model: EmbeddingInterface | None = None
_guard_model: LLMInterface | None = None

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

def get_raw_model():
    global _model
    if not _model:
        settings = get_settings()
        _model = LLMFactory(model_name=settings.MODEL_NAME, settings=settings, pricing_catalog=load_pricing()).create()
    return _model

def get_raw_small_model():
    global _small_model
    if not _small_model:
        settings = get_settings()
        _small_model = LLMFactory(model_name=settings.SMALL_MODEL_NAME, settings=settings, pricing_catalog=load_pricing()).create()
    return _small_model

def get_raw_guard_model():
    global _guard_model
    if not _guard_model:
        settings = get_settings()
        _guard_model = LLMFactory(model_name=settings.GUARD_MODEL_NAME, settings=settings, pricing_catalog=load_pricing()).create()
    return _guard_model



def get_call_service(session: DBSessionDep):
    return LLMCallService(LLMCallRepository(session))

CallServiceDep = Annotated[LLMCallService, Depends(get_call_service)]


def get_model(calls: CallServiceDep):
    return TrackedLLM(get_raw_model(), calls)

ModelDep = Annotated[TrackedLLM, Depends(get_model)]

def get_small_model(calls: CallServiceDep):
    return TrackedLLM(get_raw_small_model(), calls)

SmallModelDep = Annotated[TrackedLLM, Depends(get_small_model)]

def get_guard_model(calls: CallServiceDep):
    return TrackedLLM(get_raw_guard_model(), calls)

GuardModelDep = Annotated[TrackedLLM, Depends(get_guard_model)]

def get_embedding_model(settings: SettingsDep, calls: CallServiceDep):
    global _embedding_model
    if not _embedding_model:
        _embedding_model = EmbeddingFactory(settings).create()
    return TrackedEmbedding(_embedding_model, calls)

EmbeddingModelDep = Annotated[TrackedEmbedding, Depends(get_embedding_model)]

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

def get_doc_repo(session: DBSessionDep) -> DocumentRepository:
    return DocumentRepository(session)

DocRepoDep = Annotated[DocumentRepository, Depends(get_doc_repo)]

def get_chunk_repo(session: DBSessionDep) -> ChunkRepository:
    return ChunkRepository(session)

ChunkRepoDep = Annotated[ChunkRepository, Depends(get_chunk_repo)]

def get_chunk_service(settings: SettingsDep) -> ChunkingService:
    return ChunkingService(settings)

ChunkServiceDep = Annotated[ChunkingService, Depends(get_chunk_service)]

def get_ingestion_service(settings: SettingsDep, embedding_model: EmbeddingModelDep,
                          doc_repo: DocRepoDep, chunk_repo: ChunkRepoDep, chunk_service: ChunkServiceDep) -> IngestionService:
    return IngestionService(settings, embedding_model, doc_repo, chunk_repo, chunk_service)

IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]

def get_retrieval_service(chunk_repo: ChunkRepoDep, model: ModelDep) -> RetrievalService:
    return RetrievalService(chunk_repo, model)

RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]

def get_guardrail_service(model: GuardModelDep, settings: SettingsDep) -> GuardrailService:
    return GuardrailService(model, settings)

GuardrailServiceDep = Annotated[GuardrailService, Depends(get_guardrail_service)]

def get_redis_cache(settings: SettingsDep) -> RedisCache:
    return RedisCache(settings)

RedisCacheDep = Annotated[RedisCache, Depends(get_redis_cache)]

def get_router(settings: SettingsDep, calls: CallServiceDep) -> RouterInterface:
    return RouterFactory(settings, calls).create(provider=settings.ROUTER_PROVIDER)

RouterDep = Annotated[RouterInterface, Depends(get_router)]

def get_fallback_router(settings: SettingsDep, model: SmallModelDep, calls: CallServiceDep) -> RouterInterface:
    return RouterFactory(settings, calls).create(provider=settings.ROUTER_PROVIDER_FALLBACK, model=model)

FallbackRouterDep = Annotated[RouterInterface, Depends(get_fallback_router)]

def get_router_service(main_router: RouterDep, fallback_router: FallbackRouterDep) -> RouterService:
    return RouterService(main_router, fallback_router)

RouterServiceDep = Annotated[RouterService, Depends(get_router_service)]

def get_chat_service(model: ModelDep, settings: SettingsDep, message_service: MessageServiceDep,
                     conversation_service: ConversationServiceDep,
                     memory_service: MemoryServiceDep, guardrail: GuardrailServiceDep,
                     retrieval_service: RetrievalServiceDep, embedding_model: EmbeddingModelDep, redis_cache: RedisCacheDep, router: RouterServiceDep) -> ChatService:
    return ChatService(
        model,
        settings,
        memory_service,
        message_service,
        conversation_service,
        guardrail,
        retrieval_service,
        embedding_model,
        redis_cache,
        router
    )

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
