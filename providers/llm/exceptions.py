"""Shared exceptions raised by LLM providers."""

from models import LLMUsage


class GenerationError(RuntimeError):
    def __init__(self, message: str, usage: LLMUsage | None = None):
        super().__init__(message)
        self.usage = usage
