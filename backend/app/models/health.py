"""Component health, reported the same way telemetry reports it."""

from pydantic import BaseModel

from app.models.execution import ComponentStatus


class ComponentHealth(BaseModel):
    name: str
    status: ComponentStatus
    detail: str


class HealthResponse(BaseModel):
    status: str
    components: list[ComponentHealth]
