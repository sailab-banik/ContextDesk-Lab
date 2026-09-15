"""Aggregates: what the analytics numbers are allowed to claim."""

from datetime import UTC, datetime

from app.config import Settings
from app.models.execution import (
    CacheReport,
    ComponentStatus,
    ContextSummary,
    ExecutionConfig,
    ExecutionRecord,
    LLMReport,
    MemoryReport,
    RetrievalReport,
)
from app.telemetry.metrics import estimate_cost_usd, summarize


def record(
    *,
    total_ms: float = 100.0,
    cache_status: ComponentStatus = ComponentStatus.STUB,
    cache_hit: bool = False,
    llm_called: bool = True,
    llm_ms: float = 80.0,
    input_tokens: int = 100,
    output_tokens: int = 50,
    context_tokens: int = 200,
    sources: list[str] | None = None,
) -> ExecutionRecord:
    return ExecutionRecord(
        request_id=f"req-{total_ms}-{cache_hit}",
        user_id="CUST-1001",
        session_id="s",
        message="m",
        started_at=datetime.now(UTC),
        execution_config=ExecutionConfig(),
        total_duration_ms=total_ms,
        memory=MemoryReport(status=ComponentStatus.STUB),
        retrieval=RetrievalReport(status=ComponentStatus.STUB),
        cache=CacheReport(status=cache_status, hit=cache_hit, duration_ms=5.0),
        llm=LLMReport(
            status=ComponentStatus.STUB,
            called=llm_called,
            duration_ms=llm_ms,
            input_tokens=input_tokens if llm_called else 0,
            output_tokens=output_tokens if llm_called else 0,
        ),
        context=ContextSummary(estimated_tokens=context_tokens, sources=sources or ["customer"]),
    )


def test_requests_that_ran_without_the_cache_are_not_counted_as_misses(settings: Settings):
    records = [
        record(cache_status=ComponentStatus.DISABLED),
        record(cache_status=ComponentStatus.STUB, cache_hit=True, llm_called=False),
    ]

    summary = summarize(records, settings)

    assert summary.cache.hits == 1
    assert summary.cache.misses == 0
    assert summary.cache.hit_rate == 1.0
    assert summary.cache.llm_calls_avoided == 1


def test_percentiles_use_nearest_rank(settings: Settings):
    records = [record(total_ms=value) for value in (10, 20, 30, 40, 100)]

    latency = summarize(records, settings).latency

    assert latency.p50_ms == 30.0
    assert latency.p95_ms == 100.0
    assert latency.average_ms == 40.0


def test_saving_is_estimated_from_the_calls_that_did_happen(settings: Settings):
    records = [
        record(input_tokens=1000, output_tokens=500),
        record(cache_hit=True, llm_called=False),
    ]

    llm = summarize(records, settings).llm

    assert llm.total_requests == 2
    assert llm.total_llm_calls == 1
    # One avoided call, priced at the average of the calls that ran.
    assert llm.estimated_saved_usd == estimate_cost_usd(1000, 500, settings)


def test_no_requests_yields_zeroes_not_errors(settings: Settings):
    summary = summarize([], settings)

    assert summary.latency.p95_ms == 0.0
    assert summary.cache.hit_rate == 0.0
    assert summary.llm.estimated_cost_usd == 0.0
    assert summary.context.sources_used == {}


def test_cost_follows_the_configured_rates(settings: Settings):
    priced = settings.model_copy(
        update={"llm_input_cost_per_1m": 1.0, "llm_output_cost_per_1m": 2.0}
    )

    assert estimate_cost_usd(1_000_000, 1_000_000, priced) == 3.0
    assert estimate_cost_usd(0, 0, priced) == 0.0


def test_source_usage_is_counted_across_requests(settings: Settings):
    records = [
        record(sources=["customer", "subscription"]),
        record(total_ms=101.0, sources=["customer"]),
    ]

    context = summarize(records, settings).context

    assert context.sources_used == {"customer": 2, "subscription": 1}
    assert context.average_context_tokens == 200.0
