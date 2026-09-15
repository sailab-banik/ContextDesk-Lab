"""The LLM seam.

The LLM service turns a user message plus already-prepared context into a
response. It never retrieves context, touches memory, or reads the cache.
"""

from typing import Protocol

from app.models.results import LLMResult


class LLMService(Protocol):
    model: str

    async def generate(self, message: str, context: str) -> LLMResult:
        ...
