"""Health route: which components are live, stubbed, or unreachable."""

from fastapi import APIRouter

from app.api.dependencies import SettingsDep
from app.config import Settings
from app.models.execution import ComponentStatus
from app.models.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep) -> HealthResponse:
    """Reports the same four states telemetry uses.

    A stub is never reported as OK — Milestone 0 is done when all three Iris
    components read `ok` here rather than `stub`.
    """
    components = [
        _component("llm", settings.llm_configured, settings.llm_model, settings),
        _component("memory", settings.memory_configured, "Redis Iris Agent Memory", settings),
        _component(
            "retrieval", settings.retrieval_configured, "Redis Iris Context Retriever", settings
        ),
        _component("cache", settings.cache_configured, "Redis Iris LangCache", settings),
    ]
    return HealthResponse(status="ok", components=components)


def _component(name: str, configured: bool, detail: str, settings: Settings) -> ComponentHealth:
    if settings.contextdesk_stub_mode:
        return ComponentHealth(
            name=name,
            status=ComponentStatus.STUB,
            detail="CONTEXTDESK_STUB_MODE=true forces in-process fakes",
        )
    if not configured:
        return ComponentHealth(
            name=name,
            status=ComponentStatus.STUB,
            detail=f"{detail}: not configured, using the in-process stub",
        )
    return ComponentHealth(name=name, status=ComponentStatus.OK, detail=detail)
