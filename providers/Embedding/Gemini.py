from .EmbeddingInterface import EmbeddingInterface
from config import Settings
from google import genai
from google.genai.types import EmbedContentConfig
from models import LLMUsage
from config import load_pricing

class Gemini(EmbeddingInterface):
    provider = "gemini"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.EMBEDDING_MODEL
        self.pricing = load_pricing()[self.provider][self.model]
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def embed_index(self, title: str, content: list[str]) -> tuple[list[list[float]], LLMUsage]:
        document_texts = [f"title: {title} | text: {c}" for c in content]

        result = await self.client.aio.models.embed_content(
            model=self.model,
            contents=document_texts,
            config=EmbedContentConfig(output_dimensionality=self.settings.EMBEDDING_VECTOR_SIZE)
        )

        return [embedding.values for embedding in result.embeddings], self._usage(result)


    async def embed_retrieve(self, query: str) -> tuple[list[float], LLMUsage]:
        query_text = f"task: question answering | query: {query}"

        result = await self.client.aio.models.embed_content(
            model=self.model,
            contents=[query_text],
            config=EmbedContentConfig(output_dimensionality=self.settings.EMBEDDING_VECTOR_SIZE)
        )

        return result.embeddings[0].values, self._usage(result)

    def _usage(self, result) -> LLMUsage:
        metadata = getattr(result, "usage_metadata", None)
        tokens = getattr(metadata, "prompt_token_count", None)
        if tokens is None:
            return LLMUsage()
        input_cost, output_cost, total_cost = self.pricing.estimate(tokens, 0)
        return LLMUsage(prompt_tokens=tokens, response_tokens=0, total_tokens=tokens,
                        input_cost=input_cost, output_cost=output_cost, total_cost=total_cost)
