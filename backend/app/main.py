"""FastAPI entry point: configuration, component wiring, and routes."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, chat, health
from app.api.dependencies import build_chat_service
from app.config import get_settings
from app.services.telemetry_service import TelemetryService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Clients are built once, at startup, from configuration. Whether a
    # component is real or stubbed is decided here and nowhere else.
    settings = get_settings()
    app.state.settings = settings
    app.state.telemetry_service = TelemetryService(settings)
    app.state.chat_service = build_chat_service(settings, app.state.telemetry_service)
    yield


app = FastAPI(title="ContextDesk Lab", lifespan=lifespan)

# The frontend runs on a separate origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(analytics.router)
