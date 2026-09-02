from .LLMInterface import LLMInterface
from groq import AsyncGroq
from config import Settings
from typing import AsyncGenerator
import asyncio
from models import LLMResponse, LLMStreamResponse, LLMUsage
from .schemas.title import TitleSummarization
import json

class Groq(LLMInterface):
    
    def __init__(self, settings: Settings):
        self.model = settings.MODEL_NAME
        self.client = AsyncGroq(api_key=settings.GROQ_KEY)
        
        
    async def generate(self, messages) -> str:
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        prompt_tokens = completion.usage.prompt_tokens
        response_tokens = completion.usage.completion_tokens
        
        response = LLMResponse(
            prompt_content=messages[1]["content"],
            response_content=completion.choices[0].message.content,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                total_tokens=prompt_tokens+response_tokens
            )
        )
        
        return response
    
    async def stream(self, messages) -> AsyncGenerator[LLMStreamResponse, None]:
        chat_stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        
        async for chunk in chat_stream:    
            if chunk.choices[0].finish_reason == "stop":
                prompt_tokens = chunk.usage.prompt_tokens
                response_tokens = chunk.usage.completion_tokens
                yield LLMStreamResponse(
                    type="stop",
                    content="",
                    raw_content="",
                    usage=LLMUsage(
                        prompt_tokens=prompt_tokens,
                        response_tokens=response_tokens,
                        total_tokens=prompt_tokens+response_tokens
                    )
                )
            else:
                yield LLMStreamResponse(
                    type="data",
                    content=f"data: {chunk.choices[0].delta.content or ''}\n\n",
                    raw_content=chunk.choices[0].delta.content or ''
                )
            await asyncio.sleep(0.05)
            
        yield LLMStreamResponse(
            type="data",
            content=f"data: [DONE]\n\n",
            raw_content="",
            done=True
        )
        
    async def generate_title(self, message: str) -> str:
        system_message = {"role": "system", "content": "Generate a title of the conversation based on the user messages"}
        user_message = {"role": "user", "content": message}
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[system_message, user_message],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sql_query_generation",
                    "schema": TitleSummarization.model_json_schema()
                }
            }
        )
        
        raw_result = json.loads(response.choices[0].message.content or "{}")
        result = TitleSummarization.model_validate(raw_result)
        return result.title