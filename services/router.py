from providers.router import RouterInterface
from models.chat import ChatIntents
from models.chat import ChatIntents
from infrastructure.prompts import BASE_PROMPT, SMALL_TALK_PROMPT, POLICY_FOLLOWUP_PROMPT, POLICY_QUESTION_PROMPT, UNSUPPORTED_PROMPT


class RouterService:
    def __init__(self, main_router: RouterInterface, fallback_router: RouterInterface):
        self.main_router = main_router
        self.fallback_router = fallback_router
        
    async def route(self, message: str, history: list[dict] | None, **call_context) -> tuple[str, bool, bool]:
        if history:
            raw_history = "\n\n".join([f"Role: {message['role']}\nContent: {message['content']}" for message in history])
            message = f"History:\n{raw_history}\n\nLast user message:\n{message}"

                    
        intent, confidence = await self.main_router.route(message, **call_context)
        
        if confidence < 0.6:
            intent, confidence = await self.fallback_router.route(message, **call_context)
            
        prompts_map = {
            ChatIntents.SMALL_TALK: SMALL_TALK_PROMPT,
            ChatIntents.POLICY_QUESTION: POLICY_QUESTION_PROMPT,
            ChatIntents.POLICY_FOLLOWUP: POLICY_FOLLOWUP_PROMPT,
            ChatIntents.UNSUPPORTED: UNSUPPORTED_PROMPT,
        }
        
        print("-------------------------------------")
        print(intent)
        print("-------------------------------------")
    
        system_prompt = BASE_PROMPT + "\n\n" + prompts_map[intent]

        follow_up = intent == ChatIntents.POLICY_FOLLOWUP
        needs_retrieval = intent == ChatIntents.POLICY_QUESTION or intent == ChatIntents.POLICY_FOLLOWUP
        

        return system_prompt, follow_up, needs_retrieval
        
