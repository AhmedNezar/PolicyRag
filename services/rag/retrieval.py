from repositories import ChunkRepository
from providers.embedding import EmbeddingInterface
from providers.llm.LLMInterface import LLMInterface
from infrastructure.prompts import REWRITE_PROMPT
from models.chat import QueryRewrite

class RetrievalService:
    def __init__(self, chunk_repo: ChunkRepository, model: LLMInterface):
        self.chunk_repo = chunk_repo
        self.model = model
        
        
    async def retrieve(self, embeddings: list[float]) -> list[str]:
        chunks = await self.chunk_repo.search(embeddings)
        chunk_text = [c.content for c in chunks]
        return chunk_text
    
    async def rewrite(self, history: list[dict], message: str) -> str:
        recent_history = history[-10:]
        
        history_text = "\n".join(
            f"{item['role']}: {item['content']}"
            for item in recent_history
        )

        conversation = f"""
        Recent conversation history:
        {history_text}

        Latest user message:
        {message}
        """
        
        rewrite_response = await self.model.generate(REWRITE_PROMPT, [{"role": "user", "content": conversation}], QueryRewrite, "query_rewrite")
        return rewrite_response.query