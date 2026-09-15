"""The structured retrieval seam.

Retrieval fetches business data and returns plain records. Redis keys and MCP
envelopes stop at this boundary and never travel upward.
"""

from typing import Protocol

from app.models.execution import ComponentStatus, RetrievalReport

# The five sources fetched for a customer, in the order they are queried. Each
# is one round trip, which is the cost side of the retrieval tradeoff and is
# reported per source so it stays visible.
SOURCE_CUSTOMER = "customer"
SOURCE_SUBSCRIPTION = "subscription"
SOURCE_API_USAGE = "api_usage"
SOURCE_TICKETS = "support_tickets"
SOURCE_INCIDENTS = "regional_incidents"


class ContextRetrievalService(Protocol):
    status: ComponentStatus

    async def retrieve_customer_context(self, customer_id: str) -> RetrievalReport:
        """Fetch every structured source available for this customer.

        Selection is deliberately not done here: the builder decides what
        reaches the model, so the inspector can show what was fetched and
        then dropped.
        """
        ...
