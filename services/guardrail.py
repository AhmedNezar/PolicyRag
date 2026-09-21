from services.llm_calls import TrackedLLM
from models.chat import ChatIntents, ChatRouter
from infrastructure.prompts import GUARDRAIL_PROMPT, BASE_PROMPT, SMALL_TALK_PROMPT, POLICY_FOLLOWUP_PROMPT, POLICY_QUESTION_PROMPT, UNSUPPORTED_PROMPT, BLOCKED_PROMPT

class GuardrailService:
    def __init__(self, model: TrackedLLM):
        self.model = model

    async def route(self, message: str, history: list[dict] | None = None, **call_context) -> tuple[str, str, bool, bool]:
        recent_history = history[-4:] if history else []

        history_text = "\n".join(
            f"{item['role']}: {item['content']}"
            for item in recent_history
        )

        router_input = f"""
        Recent conversation history:
        {history_text or "None"}

        Latest user message:
        {message}
        """

        result, _ = await self.model.generate(
            system_message=GUARDRAIL_PROMPT,
            user_messages=[{"role": "user", "content": router_input}],
            output_schema=ChatRouter,
            schema_name="chat_router",
            **call_context
        )

        prompts_map = {
            ChatIntents.SMALL_TALK: SMALL_TALK_PROMPT,
            ChatIntents.POLICY_QUESTION: POLICY_QUESTION_PROMPT,
            ChatIntents.POLICY_FOLLOWUP: POLICY_FOLLOWUP_PROMPT,
            ChatIntents.UNSUPPORTED: UNSUPPORTED_PROMPT,
            ChatIntents.BLOCKED: BLOCKED_PROMPT
        }

        system_prompt = BASE_PROMPT + "\n\n" + prompts_map[result.route]
        user_message = message if result.allowed else "Not Allowed"

        follow_up = result.route == ChatIntents.POLICY_FOLLOWUP

        return system_prompt, user_message, result.needs_retrieval, follow_up
