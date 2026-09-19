"""Schema declaration for the Context Retriever surface.

This file is consumed by `ctxctl surface create --models`, not by the running
application. It tells Context Retriever which Redis keys hold which entities
and which fields to index, and the index types decide which MCP tools get
generated:

    tag     -> filter_<entity>_by_<field>
    text    -> search_<entity>_by_text
    numeric -> find_<entity>_by_<field>_range

Three things here are contracts with code elsewhere and are not free to change
on one side only:

1. `__redis_key_template__` must match `KEY_TEMPLATES` in `seed_redis.py`,
   which is what actually writes the records.
2. The class name determines the generated tool name, so it must match the
   `TOOL_*` constants in `app/retrieval/context_retriever_client.py`. The
   ticket entity is `Ticket`, not `SupportTicket`, for exactly this reason.
3. Field names and types mirror `app/models/domain.py`. A tag index over an
   int silently empties the entity's index, so every tag field is a `str`.
"""

from context_surfaces.context_model import ContextField, ContextModel


class Customer(ContextModel):
    """A customer account on the platform."""

    __redis_key_template__ = "customer:{id}"

    id: str = ContextField(description="Unique customer ID", is_key_component=True)
    name: str = ContextField(description="Customer or company name", index="text")
    region: str = ContextField(
        description="Deployment region, used to match regional incidents", index="tag"
    )
    plan_id: str = ContextField(description="ID of the subscribed plan")


class Subscription(ContextModel):
    """The plan a customer is on and the limits it carries."""

    __redis_key_template__ = "subscription:{id}"

    id: str = ContextField(description="Unique subscription ID", is_key_component=True)
    customer_id: str = ContextField(description="Owning customer ID", index="tag")
    plan: str = ContextField(description="Plan name, e.g. Starter or Growth", index="tag")
    api_limit: int = ContextField(
        description="Daily API request allowance for this plan", index="numeric"
    )


class ApiUsage(ContextModel):
    """Current API consumption, read against the subscription's limits."""

    __redis_key_template__ = "api_usage:{id}"

    id: str = ContextField(description="Unique usage record ID", is_key_component=True)
    customer_id: str = ContextField(description="Owning customer ID", index="tag")
    requests_today: int = ContextField(
        description="API requests made so far today", index="numeric"
    )
    average_latency: float = ContextField(
        description="Average request latency in milliseconds", index="numeric"
    )
    error_rate: float = ContextField(description="Fraction of requests returning an error")


class Ticket(ContextModel):
    """A support ticket raised by a customer."""

    __redis_key_template__ = "ticket:{id}"

    id: str = ContextField(description="Unique ticket ID", is_key_component=True)
    customer_id: str = ContextField(description="Reporting customer ID", index="tag")
    issue_type: str = ContextField(description="What the ticket is about", index="text")
    status: str = ContextField(description="open, pending, or resolved", index="tag")
    created_at: str = ContextField(description="ISO-8601 creation timestamp")


class Incident(ContextModel):
    """A platform incident, scoped to a region."""

    __redis_key_template__ = "incident:{id}"

    id: str = ContextField(description="Unique incident ID", is_key_component=True)
    service: str = ContextField(description="Affected internal service")
    region: str = ContextField(description="Region the incident affects", index="tag")
    status: str = ContextField(description="investigating, identified, or resolved", index="tag")
    description: str = ContextField(description="What is happening and its impact", index="text")
