"""Context Retriever-backed structured retrieval."""

import json
from typing import Any

from context_surfaces import UnifiedClient

from app.config import Settings
from app.models.execution import ComponentStatus, RetrievedSource, RetrievalReport
from app.retrieval.service import (
    SOURCE_API_USAGE,
    SOURCE_CUSTOMER,
    SOURCE_INCIDENTS,
    SOURCE_SUBSCRIPTION,
    SOURCE_TICKETS,
)
from app.telemetry.timing import Stopwatch

# Context Retriever generates one filter tool per entity, not one per indexed
# field: the field travels inside the request as a tag condition. Run
# `python -m app.data.inspect_surface` to see the live list rather than
# inferring these names.
#
# The entity segment is the model class name lowercased, so `ApiUsage` becomes
# `apiusage` — it does not follow the `api_usage:{id}` key template.
TOOL_GET_CUSTOMER = "get_customer_by_id"
TOOL_FILTER_SUBSCRIPTION = "filter_subscription"
TOOL_FILTER_API_USAGE = "filter_apiusage"
TOOL_FILTER_TICKETS = "filter_ticket"
TOOL_FILTER_INCIDENTS = "filter_incident"


class ContextRetrieverService:
    """Structured business data over Redis Iris Context Retriever.

    The retriever reads records already written to Redis under their key
    templates, so `app/data/seed_redis.py` must have run before any of these
    tools return anything.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = UnifiedClient(
            api_url=settings.context_retriever_api_url or None,
            mcp_url=settings.context_retriever_mcp_url or None,
        )
        self._agent_key = settings.context_retriever_agent_key
        self.status = ComponentStatus.OK

    async def retrieve_customer_context(self, customer_id: str) -> RetrievalReport:
        sources: list[RetrievedSource] = []

        customer_source = await self._query(
            SOURCE_CUSTOMER, TOOL_GET_CUSTOMER, {"id": customer_id}
        )
        sources.append(customer_source)

        for name, tool in (
            (SOURCE_SUBSCRIPTION, TOOL_FILTER_SUBSCRIPTION),
            (SOURCE_API_USAGE, TOOL_FILTER_API_USAGE),
            (SOURCE_TICKETS, TOOL_FILTER_TICKETS),
        ):
            sources.append(
                await self._query(
                    name,
                    tool,
                    {"customer_id": customer_id},
                    _tag_condition("customer_id", customer_id),
                )
            )

        # Incidents are regional, so this source depends on the customer record
        # having come back first.
        region = _first_value(customer_source.records, "region")
        if region:
            sources.append(
                await self._query(
                    SOURCE_INCIDENTS,
                    TOOL_FILTER_INCIDENTS,
                    {"region": region},
                    _tag_condition("region", region),
                )
            )

        failed = [source for source in sources if source.status is ComponentStatus.UNAVAILABLE]
        return RetrievalReport(
            # Partial failure is reported as failure: a half-retrieved context
            # must not read as a healthy one.
            status=ComponentStatus.UNAVAILABLE if failed else ComponentStatus.OK,
            duration_ms=round(sum(source.duration_ms for source in sources), 2),
            sources=sources,
            error="; ".join(f"{source.name}: {source.error}" for source in failed) or None,
        )

    async def _query(
        self,
        name: str,
        tool: str,
        arguments: dict[str, str | int | float],
        wire_arguments: dict[str, Any] | None = None,
    ) -> RetrievedSource:
        """Call one tool and record it as the flat query it represents.

        `arguments` is the field/value pair the inspector shows; the condition
        envelope a filter tool actually takes is passed separately so that
        shape stays inside this layer.
        """
        with Stopwatch() as timer:
            try:
                response = await self._client.query_tool(
                    agent_key=self._agent_key,
                    tool_name=tool,
                    arguments=dict(wire_arguments if wire_arguments is not None else arguments),
                )
                records = _unwrap_mcp_results(response)
            except Exception as exc:
                return RetrievedSource(
                    name=name,
                    tool=tool,
                    arguments=arguments,
                    duration_ms=timer.elapsed_ms,
                    status=ComponentStatus.UNAVAILABLE,
                    error=str(exc),
                )

        return RetrievedSource(
            name=name,
            tool=tool,
            arguments=arguments,
            records=records,
            duration_ms=timer.elapsed_ms,
            status=ComponentStatus.OK,
        )


def _tag_condition(field: str, value: str) -> dict[str, Any]:
    """Wrap one exact-match condition in the shape the filter tools expect.

    Filter tools are per entity, not per field, so the field being matched on
    travels in the request body rather than in the tool name. Conditions are
    ANDed; this project only ever needs one.
    """
    return {"tag_conditions": [{"field": field, "value": value}]}


def _unwrap_mcp_results(response: Any) -> list[dict]:
    """Strip the MCP envelope, leaving plain records.

    Tool results arrive as MCP content blocks holding a JSON string. Nothing
    above the retrieval layer should have to know that.
    """
    content = response["content"]
    payload = json.loads(content[0]["text"])
    results = payload.get("results", payload)
    return results if isinstance(results, list) else [results]


def _first_value(records: list[dict], field: str) -> str | None:
    for record in records:
        value = record.get(field)
        if value:
            return str(value)
    return None
