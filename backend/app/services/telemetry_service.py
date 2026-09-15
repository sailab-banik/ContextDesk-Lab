"""Owns the execution history and the aggregates computed from it."""

from app.config import Settings
from app.models.analytics import AnalyticsSummary, HistoryPage
from app.models.execution import ExecutionRecord, ExecutionSummary
from app.telemetry.metrics import summarize
from app.telemetry.store import ExecutionStore


class TelemetryService:
    """Records what happened; never changes what happens.

    Nothing on this class is consulted while a request is being served — the
    chat service hands it a finished record and moves on.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._store = ExecutionStore(settings.telemetry_history_limit)

    def record(self, record: ExecutionRecord) -> None:
        self._store.add(record)

    def history(self, limit: int) -> HistoryPage:
        return HistoryPage(
            items=[ExecutionSummary.from_record(r) for r in self._store.recent(limit)],
            total=len(self._store),
        )

    def get(self, request_id: str) -> ExecutionRecord | None:
        """The full record behind one history row — the replay view's source."""
        return self._store.get(request_id)

    def summary(self) -> AnalyticsSummary:
        return summarize(self._store.all(), self._settings)

    def clear(self) -> None:
        self._store.clear()
