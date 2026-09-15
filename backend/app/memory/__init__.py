"""Memory component: real client, stub, and the choice between them."""

from app.config import Settings
from app.memory.agent_memory_client import AgentMemoryService
from app.memory.service import MemoryService
from app.memory.stub import StubMemoryService


def build_memory_service(settings: Settings) -> MemoryService:
    if settings.contextdesk_stub_mode or not settings.memory_configured:
        return StubMemoryService(settings)
    return AgentMemoryService(settings)


__all__ = [
    "AgentMemoryService",
    "MemoryService",
    "StubMemoryService",
    "build_memory_service",
]
