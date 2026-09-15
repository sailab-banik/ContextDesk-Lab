"""Synthetic support records for the fictional SaaS platform.

Small on purpose. The domain exists only so that structured retrieval has
something real to fetch; CUST-1001 is the customer the three demo scenarios in
PLAN.md are written against.
"""

from app.models.domain import (
    ApiUsage,
    Customer,
    Incident,
    Subscription,
    SupportTicket,
)

DEMO_CUSTOMER_ID = "CUST-1001"

CUSTOMERS: list[Customer] = [
    Customer(id="CUST-1001", name="Aurora Labs", region="us-east", plan_id="PLAN-PRO"),
    Customer(id="CUST-1002", name="Northwind Retail", region="eu-west", plan_id="PLAN-SCALE"),
    Customer(id="CUST-1003", name="Beacon Health", region="us-west", plan_id="PLAN-STARTER"),
    Customer(id="CUST-1004", name="Kestrel Freight", region="us-east", plan_id="PLAN-STARTER"),
]

SUBSCRIPTIONS: list[Subscription] = [
    Subscription(id="SUB-2001", customer_id="CUST-1001", plan="Pro", api_limit=250_000),
    Subscription(id="SUB-2002", customer_id="CUST-1002", plan="Scale", api_limit=1_000_000),
    Subscription(id="SUB-2003", customer_id="CUST-1003", plan="Starter", api_limit=25_000),
    Subscription(id="SUB-2004", customer_id="CUST-1004", plan="Starter", api_limit=25_000),
]

# CUST-1001 is at 93% of plan limit with latency well above the others: enough
# for the assistant to say something specific rather than generic.
API_USAGE: list[ApiUsage] = [
    ApiUsage(
        id="USAGE-1001",
        customer_id="CUST-1001",
        requests_today=232_400,
        average_latency=812.5,
        error_rate=0.031,
    ),
    ApiUsage(
        id="USAGE-1002",
        customer_id="CUST-1002",
        requests_today=410_900,
        average_latency=184.2,
        error_rate=0.004,
    ),
    ApiUsage(
        id="USAGE-1003",
        customer_id="CUST-1003",
        requests_today=6_120,
        average_latency=141.7,
        error_rate=0.002,
    ),
    ApiUsage(
        id="USAGE-1004",
        customer_id="CUST-1004",
        requests_today=19_450,
        average_latency=298.4,
        error_rate=0.011,
    ),
]

SUPPORT_TICKETS: list[SupportTicket] = [
    SupportTicket(
        id="TICK-3001",
        customer_id="CUST-1001",
        issue_type="Elevated API latency on the events endpoint",
        status="open",
        created_at="2026-09-02T09:14:00Z",
    ),
    SupportTicket(
        id="TICK-3002",
        customer_id="CUST-1001",
        issue_type="Webhook retries exhausted during peak traffic",
        status="resolved",
        created_at="2026-08-21T16:02:00Z",
    ),
    SupportTicket(
        id="TICK-3003",
        customer_id="CUST-1002",
        issue_type="Invoice address change request",
        status="open",
        created_at="2026-09-10T11:37:00Z",
    ),
    SupportTicket(
        id="TICK-3004",
        customer_id="CUST-1003",
        issue_type="API key rotation guidance",
        status="resolved",
        created_at="2026-07-29T08:45:00Z",
    ),
    SupportTicket(
        id="TICK-3005",
        customer_id="CUST-1004",
        issue_type="Rate limit errors on batch import",
        status="open",
        created_at="2026-09-12T14:20:00Z",
    ),
]

# An active us-east incident is what lets scenario 1 connect a customer
# complaint to a platform-side cause.
INCIDENTS: list[Incident] = [
    Incident(
        id="INC-4001",
        service="events-api",
        region="us-east",
        status="active",
        description=(
            "Elevated p95 latency on the events API in us-east caused by a degraded "
            "upstream queue partition. Mitigation in progress."
        ),
    ),
    Incident(
        id="INC-4002",
        service="billing",
        region="eu-west",
        status="resolved",
        description="Delayed invoice generation in eu-west following a scheduled migration.",
    ),
    Incident(
        id="INC-4003",
        service="webhooks",
        region="us-east",
        status="resolved",
        description="Webhook delivery backlog in us-east cleared after queue capacity increase.",
    ),
    Incident(
        id="INC-4004",
        service="dashboard",
        region="us-west",
        status="monitoring",
        description="Intermittent dashboard load failures in us-west under investigation.",
    ),
]

# Seeded directly as long-term memories. Automatic session -> long-term
# promotion happens minutes later and cannot be relied on during a demo, so
# scenario 1's "again" is backed by memories written on purpose.
SEED_MEMORIES: list[dict[str, object]] = [
    {
        "id": "MEM-5001",
        "owner_id": "CUST-1001",
        "text": (
            "On 2026-09-02 Aurora Labs reported that the events API felt slow, with "
            "occasional timeouts during their evening batch window. Support opened "
            "ticket TICK-3001 and asked them to report back if it recurred."
        ),
        "topics": ["latency", "events-api", "support-history"],
    },
    {
        "id": "MEM-5002",
        "owner_id": "CUST-1001",
        "text": (
            "Aurora Labs runs a nightly batch job between 22:00 and 01:00 UTC that "
            "accounts for most of their daily API volume."
        ),
        "topics": ["usage-pattern", "batch"],
    },
    {
        "id": "MEM-5003",
        "owner_id": "CUST-1001",
        "text": (
            "Aurora Labs prefers concise answers with concrete numbers and asked not "
            "to be walked through basic troubleshooting steps."
        ),
        "topics": ["preference", "tone"],
    },
    {
        "id": "MEM-5004",
        "owner_id": "CUST-1002",
        "text": (
            "Northwind Retail asked about upgrading to a higher API limit ahead of "
            "their November peak season."
        ),
        "topics": ["plan", "upgrade"],
    },
]


def customer_by_id(customer_id: str) -> Customer | None:
    return next((c for c in CUSTOMERS if c.id == customer_id), None)


def subscriptions_for(customer_id: str) -> list[Subscription]:
    return [s for s in SUBSCRIPTIONS if s.customer_id == customer_id]


def usage_for(customer_id: str) -> list[ApiUsage]:
    return [u for u in API_USAGE if u.customer_id == customer_id]


def tickets_for(customer_id: str) -> list[SupportTicket]:
    return [t for t in SUPPORT_TICKETS if t.customer_id == customer_id]


def incidents_in(region: str) -> list[Incident]:
    return [i for i in INCIDENTS if i.region == region]


def memories_for(owner_id: str) -> list[dict[str, object]]:
    return [m for m in SEED_MEMORIES if m["owner_id"] == owner_id]
