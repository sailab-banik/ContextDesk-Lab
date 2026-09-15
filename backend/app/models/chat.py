"""Request and response models for the chat API."""

from pydantic import BaseModel, Field

from app.models.execution import ExecutionConfig, ExecutionRecord


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    # The demo is single-tenant and unauthenticated by design: the caller says
    # who it is. Scope stops at making retrieval demonstrable.
    user_id: str = "CUST-1001"
    session_id: str = "session-default"
    config: ExecutionConfig = Field(default_factory=ExecutionConfig)


class ChatResponse(BaseModel):
    """The invariant of the project: a response is never returned alone."""

    response: str
    execution: ExecutionRecord


class ComparisonRequest(BaseModel):
    """Experiment mode: run one message across several component configurations."""

    message: str = Field(min_length=1)
    user_id: str = "CUST-1001"
    session_id: str = "session-compare"
    configs: list[ExecutionConfig] | None = None


class ComparisonRun(BaseModel):
    label: str
    config: ExecutionConfig
    response: str
    execution: ExecutionRecord


class ComparisonResponse(BaseModel):
    message: str
    runs: list[ComparisonRun]
