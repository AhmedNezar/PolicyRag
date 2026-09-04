from repositories import ChunkRepository
from providers.embedding import EmbeddingInterface

class RetrievalService:
    def __init__(self, chunk_repo: ChunkRepository, embedding_model: EmbeddingInterface):
        self.chunk_repo = chunk_repo
        self.embedding_model = embedding_model
        
        
    async def retrieve(self, query: str) -> list[str]:
        embeddings = await self.embedding_model.embed_retrieve(query)
        chunks = await self.chunk_repo.search(embeddings)
        chunk_text = [c.content for c in chunks]
        return chunk_text