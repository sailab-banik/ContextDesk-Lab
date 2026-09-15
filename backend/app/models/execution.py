"""The execution record: the second output of every AI request.

One record feeds the inspector, the request history, the replay view, the
analytics aggregates, and the experiment comparison. Its shape mirrors the
Context Inspector's sections so the UI never has to reassemble it.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentStatus(StrEnum):
    """Four states, never a boolean.

    "The user turned this off" and "this failed" must never look alike in the
    UI, and a stub must never read as a success.
    """

    OK = "ok"
    STUB = "stub"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class ExclusionReason(StrEnum):
    """Why context that was available did not reach the model."""

    NO_DATA = "no_data"
    NOT_RELEVANT = "not_relevant"
    BELOW_RELEVANCE_THRESHOLD = "below_relevance_threshold"
    CONTEXT_BUDGET_EXCEEDED = "context_budget_exceeded"
    COMPONENT_DISABLED = "component_disabled"
    COMPONENT_UNAVAILABLE = "component_unavailable"


class ExecutionConfig(BaseModel):
    """Per-request component toggles. Passed explicitly on every request; there
    is no global switch that silently changes behavior."""

    memory_enabled: bool = True
    retrieval_enabled: bool = True
    cache_enabled: bool = True

    def label(self) -> str:
        enabled = [
            name
            for name, on in (
                ("memory", self.memory_enabled),
                ("retrieval", self.retrieval_enabled),
                ("cache", self.cache_enabled),
            )
            if on
        ]
        return " + ".join(["llm", *enabled]) if enabled else "llm only"


class MemoryEntry(BaseModel):
    id: str
    text: str
    created_at: datetime | None = None
    topics: list[str] = Field(default_factory=list)
    relevance: float | None = None
    origin: str = "long_term"


class RetrievedSource(BaseModel):
    """One Context Retriever tool call and what it returned.

    `tool` and `arguments` are recorded so the inspector can show which query
    produced the data — the MCP envelope itself never leaves the retrieval layer.
    """

    name: str
    tool: str
    arguments: dict[str, str | int | float] = Field(default_factory=dict)
    records: list[dict] = Field(default_factory=list)
    duration_ms: float = 0.0
    status: ComponentStatus = ComponentStatus.OK
    error: str | None = None

    @property
    def record_count(self) -> int:
        return len(self.records)


class ContextSection(BaseModel):
    """A block of context that reached the model."""

    name: str
    origin: str
    content: str
    estimated_tokens: int


class ExcludedContext(BaseModel):
    """A block that was available but left out, and why.

    This is the core of the project: the system selects context rather than
    sending everything, and the selection must be inspectable.
    """

    name: str
    origin: str
    reason: ExclusionReason
    estimated_tokens: int = 0
    detail: str | None = None


class MemoryReport(BaseModel):
    status: ComponentStatus
    duration_ms: float = 0.0
    entries: list[MemoryEntry] = Field(default_factory=list)
    used_count: int = 0
    # Why a DISABLED component did not run: switched off for this request, or
    # skipped because an earlier step made it unnecessary. The two are not the
    # same thing and the record should not blur them.
    skipped_reason: str | None = None
    error: str | None = None


class RetrievalReport(BaseModel):
    status: ComponentStatus
    duration_ms: float = 0.0
    sources: list[RetrievedSource] = Field(default_factory=list)
    skipped_reason: str | None = None
    error: str | None = None


class CacheReport(BaseModel):
    status: ComponentStatus
    duration_ms: float = 0.0
    hit: bool = False
    similarity: float | None = None
    matched_prompt: str | None = None
    # Fixed when the LangCache service is created; shown so a hit or miss can be
    # read against the bar it was judged on.
    threshold: float | None = None
    stored: bool = False
    skipped_reason: str | None = None
    error: str | None = None


class LLMReport(BaseModel):
    status: ComponentStatus
    called: bool = False
    duration_ms: float = 0.0
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    # Derived from token counts and configured rates. An estimate, and labeled
    # as one everywhere it is displayed.
    estimated_cost_usd: float = 0.0
    skipped_reason: str | None = None
    error: str | None = None


class ContextSummary(BaseModel):
    sources: list[str] = Field(default_factory=list)
    size_chars: int = 0
    estimated_tokens: int = 0
    budget_tokens: int = 0
    included: list[ContextSection] = Field(default_factory=list)
    excluded: list[ExcludedContext] = Field(default_factory=list)


class ExecutionStep(BaseModel):
    """One ordered step of the run, for replay."""

    name: str
    status: ComponentStatus
    duration_ms: float
    detail: str


class ExecutionRecord(BaseModel):
    request_id: str
    user_id: str
    session_id: str
    message: str
    response: str = ""

    started_at: datetime
    completed_at: datetime | None = None
    total_duration_ms: float = 0.0

    execution_config: ExecutionConfig
    memory: MemoryReport
    retrieval: RetrievalReport
    cache: CacheReport
    llm: LLMReport
    context: ContextSummary
    steps: list[ExecutionStep] = Field(default_factory=list)

    error: str | None = None


class ExecutionSummary(BaseModel):
    """The history-row projection of a record: enough for a list, not the whole
    payload."""

    request_id: str
    started_at: datetime
    user_id: str
    message: str
    config_label: str
    memory_status: ComponentStatus
    retrieval_status: ComponentStatus
    cache_status: ComponentStatus
    cache_hit: bool
    llm_called: bool
    total_duration_ms: float
    context_tokens: int

    @classmethod
    def from_record(cls, record: ExecutionRecord) -> "ExecutionSummary":
        return cls(
            request_id=record.request_id,
            started_at=record.started_at,
            user_id=record.user_id,
            message=record.message,
            config_label=record.execution_config.label(),
            memory_status=record.memory.status,
            retrieval_status=record.retrieval.status,
            cache_status=record.cache.status,
            cache_hit=record.cache.hit,
            llm_called=record.llm.called,
            total_duration_ms=record.total_duration_ms,
            context_tokens=record.context.estimated_tokens,
        )
