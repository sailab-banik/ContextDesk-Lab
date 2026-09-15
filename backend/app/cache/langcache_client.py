"""LangCache-backed semantic cache."""

from langcache import LangCache

from app.config import Settings
from app.models.execution import CacheReport, ComponentStatus
from app.models.results import CacheLookup
from app.telemetry.timing import Stopwatch


class LangCacheService:
    """Semantic cache over Redis Iris LangCache.

    The similarity threshold is fixed when the service is created in the Redis
    Cloud console and cannot be passed per request. The configured value is
    carried here only so the UI can show what a hit or miss was judged against.
    """

    def __init__(self, settings: Settings) -> None:
        self._cache = LangCache(
            server_url=settings.langcache_endpoint,
            cache_id=settings.langcache_id,
            api_key=settings.langcache_key,
        )
        self.status = ComponentStatus.OK
        self.threshold = settings.langcache_similarity_threshold

    async def lookup(self, prompt: str) -> CacheLookup:
        with Stopwatch() as timer:
            try:
                result = await self._cache.search_async(prompt=prompt)
            except Exception as exc:  # noqa: BLE001
                return CacheLookup(
                    report=CacheReport(
                        status=ComponentStatus.UNAVAILABLE,
                        duration_ms=timer.elapsed_ms,
                        threshold=self.threshold,
                        error=str(exc),
                    )
                )

        # An empty result set is a miss; the SDK returns no entries rather than
        # an error when nothing clears the threshold.
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
        return CacheLookup(
            report=CacheReport(
                status=ComponentStatus.OK,
                duration_ms=timer.elapsed_ms,
                hit=True,
                similarity=round(float(best.similarity), 4),
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
