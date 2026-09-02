from .EmbeddingInterface import EmbeddingInterface
from config import Settings
from google import genai
from google.genai.types import EmbedContentConfig

class Gemini(EmbeddingInterface):
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.EMBEDDING_MODEL
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def embed_index(self, title: str, content: list[str]) -> list[list[float]]:
        document_texts = [f"title: {title} | text: {c}" for c in content]
        
        result = await self.client.aio.models.embed_content(
            model=self.model,
            contents=document_texts,
            config=EmbedContentConfig(output_dimensionality=self.settings.EMBEDDING_VECTOR_SIZE)
        )
        
        return [embedding.values for embedding in result.embeddings]
    

    async def embed_retrieve(self, queries: list[str]) -> list[list[float]]:
        queries_texts = [f"task: question answering | query: {q}" for q in queries]
        
        result = await self.client.aio.models.embed_content(
            model=self.model,
            contents=queries_texts,
            config=EmbedContentConfig(output_dimensionality=self.settings.EMBEDDING_VECTOR_SIZE)
        )
    
        return [embedding.values for embedding in result.embeddings]