"""Structured retrieval component: real client, stub, and the choice between them."""

from app.config import Settings
from app.retrieval.context_retriever_client import ContextRetrieverService
from app.retrieval.service import ContextRetrievalService
from app.retrieval.stub import StubContextRetrieval


def build_retrieval_service(settings: Settings) -> ContextRetrievalService:
    if settings.contextdesk_stub_mode or not settings.retrieval_configured:
        return StubContextRetrieval(settings)
    return ContextRetrieverService(settings)


__all__ = [
    "ContextRetrievalService",
    "ContextRetrieverService",
    "StubContextRetrieval",
    "build_retrieval_service",
]
