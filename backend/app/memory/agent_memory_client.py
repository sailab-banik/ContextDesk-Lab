"""Agent Memory-backed memory service."""

from datetime import UTC, datetime

from redis_agent_memory import AgentMemory

from app.config import Settings
from app.models.execution import ComponentStatus, MemoryEntry, MemoryReport
from app.telemetry.timing import Stopwatch

_ROLES = {"user": "USER", "assistant": "ASSISTANT", "system": "SYSTEM"}


class AgentMemoryService:
    """Long-term memory over Redis Iris Agent Memory.

    Session events are written as the conversation happens, but Agent Memory
    promotes them to long-term memory asynchronously — minutes later. Nothing
    here waits for that: the memories a demo depends on are seeded directly
    (see `app/data/seed_memories.py`).
    """

    def __init__(self, settings: Settings) -> None:
        self._memory = AgentMemory(
            settings.agent_memory_endpoint,
            store_id=settings.agent_memory_store_id,
            api_key=settings.agent_memory_key,
        )
        self._limit = settings.memory_result_limit
        self._threshold = settings.memory_relevance_threshold
        self.status = ComponentStatus.OK

    async def get_relevant_memory(self, user_id: str, message: str) -> MemoryReport:
        with Stopwatch() as timer:
            try:
                result = await self._memory.search_long_term_memory_async(
                    request={
                        "text": message,
                        "filter": {"owner_id": {"eq": user_id}},
                        "limit": self._limit,
                    }
                )
            except Exception as exc:
                return MemoryReport(
                    status=ComponentStatus.UNAVAILABLE,
                    duration_ms=timer.elapsed_ms,
                    error=str(exc),
                )

        entries = [
            MemoryEntry(
                id=item.id,
                text=item.text,
                created_at=item.created_at,
                topics=item.topics or [],
                # Agent Memory ranks results semantically but does not return a
                # score, so relevance is left unset rather than invented. The
                # builder keeps the service's ordering when no score exists.
                relevance=None,
            )
            for item in (result.items or [])
        ]
        return MemoryReport(
            status=ComponentStatus.OK,
            duration_ms=timer.elapsed_ms,
            entries=entries,
        )

    async def store_memory(self, session_id: str, user_id: str, role: str, content: str) -> bool:
        try:
            await self._memory.add_session_event_async(
                session_id=session_id,
                actor_id=user_id,
                role=_ROLES.get(role, "USER"),
                content=[{"text": content}],
                created_at=datetime.now(UTC),
            )
        except Exception:
            return False
        return True
