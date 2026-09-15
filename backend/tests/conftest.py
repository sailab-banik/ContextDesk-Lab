"""Shared fixtures.

Tests run entirely against the stubs: no Redis Cloud account, no API key, and
no network. That is the point of the stubs existing.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.context_builder import ContextBuilder
from app.services.telemetry_service import TelemetryService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        contextdesk_stub_mode=True,
        openai_api_key="",
        llm_model="test-model",
    )


@pytest.fixture
def builder(settings: Settings) -> ContextBuilder:
    return ContextBuilder(settings)


@pytest.fixture
def telemetry(settings: Settings) -> TelemetryService:
    return TelemetryService(settings)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONTEXTDESK_STUB_MODE", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
