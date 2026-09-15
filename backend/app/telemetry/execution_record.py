"""Builds the execution record as the request runs.

The chat service reads as a sequence of named steps because the bookkeeping
lives here rather than inline in the orchestration path.
"""

import uuid
from datetime import UTC, datetime

from app.models.execution import (
    CacheReport,
    ComponentStatus,
    ContextSummary,
    ExecutionConfig,
    ExecutionRecord,
    ExecutionStep,
    LLMReport,
    MemoryReport,
    RetrievalReport,
)


class ExecutionRecordBuilder:
    """Accumulates one request's telemetry.

    Reports default to DISABLED: a component that never ran because the user
    switched it off is a different outcome from one that failed, and the record
    says so without the caller having to remember to set it.
    """

    def __init__(
        self, user_id: str, session_id: str, message: str, config: ExecutionConfig
    ) -> None:
        self.request_id = uuid.uuid4().hex[:12]
        self._user_id = user_id
        self._session_id = session_id
        self._message = message
        self._config = config
        self._started_at = datetime.now(UTC)

        self.memory = MemoryReport(status=ComponentStatus.DISABLED)
        self.retrieval = RetrievalReport(status=ComponentStatus.DISABLED)
        self.cache = CacheReport(status=ComponentStatus.DISABLED)
        self.llm = LLMReport(status=ComponentStatus.DISABLED)
        self.context = ContextSummary()
        self._steps: list[ExecutionStep] = []

    def add_step(
        self, name: str, status: ComponentStatus, duration_ms: float, detail: str
    ) -> None:
        self._steps.append(
            ExecutionStep(name=name, status=status, duration_ms=duration_ms, detail=detail)
        )

    def finish(self, response: str, error: str | None = None) -> ExecutionRecord:
        completed_at = datetime.now(UTC)
        return ExecutionRecord(
            request_id=self.request_id,
            user_id=self._user_id,
            session_id=self._session_id,
            message=self._message,
            response=response,
            started_at=self._started_at,
            completed_at=completed_at,
            total_duration_ms=round(
                (completed_at - self._started_at).total_seconds() * 1000, 2
            ),
            execution_config=self._config,
            memory=self.memory,
            retrieval=self.retrieval,
            cache=self.cache,
            llm=self.llm,
            context=self.context,
            steps=self._steps,
            error=error,
        )
