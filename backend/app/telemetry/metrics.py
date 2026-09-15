"""Aggregate metrics over execution records.

Every figure here is derived from records after the fact. Nothing in this
module runs on the request path or changes what a request does.
"""

import math

from app.config import Settings
from app.models.analytics import (
    AnalyticsSummary,
    CacheMetrics,
    ContextMetrics,
    LatencyMetrics,
    LLMMetrics,
)
from app.models.execution import ComponentStatus, ExecutionRecord

_TOKENS_PER_MILLION = 1_000_000


def estimate_cost_usd(input_tokens: int, output_tokens: int, settings: Settings) -> float:
    """Token counts times configured rates. An estimate, labeled as one wherever
    it is displayed — real billing depends on the provider's own accounting."""
    cost = (
        input_tokens * settings.llm_input_cost_per_1m
        + output_tokens * settings.llm_output_cost_per_1m
    ) / _TOKENS_PER_MILLION
    return round(cost, 6)


def summarize(records: list[ExecutionRecord], settings: Settings) -> AnalyticsSummary:
    return AnalyticsSummary(
        latency=_latency(records),
        cache=_cache(records),
        llm=_llm(records, settings),
        context=_context(records),
    )


def _latency(records: list[ExecutionRecord]) -> LatencyMetrics:
    totals = [r.total_duration_ms for r in records]
    llm_durations = [r.llm.duration_ms for r in records if r.llm.called]
    cache_hit_durations = [r.total_duration_ms for r in records if r.cache.hit]
    return LatencyMetrics(
        average_ms=_mean(totals),
        p50_ms=_percentile(totals, 50),
        p95_ms=_percentile(totals, 95),
        average_llm_ms=_mean(llm_durations),
        average_cache_hit_ms=_mean(cache_hit_durations),
    )


def _cache(records: list[ExecutionRecord]) -> CacheMetrics:
    # Only requests that actually consulted the cache can count toward its hit
    # rate; requests that ran with the cache switched off are not misses.
    consulted = [
        r for r in records if r.cache.status in (ComponentStatus.OK, ComponentStatus.STUB)
    ]
    hits = [r for r in consulted if r.cache.hit]
    return CacheMetrics(
        hit_rate=round(len(hits) / len(consulted), 4) if consulted else 0.0,
        hits=len(hits),
        misses=len(consulted) - len(hits),
        average_lookup_ms=_mean([r.cache.duration_ms for r in consulted]),
        llm_calls_avoided=len([r for r in hits if not r.llm.called]),
    )


def _llm(records: list[ExecutionRecord], settings: Settings) -> LLMMetrics:
    called = [r for r in records if r.llm.called]
    input_tokens = sum(r.llm.input_tokens for r in called)
    output_tokens = sum(r.llm.output_tokens for r in called)

    # What a cache hit saved cannot be measured, only estimated: price the
    # skipped call at the average cost of the calls that did happen.
    avoided = len([r for r in records if r.cache.hit and not r.llm.called])
    average_input = input_tokens / len(called) if called else 0
    average_output = output_tokens / len(called) if called else 0

    return LLMMetrics(
        total_requests=len(records),
        total_llm_calls=len(called),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimate_cost_usd(input_tokens, output_tokens, settings),
        estimated_saved_usd=estimate_cost_usd(
            int(average_input * avoided), int(average_output * avoided), settings
        ),
    )


def _context(records: list[ExecutionRecord]) -> ContextMetrics:
    live = (ComponentStatus.OK, ComponentStatus.STUB)
    sources_used: dict[str, int] = {}
    for record in records:
        for name in record.context.sources:
            sources_used[name] = sources_used.get(name, 0) + 1

    return ContextMetrics(
        memory_used=len([r for r in records if r.memory.status in live and r.memory.entries]),
        retrieval_used=len([r for r in records if r.retrieval.status in live]),
        cache_used=len([r for r in records if r.cache.status in live]),
        average_context_tokens=_mean([float(r.context.estimated_tokens) for r in records]),
        sources_used=dict(sorted(sources_used.items(), key=lambda kv: kv[1], reverse=True)),
    )


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _percentile(values: list[float], percentile: int) -> float:
    """Nearest-rank percentile: with the handful of requests a demo produces,
    interpolating between samples would invent precision that is not there."""
    if not values:
        return 0.0
    ordered = sorted(values)
    # Nearest rank is the ceiling of P/100 * N. `round` would be wrong here:
    # it breaks ties to even, so p50 of five samples would pick the second.
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return round(ordered[rank - 1], 2)
