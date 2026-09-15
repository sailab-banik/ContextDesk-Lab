"""Context selection: what reaches the model, and the reason for every omission."""

from app.config import Settings
from app.models.execution import (
    ComponentStatus,
    ExclusionReason,
    MemoryEntry,
    MemoryReport,
    RetrievalReport,
    RetrievedSource,
)
from app.services.context_builder import ContextBuilder


def memory_report(*entries: MemoryEntry) -> MemoryReport:
    return MemoryReport(status=ComponentStatus.STUB, entries=list(entries))


def retrieval_report(*sources: RetrievedSource) -> RetrievalReport:
    return RetrievalReport(status=ComponentStatus.STUB, sources=list(sources))


def source(name: str, records: list[dict]) -> RetrievedSource:
    return RetrievedSource(
        name=name, tool=f"filter_{name}", records=records, status=ComponentStatus.STUB
    )


def test_empty_source_is_excluded_as_no_data(builder: ContextBuilder):
    built = builder.build(memory_report(), retrieval_report(source("subscription", [])))

    assert built.summary.sources == []
    excluded = built.summary.excluded[0]
    assert excluded.reason is ExclusionReason.NO_DATA
    assert "filter_subscription" in (excluded.detail or "")


def test_resolved_tickets_are_dropped_with_their_status_recorded(builder: ContextBuilder):
    built = builder.build(
        memory_report(),
        retrieval_report(
            source(
                "support_tickets",
                [
                    {"id": "TICK-1", "status": "open"},
                    {"id": "TICK-2", "status": "resolved"},
                ],
            )
        ),
    )

    assert "TICK-1" in built.prompt
    assert "TICK-2" not in built.prompt
    dropped = built.summary.excluded[0]
    assert dropped.name == "support_tickets: TICK-2"
    assert dropped.reason is ExclusionReason.NOT_RELEVANT
    assert dropped.detail == "status=resolved"


def test_resolved_incidents_are_dropped_but_monitoring_ones_are_kept(builder: ContextBuilder):
    built = builder.build(
        memory_report(),
        retrieval_report(
            source(
                "regional_incidents",
                [
                    {"id": "INC-1", "status": "active"},
                    {"id": "INC-2", "status": "monitoring"},
                    {"id": "INC-3", "status": "resolved"},
                ],
            )
        ),
    )

    assert "INC-1" in built.prompt and "INC-2" in built.prompt
    assert "INC-3" not in built.prompt


def test_memory_below_the_relevance_threshold_is_excluded(builder: ContextBuilder):
    built = builder.build(
        memory_report(
            MemoryEntry(id="MEM-1", text="relevant memory", relevance=0.9),
            MemoryEntry(id="MEM-2", text="stale memory", relevance=0.1),
        ),
        retrieval_report(),
    )

    assert built.summary.sources == ["memory: MEM-1"]
    excluded = built.summary.excluded[0]
    assert excluded.name == "memory: MEM-2"
    assert excluded.reason is ExclusionReason.BELOW_RELEVANCE_THRESHOLD
    assert "0.1" in (excluded.detail or "")


def test_unscored_memory_is_trusted_to_the_service_that_ranked_it(builder: ContextBuilder):
    """Agent Memory ranks semantically without returning a score; an unscored
    entry is kept rather than dropped by a threshold it cannot be measured on."""
    built = builder.build(
        memory_report(MemoryEntry(id="MEM-1", text="ranked by the service", relevance=None)),
        retrieval_report(),
    )

    assert built.summary.sources == ["memory: MEM-1"]


def test_context_past_the_budget_is_excluded_in_priority_order(settings: Settings):
    tight = ContextBuilder(settings.model_copy(update={"context_budget_tokens": 30}))

    built = tight.build(
        memory_report(MemoryEntry(id="MEM-1", text="x" * 400, relevance=1.0)),
        retrieval_report(
            source("customer", [{"id": "CUST-1", "name": "Aurora"}]),
            source("api_usage", [{"id": "USAGE-1", "detail": "y" * 400}]),
        ),
    )

    assert built.summary.sources == ["customer"]
    over_budget = {e.name: e for e in built.summary.excluded}
    assert over_budget["api_usage"].reason is ExclusionReason.CONTEXT_BUDGET_EXCEEDED
    assert over_budget["memory: MEM-1"].reason is ExclusionReason.CONTEXT_BUDGET_EXCEEDED
    assert built.summary.estimated_tokens <= 30


def test_failed_source_is_excluded_as_unavailable_not_as_empty(builder: ContextBuilder):
    built = builder.build(
        memory_report(),
        RetrievalReport(
            status=ComponentStatus.UNAVAILABLE,
            sources=[
                RetrievedSource(
                    name="subscription",
                    tool="filter_subscription_by_customer_id",
                    status=ComponentStatus.UNAVAILABLE,
                    error="connection refused",
                )
            ],
        ),
    )

    excluded = built.summary.excluded[0]
    assert excluded.reason is ExclusionReason.COMPONENT_UNAVAILABLE
    assert excluded.detail == "connection refused"


def test_sources_are_assembled_in_priority_order(builder: ContextBuilder):
    built = builder.build(
        memory_report(MemoryEntry(id="MEM-1", text="a memory", relevance=1.0)),
        retrieval_report(
            source("regional_incidents", [{"id": "INC-1", "status": "active"}]),
            source("customer", [{"id": "CUST-1"}]),
            source("subscription", [{"id": "SUB-1"}]),
        ),
    )

    assert built.summary.sources == [
        "customer",
        "subscription",
        "regional_incidents",
        "memory: MEM-1",
    ]
