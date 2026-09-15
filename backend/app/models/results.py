"""Results passed between the chat service and the components it coordinates.

These are the seams of the orchestration path — typed, not dictionaries.
"""

from pydantic import BaseModel

from app.models.execution import CacheReport, ComponentStatus, ContextSummary


class CacheLookup(BaseModel):
    """A cache decision plus the response it can serve.

    The decision is always explicit: a miss is reported as a miss, and the
    similarity score is never hidden.
    """

    report: CacheReport
    response: str | None = None


class LLMResult(BaseModel):
    text: str
    model: str
    status: ComponentStatus
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


class BuiltContext(BaseModel):
    """What the context builder produced: the text the model will see, and the
    account of how it was chosen."""

    prompt: str
    summary: ContextSummary
