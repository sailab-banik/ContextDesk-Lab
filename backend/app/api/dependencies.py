"""Wiring for the route handlers.

The component graph is assembled once at startup and stored on the app, so a
request never builds a client and the stub/real choice is made in exactly one
place.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.cache import build_semantic_cache
from app.config import Settings, get_settings
from app.llm import build_llm_service
from app.memory import build_memory_service
from app.retrieval import build_retrieval_service
from app.services.chat_service import ChatService
from app.services.context_builder import ContextBuilder
from app.services.telemetry_service import TelemetryService


def build_chat_service(settings: Settings, telemetry: TelemetryService) -> ChatService:
    return ChatService(
        settings=settings,
        memory=build_memory_service(settings),
        retrieval=build_retrieval_service(settings),
        cache=build_semantic_cache(settings),
        llm=build_llm_service(settings),
        context_builder=ContextBuilder(settings),
        telemetry=telemetry,
    )


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_telemetry_service(request: Request) -> TelemetryService:
    return request.app.state.telemetry_service


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
TelemetryServiceDep = Annotated[TelemetryService, Depends(get_telemetry_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
