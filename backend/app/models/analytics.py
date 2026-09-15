"""Aggregate metrics computed from execution records."""

from pydantic import BaseModel, Field

from app.models.execution import ExecutionSummary


class LatencyMetrics(BaseModel):
    average_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    average_llm_ms: float = 0.0
    average_cache_hit_ms: float = 0.0


class CacheMetrics(BaseModel):
    hit_rate: float = 0.0
    hits: int = 0
    misses: int = 0
    average_lookup_ms: float = 0.0
    llm_calls_avoided: int = 0


class LLMMetrics(BaseModel):
    total_requests: int = 0
    total_llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    # Both figures are estimates derived from token counts and configured rates.
    estimated_cost_usd: float = 0.0
    estimated_saved_usd: float = 0.0


class ContextMetrics(BaseModel):
    memory_used: int = 0
    retrieval_used: int = 0
    cache_used: int = 0
    average_context_tokens: float = 0.0
    sources_used: dict[str, int] = Field(default_factory=dict)


class AnalyticsSummary(BaseModel):
    latency: LatencyMetrics
    cache: CacheMetrics
    llm: LLMMetrics
    context: ContextMetrics
    cost_is_estimated: bool = True


class HistoryPage(BaseModel):
    items: list[ExecutionSummary]
    total: int
