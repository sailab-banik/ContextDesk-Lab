"""Wall-clock measurement for individual execution steps."""

import time
from types import TracebackType


class Stopwatch:
    """Measures one step.

    Every component reports its own duration, so timing is taken at the call
    site rather than inferred later:

        with Stopwatch() as timer:
            ...
        timer.elapsed_ms

    The elapsed time is readable from inside the block as well, because error
    paths return from there — a component that failed after 300ms still cost
    300ms and the record must say so.
    """

    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._stopped_at: float | None = None

    def __enter__(self) -> "Stopwatch":
        self._start = time.perf_counter()
        self._stopped_at = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stopped_at = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        end = self._stopped_at if self._stopped_at is not None else time.perf_counter()
        return round((end - self._start) * 1000, 2)
