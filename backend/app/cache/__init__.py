"""Semantic cache component: real client, stub, and the choice between them."""

from app.cache.langcache_client import LangCacheService
from app.cache.service import SemanticCacheService
from app.cache.stub import StubSemanticCache
from app.config import Settings


def build_semantic_cache(settings: Settings) -> SemanticCacheService:
    if settings.contextdesk_stub_mode or not settings.cache_configured:
        return StubSemanticCache(settings)
    return LangCacheService(settings)


__all__ = [
    "LangCacheService",
    "SemanticCacheService",
    "StubSemanticCache",
    "build_semantic_cache",
]
