"""LLM component: one provider built well, plus a stub for keyless runs."""

from app.config import Settings
from app.llm.openai_provider import OpenAIProvider
from app.llm.service import LLMService
from app.llm.stub import StubLLM


def build_llm_service(settings: Settings) -> LLMService:
    if settings.contextdesk_stub_mode or not settings.llm_configured:
        return StubLLM(settings)
    return OpenAIProvider(settings)


__all__ = ["LLMService", "OpenAIProvider", "StubLLM", "build_llm_service"]
