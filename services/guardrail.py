from services.llm_calls import TrackedLLM
from config.base import Settings

class GuardrailService:
    def __init__(self, model: TrackedLLM, settings: Settings):
        self.model = model
        self.settings = settings

    async def guard(self, message: str, **call_context) -> tuple[str, str, bool, bool]:

        result, _ = await self.model.generate(
            system_message="",
            user_messages=[{"role": "user", "content": message}],
            # output_schema=ChatRouter,
            # schema_name="chat_router",
            **call_context
        )
        
        print("---------------------------------------")
        print(f"Guardrail conf. ({result})")
        print("---------------------------------------")
        
        if float(result) > self.settings.GUARD_THRESHOLD:
            return False
        
        return True