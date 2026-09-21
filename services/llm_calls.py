from models import LLMUsage
from models.llm_calls import LLMCallType
from providers.llm.LLMInterface import LLMInterface


class LLMCallService:
    def __init__(self, repository):
        self.repository = repository

    async def record(self, provider: LLMInterface, call_type, purpose, usage=None, *,
                     message_id=None, conversation_id=None, error=None):
        
        return await self.repository.create({
            "call_type": call_type,
            "purpose": purpose,
            "provider": provider.provider,
            "model": provider.model,
            "message_id": message_id,
            "conversation_id": conversation_id,
            **(usage or LLMUsage()).model_dump(),
            "is_success": error is None,
            "error_type": type(error).__name__ if error else None,
        })


class TrackedLLM:
    def __init__(self, provider, calls: LLMCallService):
        self.provider = provider
        self.calls = calls

    async def generate(self, system_message, user_messages, output_schema=None,
                       schema_name=None, *, message_id=None, conversation_id=None):
        context = dict(message_id=message_id, conversation_id=conversation_id)
        try:
            output, usage = await self.provider.generate(system_message, user_messages, output_schema, schema_name)
        except BaseException as error:
            await self.calls.record(
                self.provider, 
                LLMCallType.GENERATION,
                schema_name or "generation",
                getattr(error, "usage", None), 
                error=error, 
                **context
            )
            raise
        await self.calls.record(self.provider, LLMCallType.GENERATION, schema_name or "generation", usage, **context)
        return output, usage

    async def stream(self, messages, *, message_id=None, conversation_id=None):
        context = dict(message_id=message_id, conversation_id=conversation_id)
        usage = None
        terminal = None
        stream = self.provider.stream(messages)
        try:
            async for chunk in stream:
                if chunk.usage is not None:
                    usage = chunk.usage
                if chunk.type == "stop":
                    terminal = chunk
                else:
                    yield chunk
            if terminal is None:
                raise RuntimeError("Provider stream ended without a terminal event")
        except BaseException as error:
            await self.calls.record(
                self.provider,
                LLMCallType.GENERATION,
                "answer",
                getattr(error, "usage", None) or usage,
                error=error,
                **context
            )
            raise
        finally:
            await stream.aclose()

        await self.calls.record(self.provider, LLMCallType.GENERATION, "answer", usage, **context)
        yield terminal


class TrackedEmbedding:
    def __init__(self, provider, calls: LLMCallService):
        self.provider = provider
        self.calls = calls

    async def _embed(self, method, purpose, *, message_id=None, conversation_id=None, **kwargs):
        context = dict(message_id=message_id, conversation_id=conversation_id)
        try:
            vectors, usage = await method(**kwargs)
        except BaseException as error:
            await self.calls.record(self.provider, LLMCallType.EMBEDDING, purpose, error=error, **context)
            raise
        await self.calls.record(self.provider, LLMCallType.EMBEDDING, purpose, usage, **context)
        return vectors

    async def embed_index(self, title, content, *, message_id=None, conversation_id=None):
        return await self._embed(
            self.provider.embed_index, 
            "document_index",
            title=title, 
            content=content,
            message_id=message_id, 
            conversation_id=conversation_id
        )

    async def embed_retrieve(self, query, *, message_id=None, conversation_id=None):
        return await self._embed(
            self.provider.embed_retrieve, 
            "query_embedding",
            query=query,
            message_id=message_id,
            conversation_id=conversation_id
        )
