"""In-process semantic cache fake."""

from app.config import Settings
from app.models.execution import CacheReport, ComponentStatus
from app.models.results import CacheLookup
from app.telemetry.text import overlap_score
from app.telemetry.timing import Stopwatch


class StubSemanticCache:
    """A cache that matches on word overlap instead of embeddings.

    It exists so the cache path is exercisable before a LangCache service is
    provisioned. Its threshold is lower than the LangCache default because
    lexical overlap scores lower than embedding cosine similarity for the same
    pair of prompts — reporting the real 0.92 here would make every lookup miss
    and misrepresent what the component does. Status is STUB, never OK.
    """

    def __init__(self, settings: Settings) -> None:
        self.status = ComponentStatus.STUB
        self.threshold = settings.stub_similarity_threshold
        self._entries: list[tuple[str, str]] = []

    async def lookup(self, prompt: str) -> CacheLookup:
        with Stopwatch() as timer:
            scored = [
                (overlap_score(prompt, cached_prompt), cached_prompt, response)
                for cached_prompt, response in self._entries
            ]
            best = max(scored, default=None, key=lambda item: item[0])

        if best is None or best[0] < self.threshold:
            return CacheLookup(
                report=CacheReport(
                    status=ComponentStatus.STUB,
                    duration_ms=timer.elapsed_ms,
                    hit=False,
                    similarity=round(best[0], 4) if best else None,
                    threshold=self.threshold,
                )
            )

        similarity, matched_prompt, response = best
        return CacheLookup(
            report=CacheReport(
                status=ComponentStatus.STUB,
                duration_ms=timer.elapsed_ms,
                hit=True,
                similarity=round(similarity, 4),
                matched_prompt=matched_prompt,
                threshold=self.threshold,
            ),
            response=response,
        )

    async def store(self, prompt: str, response: str) -> bool:
        self._entries.append((prompt, response))
        return True
