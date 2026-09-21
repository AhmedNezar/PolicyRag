from .LLMInterface import LLMInterface
from .exceptions import GenerationError
from groq import AsyncGroq
from config import Settings
from typing import AsyncGenerator
from models import LLMStreamResponse, LLMUsage, TokenPricing
from pydantic import BaseModel
import asyncio


class Groq(LLMInterface):
    provider = "groq"

    def __init__(self, settings: Settings, *, pricing: TokenPricing):
        super().__init__(pricing=pricing)
        self.model = settings.MODEL_NAME
        self.client = AsyncGroq(api_key=settings.GROQ_KEY)

    def _usage(self, raw) -> LLMUsage:
        if raw is None:
            return LLMUsage()
        prompt, completion = raw.prompt_tokens, raw.completion_tokens
        usage = LLMUsage(prompt_tokens=prompt, response_tokens=completion, total_tokens=raw.total_tokens)
        if prompt is not None and completion is not None:
            usage.input_cost, usage.output_cost, usage.total_cost = self.pricing.estimate(prompt, completion)
            if usage.total_tokens is None:
                usage.total_tokens = prompt + completion
        return usage

    async def generate(self, system_message: str, user_messages: list[dict],
                       output_schema: type[BaseModel] | None = None,
                       schema_name: str | None = None) -> tuple[str | BaseModel, LLMUsage]:
        options = {}
        if output_schema:
            options["response_format"] = {"type": "json_schema", "json_schema": {
                "name": schema_name or output_schema.__name__,
                "schema": output_schema.model_json_schema(),
            }}
            
        response = await self.client.chat.completions.create(
            model=self.model, 
            messages=[{"role": "system", "content": system_message}] + user_messages,
            **options
        )
        usage = self._usage(response.usage)
        try:
            content = response.choices[0].message.content or ""
            output = output_schema.model_validate_json(content) if output_schema else content
        except Exception as error:
            raise GenerationError("Invalid structured model response", usage) from error
        return output, usage

    async def stream(self, messages: list[dict]) -> AsyncGenerator[LLMStreamResponse, None]:
        chat_stream = await self.client.chat.completions.create(model=self.model, messages=messages, stream=True)
        usage = LLMUsage()
        finish_reason = None
        try:
            async for chunk in chat_stream:
                if chunk.usage is not None:
                    usage = self._usage(chunk.usage)
                for choice in chunk.choices:
                    if choice.finish_reason is not None:
                        finish_reason = choice.finish_reason
                    content = choice.delta.content or ""
                    if content:
                        yield LLMStreamResponse(type="data", content=content, raw_content=content, usage=usage)
                        
                    await asyncio.sleep(0.05)
                    
            if finish_reason != "stop":
                raise GenerationError("Generation did not finish normally", usage)
            yield LLMStreamResponse(type="stop", content="", raw_content="", usage=usage)
        finally:
            await chat_stream.close()
