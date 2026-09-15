"""In-process structured retrieval fake."""

from app.config import Settings
from app.data import sample_data
from app.models.execution import ComponentStatus, RetrievalReport, RetrievedSource
from app.retrieval.context_retriever_client import (
    TOOL_FILTER_API_USAGE,
    TOOL_FILTER_INCIDENTS,
    TOOL_FILTER_SUBSCRIPTION,
    TOOL_FILTER_TICKETS,
    TOOL_GET_CUSTOMER,
)
from app.retrieval.service import (
    SOURCE_API_USAGE,
    SOURCE_CUSTOMER,
    SOURCE_INCIDENTS,
    SOURCE_SUBSCRIPTION,
    SOURCE_TICKETS,
)
from app.telemetry.timing import Stopwatch


class StubContextRetrieval:
    """Serves the same five sources from the synthetic dataset in process.

    It reports the tool name it stands in for, so the inspector shows the query
    that would have run against Context Retriever. Status is STUB: the records
    are real, the round trip is not.
    """

    def __init__(self, settings: Settings) -> None:
        self.status = ComponentStatus.STUB

    async def retrieve_customer_context(self, customer_id: str) -> RetrievalReport:
        with Stopwatch() as timer:
            customer = sample_data.customer_by_id(customer_id)
            sources = [
                _source(
                    SOURCE_CUSTOMER,
                    TOOL_GET_CUSTOMER,
                    {"id": customer_id},
                    [customer.model_dump()] if customer else [],
                ),
                _source(
                    SOURCE_SUBSCRIPTION,
                    TOOL_FILTER_SUBSCRIPTION,
                    {"customer_id": customer_id},
                    [s.model_dump() for s in sample_data.subscriptions_for(customer_id)],
                ),
                _source(
                    SOURCE_API_USAGE,
                    TOOL_FILTER_API_USAGE,
                    {"customer_id": customer_id},
                    [u.model_dump() for u in sample_data.usage_for(customer_id)],
                ),
                _source(
                    SOURCE_TICKETS,
                    TOOL_FILTER_TICKETS,
                    {"customer_id": customer_id},
                    [t.model_dump() for t in sample_data.tickets_for(customer_id)],
                ),
            ]
            if customer:
                sources.append(
                    _source(
                        SOURCE_INCIDENTS,
                        TOOL_FILTER_INCIDENTS,
                        {"region": customer.region},
                        [i.model_dump() for i in sample_data.incidents_in(customer.region)],
                    )
                )

        return RetrievalReport(
            status=ComponentStatus.STUB,
            duration_ms=timer.elapsed_ms,
            sources=sources,
        )


def _source(
    name: str, tool: str, arguments: dict[str, str | int | float], records: list[dict]
) -> RetrievedSource:
    return RetrievedSource(
        name=name,
        tool=tool,
        arguments=arguments,
        records=records,
        status=ComponentStatus.STUB,
    )
