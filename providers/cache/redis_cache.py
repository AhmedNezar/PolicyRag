from config.base import Settings
from redisvl.extensions.cache.llm import SemanticCache
from providers.embedding import EmbeddingInterface
from redisvl.utils.vectorize import CustomVectorizer

class RedisCache:
    def __init__(self, settings: Settings, embedding_model: EmbeddingInterface):
        vectorizer = CustomVectorizer(
            embed=embedding_model.embed_sync,
            aembed=embedding_model.embed_retrieve
        )
        
        self.llmcache = SemanticCache(
            name="policy_cache",
            redis_url=f"redis://:{settings.REDIS_PASSWORD}@localhost:6379/0",
            distance_threshold=0.1,
            vectorizer=vectorizer
        )
        
    async def retrieve(self, vector: list[float]) -> str | None:
        if response := await self.llmcache.acheck(vector=vector):
            return response[0]["response"]
        else:
            return None
            
    async def add(self, query: str, response: str, vector: list[float]):
        await self.llmcache.astore(
            prompt=query,
            response=response,
            vector=vector
        )