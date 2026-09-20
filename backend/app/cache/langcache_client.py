"""LangCache-backed semantic cache."""

from langcache import LangCache

from app.config import Settings
from app.models.execution import CacheReport, ComponentStatus
from app.models.results import CacheLookup
from app.telemetry.timing import Stopwatch


class LangCacheService:
    """Semantic cache over Redis Iris LangCache.

    Lookup searches at a deliberately low floor and applies the real threshold
    here rather than letting the service decide. The service only returns
    entries that clear the threshold it was searched with, so searching at the
    decision threshold makes every miss indistinguishable from an empty cache —
    the score that produced the miss is exactly what this project exists to
    show. Searching low and judging locally keeps that number visible.

    The floor is still a lower bound the service may refuse to go under: the
    threshold set when the service was created in the Redis Cloud console may
    clamp it. If misses keep arriving with no similarity at all, that clamp is
    the reason, and the service has to be recreated to search any wider.
    """

    def __init__(self, settings: Settings) -> None:
        self._cache = LangCache(
            server_url=settings.langcache_endpoint,
            cache_id=settings.langcache_id,
            api_key=settings.langcache_key,
        )
        self.status = ComponentStatus.OK
        self.threshold = settings.langcache_similarity_threshold
        self._search_floor = settings.langcache_search_floor

    async def lookup(self, prompt: str) -> CacheLookup:
        with Stopwatch() as timer:
            try:
                result = await self._cache.search_async(
                    prompt=prompt, similarity_threshold=self._search_floor, max_results=1
                )
            except Exception as exc:  # noqa: BLE001
                return CacheLookup(
                    report=CacheReport(
                        status=ComponentStatus.UNAVAILABLE,
                        duration_ms=timer.elapsed_ms,
                        threshold=self.threshold,
                        error=str(exc),
                    )
                )

        # Nothing cleared even the floor, so there is no score to report: the
        # nearest cached prompt is further away than the search was willing to
        # look.
        entries = getattr(result, "data", None) or []
        if not entries:
            return CacheLookup(
                report=CacheReport(
                    status=ComponentStatus.OK,
                    duration_ms=timer.elapsed_ms,
                    hit=False,
                    threshold=self.threshold,
                )
            )

        best = entries[0]
        similarity = round(float(best.similarity), 4)
        if similarity < self.threshold:
            return CacheLookup(
                report=CacheReport(
                    status=ComponentStatus.OK,
                    duration_ms=timer.elapsed_ms,
                    hit=False,
                    similarity=similarity,
                    matched_prompt=best.prompt,
                    threshold=self.threshold,
                )
            )

        return CacheLookup(
            report=CacheReport(
                status=ComponentStatus.OK,
                duration_ms=timer.elapsed_ms,
                hit=True,
                similarity=similarity,
                matched_prompt=best.prompt,
                threshold=self.threshold,
            ),
            response=best.response,
        )

    async def store(self, prompt: str, response: str) -> bool:
        try:
            await self._cache.set_async(prompt=prompt, response=response)
        except Exception:  # noqa: BLE001
            return False
        return True
