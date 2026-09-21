from .RouterInterface import RouterInterface
from services.llm_calls import TrackedLLM
from models.chat import ChatIntents, ChatRouter
from infrastructure.prompts import ROUTER_PROMPT

class LLMRouter(RouterInterface):
    def __init__(self, model: TrackedLLM):
        self.model = model
        
    async def route(self, message: str, **call_context) -> tuple[ChatIntents, float]:
        response, _ = await self.model.generate(
            system_message=ROUTER_PROMPT,
            user_messages=[{"role": "user", "content": message}],
            output_schema=ChatRouter,
            schema_name="intent_router",
            **call_context,
        )
        
        intent = response.route
        confidence = response.confidence
        
        return ChatIntents(intent), confidence
