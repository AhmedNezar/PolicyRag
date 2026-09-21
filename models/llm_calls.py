from enum import Enum


class LLMCallType(str, Enum):
    GENERATION = "generation"
    EMBEDDING = "embedding"
