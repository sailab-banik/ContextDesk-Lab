"""Assembles the context block that reaches the model — and the account of what
did not.

This is where the project's central claim lives: the system selects context
rather than sending everything, and every omission has a stated reason.
"""

from dataclasses import dataclass

from app.config import Settings
from app.models.execution import (
    ComponentStatus,
    ContextSection,
    ContextSummary,
    ExcludedContext,
    ExclusionReason,
    MemoryReport,
    RetrievalReport,
    RetrievedSource,
)
from app.models.results import BuiltContext
from app.retrieval.service import (
    SOURCE_CUSTOMER,
    SOURCE_INCIDENTS,
    SOURCE_TICKETS,
)
from app.telemetry.text import estimate_tokens

# Identity first, then what is already known about this customer, then live data
# in descending specificity. Under a tight budget the tail is what gets dropped,
# so the order is the policy and is stated once, here.
SOURCE_PRIORITY = [
    SOURCE_CUSTOMER,
    "subscription",
    "api_usage",
    SOURCE_TICKETS,
    SOURCE_INCIDENTS,
]

MEMORY_ORIGIN = "memory"
RETRIEVAL_ORIGIN = "retrieval"

# A ticket nobody is working on, or an incident already fixed, is history rather
# than context. Both are still reported as excluded so the omission is visible.
OPEN_TICKET_STATUSES = frozenset({"open", "pending", "in_progress", "escalated"})
CLOSED_INCIDENT_STATUSES = frozenset({"resolved", "closed"})


@dataclass
class _Candidate:
    name: str
    origin: str
    content: str
    tokens: int


class ContextBuilder:
    """Turns component reports into one prompt block plus a context summary."""

    def __init__(self, settings: Settings) -> None:
        self._budget_tokens = settings.context_budget_tokens
        self._memory_threshold = settings.memory_relevance_threshold

    def build(self, memory: MemoryReport, retrieval: RetrievalReport) -> BuiltContext:
        excluded: list[ExcludedContext] = []
        candidates: list[_Candidate] = []

        candidates += self._retrieval_candidates(retrieval, excluded)
        candidates += self._memory_candidates(memory, excluded)

        included = self._apply_budget(candidates, excluded)
        prompt = "\n\n".join(section.content for section in included)

        return BuiltContext(
            prompt=prompt,
            summary=ContextSummary(
                sources=[section.name for section in included],
                size_chars=len(prompt),
                estimated_tokens=estimate_tokens(prompt),
                budget_tokens=self._budget_tokens,
                included=included,
                excluded=excluded,
            ),
        )

    def _retrieval_candidates(
        self, retrieval: RetrievalReport, excluded: list[ExcludedContext]
    ) -> list[_Candidate]:
        if retrieval.status is ComponentStatus.DISABLED:
            excluded.append(
                ExcludedContext(
                    name="structured retrieval",
                    origin=RETRIEVAL_ORIGIN,
                    reason=ExclusionReason.COMPONENT_DISABLED,
                    detail="retrieval_enabled=false for this request",
                )
            )
            return []
        if retrieval.status is ComponentStatus.UNAVAILABLE and not retrieval.sources:
            excluded.append(
                ExcludedContext(
                    name="structured retrieval",
                    origin=RETRIEVAL_ORIGIN,
                    reason=ExclusionReason.COMPONENT_UNAVAILABLE,
                    detail=retrieval.error,
                )
            )
            return []

        by_name = {source.name: source for source in retrieval.sources}
        ordered = [by_name[name] for name in SOURCE_PRIORITY if name in by_name]
        ordered += [s for s in retrieval.sources if s.name not in SOURCE_PRIORITY]

        candidates: list[_Candidate] = []
        for source in ordered:
            if source.status is ComponentStatus.UNAVAILABLE:
                excluded.append(
                    ExcludedContext(
                        name=source.name,
                        origin=RETRIEVAL_ORIGIN,
                        reason=ExclusionReason.COMPONENT_UNAVAILABLE,
                        detail=source.error,
                    )
                )
                continue

            records = self._keep_current_records(source, excluded)
            if not records:
                excluded.append(
                    ExcludedContext(
                        name=source.name,
                        origin=RETRIEVAL_ORIGIN,
                        reason=ExclusionReason.NO_DATA,
                        detail=f"{source.tool} returned nothing usable",
                    )
                )
                continue

            content = _format_source(source, records)
            candidates.append(
                _Candidate(
                    name=source.name,
                    origin=RETRIEVAL_ORIGIN,
                    content=content,
                    tokens=estimate_tokens(content),
                )
            )
        return candidates

    def _keep_current_records(
        self, source: RetrievedSource, excluded: list[ExcludedContext]
    ) -> list[dict]:
        if source.name == SOURCE_TICKETS:
            keep, drop = _partition(
                source.records, lambda r: str(r.get("status", "")).lower() in OPEN_TICKET_STATUSES
            )
        elif source.name == SOURCE_INCIDENTS:
            keep, drop = _partition(
                source.records,
                lambda r: str(r.get("status", "")).lower() not in CLOSED_INCIDENT_STATUSES,
            )
        else:
            return source.records

        for record in drop:
            excluded.append(
                ExcludedContext(
                    name=f"{source.name}: {record.get('id', 'record')}",
                    origin=RETRIEVAL_ORIGIN,
                    reason=ExclusionReason.NOT_RELEVANT,
                    detail=f"status={record.get('status')}",
                )
            )
        return keep

    def _memory_candidates(
        self, memory: MemoryReport, excluded: list[ExcludedContext]
    ) -> list[_Candidate]:
        if memory.status is ComponentStatus.DISABLED:
            excluded.append(
                ExcludedContext(
                    name="memory",
                    origin=MEMORY_ORIGIN,
                    reason=ExclusionReason.COMPONENT_DISABLED,
                    detail="memory_enabled=false for this request",
                )
            )
            return []
        if memory.status is ComponentStatus.UNAVAILABLE:
            excluded.append(
                ExcludedContext(
                    name="memory",
                    origin=MEMORY_ORIGIN,
                    reason=ExclusionReason.COMPONENT_UNAVAILABLE,
                    detail=memory.error,
                )
            )
            return []

        candidates: list[_Candidate] = []
        for entry in memory.entries:
            # A memory with no score was ranked by the service itself and is
            # taken on trust; a scored one must clear the bar. Stale memory that
            # slips through actively misleads, so the cut is explicit.
            if entry.relevance is not None and entry.relevance < self._memory_threshold:
                excluded.append(
                    ExcludedContext(
                        name=f"memory: {entry.id}",
                        origin=MEMORY_ORIGIN,
                        reason=ExclusionReason.BELOW_RELEVANCE_THRESHOLD,
                        estimated_tokens=estimate_tokens(entry.text),
                        detail=f"relevance {entry.relevance} < {self._memory_threshold}",
                    )
                )
                continue

            score = "" if entry.relevance is None else f" (relevance {entry.relevance})"
            content = f"## memory: {entry.id}{score}\n{entry.text}"
            candidates.append(
                _Candidate(
                    name=f"memory: {entry.id}",
                    origin=MEMORY_ORIGIN,
                    content=content,
                    tokens=estimate_tokens(content),
                )
            )
        return candidates

    def _apply_budget(
        self, candidates: list[_Candidate], excluded: list[ExcludedContext]
    ) -> list[ContextSection]:
        included: list[ContextSection] = []
        spent = 0
        for candidate in candidates:
            if spent + candidate.tokens > self._budget_tokens:
                excluded.append(
                    ExcludedContext(
                        name=candidate.name,
                        origin=candidate.origin,
                        reason=ExclusionReason.CONTEXT_BUDGET_EXCEEDED,
                        estimated_tokens=candidate.tokens,
                        detail=f"{spent}/{self._budget_tokens} tokens already used",
                    )
                )
                continue
            spent += candidate.tokens
            included.append(
                ContextSection(
                    name=candidate.name,
                    origin=candidate.origin,
                    content=candidate.content,
                    estimated_tokens=candidate.tokens,
                )
            )
        return included


def _partition(records: list[dict], keep_if) -> tuple[list[dict], list[dict]]:
    keep = [r for r in records if keep_if(r)]
    drop = [r for r in records if not keep_if(r)]
    return keep, drop


def _format_source(source: RetrievedSource, records: list[dict]) -> str:
    rows = "\n".join(
        "- " + " | ".join(f"{key}={value}" for key, value in record.items()) for record in records
    )
    return f"## {source.name} (via {source.tool})\n{rows}"
