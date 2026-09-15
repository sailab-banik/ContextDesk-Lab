"""The semantic cache seam.

Both the LangCache client and the in-process stub implement this protocol, so
the chat service never learns which one it is talking to — only what the
component reported.
"""

from typing import Protocol

from app.models.execution import ComponentStatus
from app.models.results import CacheLookup


class SemanticCacheService(Protocol):
    status: ComponentStatus
    threshold: float

    async def lookup(self, prompt: str) -> CacheLookup:
        """Search for a semantically equivalent prompt.

        Always returns a decision — hit or miss, with the similarity score that
        produced it.
        """
        ...

    async def store(self, prompt: str, response: str) -> bool:
        """Remember a prompt/response pair for later lookups."""
        ...
