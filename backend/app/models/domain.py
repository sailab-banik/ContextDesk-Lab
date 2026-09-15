"""The synthetic support domain.

Deliberately small and flat: these records exist only to make structured
retrieval demonstrable. Flat scalar fields are also what the Context Retriever
indexes (TAG / TEXT / NUMERIC), so nothing here is nested.
"""

from pydantic import BaseModel


class Customer(BaseModel):
    id: str
    name: str
    region: str
    plan_id: str


class Subscription(BaseModel):
    id: str
    customer_id: str
    plan: str
    api_limit: int


class ApiUsage(BaseModel):
    id: str
    customer_id: str
    requests_today: int
    average_latency: float
    error_rate: float


class SupportTicket(BaseModel):
    id: str
    customer_id: str
    issue_type: str
    status: str
    created_at: str


class Incident(BaseModel):
    id: str
    service: str
    region: str
    status: str
    description: str
