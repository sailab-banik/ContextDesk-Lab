"""In-process memory fake."""

from datetime import UTC, datetime

from app.config import Settings
from app.data.sample_data import SEED_MEMORIES
from app.models.execution import ComponentStatus, MemoryEntry, MemoryReport
from app.telemetry.text import overlap_score
from app.telemetry.timing import Stopwatch


class StubMemoryService:
    """Serves the seeded long-term memories from process memory.

    Ranking is word overlap rather than embedding similarity, so the score it
    reports is a local approximation and the component reports STUB. Session
    events are kept in a list and, unlike Agent Memory, are never promoted to
    long-term memory — the stub does not pretend to do what it cannot.
    """

    def __init__(self, settings: Settings) -> None:
        self.status = ComponentStatus.STUB
        self._limit = settings.memory_result_limit
        self._long_term = [
            MemoryEntry(
                id=str(record["id"]),
                text=str(record["text"]),
                topics=list(record["topics"]),  # type: ignore[arg-type]
                origin="long_term",
            )
            for record in SEED_MEMORIES
        ]
        self._owners = {str(record["id"]): str(record["owner_id"]) for record in SEED_MEMORIES}
        self.session_events: list[tuple[str, str, str, str]] = []

    async def get_relevant_memory(self, user_id: str, message: str) -> MemoryReport:
        with Stopwatch() as timer:
            scored = [
                entry.model_copy(update={"relevance": round(overlap_score(message, entry.text), 4)})
                for entry in self._long_term
                if self._owners[entry.id] == user_id
            ]
            scored.sort(key=lambda entry: entry.relevance or 0.0, reverse=True)

        return MemoryReport(
            status=ComponentStatus.STUB,
            duration_ms=timer.elapsed_ms,
            entries=scored[: self._limit],
        )

    async def store_memory(self, session_id: str, user_id: str, role: str, content: str) -> bool:
        self.session_events.append(
            (session_id, user_id, role, f"{datetime.now(UTC).isoformat()} {content}")
        )
        return True
