"""In-process store of recent execution records.

The lab is a single-process learning tool, so history lives in memory and is
bounded. Nothing here persists across a restart, and nothing here is on the
request path except one append.
"""

from collections import deque

from app.models.execution import ExecutionRecord


class ExecutionStore:
    def __init__(self, capacity: int) -> None:
        self._records: deque[ExecutionRecord] = deque(maxlen=capacity)

    def add(self, record: ExecutionRecord) -> None:
        self._records.append(record)

    def recent(self, limit: int) -> list[ExecutionRecord]:
        records = list(self._records)
        records.reverse()
        return records[:limit]

    def get(self, request_id: str) -> ExecutionRecord | None:
        return next((r for r in self._records if r.request_id == request_id), None)

    def all(self) -> list[ExecutionRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)
