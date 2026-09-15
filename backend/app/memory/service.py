"""The memory seam.

Memory retrieves and scores; it never decides whether it should have run. That
decision belongs to the execution config the chat service reads.
"""

from typing import Protocol

from app.models.execution import ComponentStatus, MemoryReport


class MemoryService(Protocol):
    status: ComponentStatus

    async def get_relevant_memory(self, user_id: str, message: str) -> MemoryReport:
        """Return the long-term memories worth considering for this message.

        Everything retrieved is returned, scored where a score is available.
        The context builder decides what actually reaches the model, so the
        inspector can show both what was found and what was left out.
        """
        ...

    async def store_memory(self, session_id: str, user_id: str, role: str, content: str) -> bool:
        """Record one turn of the conversation as a session event."""
        ...
