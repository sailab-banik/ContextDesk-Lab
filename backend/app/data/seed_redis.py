"""Load the synthetic dataset into Redis.

Context Retriever reads records that are *already* in Redis under their key
templates, so this must run before the Context Retriever service is created in
the Redis Cloud console and before any retrieval tool will return anything.

    uv run python -m app.data.seed_redis
"""

import sys

from pydantic import BaseModel
from redis import Redis

from app.config import get_settings
from app.data.sample_data import (
    API_USAGE,
    CUSTOMERS,
    INCIDENTS,
    SUBSCRIPTIONS,
    SUPPORT_TICKETS,
)

# Key templates from PLAN.md, Milestone 0. The entity registration in the
# console points at these exact prefixes, so they are not free to change on one
# side only.
KEY_TEMPLATES: list[tuple[str, list[BaseModel]]] = [
    ("customer:{id}", list(CUSTOMERS)),
    ("subscription:{id}", list(SUBSCRIPTIONS)),
    ("api_usage:{id}", list(API_USAGE)),
    ("ticket:{id}", list(SUPPORT_TICKETS)),
    ("incident:{id}", list(INCIDENTS)),
]


def seed(redis_url: str) -> int:
    client = Redis.from_url(redis_url, decode_responses=True)
    written = 0

    for template, records in KEY_TEMPLATES:
        for record in records:
            payload = record.model_dump()
            key = template.format(**payload)
            # Written as JSON documents: Context Retriever indexes RedisJSON
            # fields, and TAG values must already be strings when written
            # directly rather than through a ContextModel.
            client.json().set(key, "$", payload)
            written += 1
        print(f"  {template:22} {len(records):>3} records")

    client.close()
    return written


def main() -> int:
    settings = get_settings()
    if not settings.redis_url:
        print(
            "REDIS_URL is not set. Create the database first (PLAN.md, Milestone 0) "
            "and put its connection string in the root .env.",
            file=sys.stderr,
        )
        return 1

    print(f"Seeding {settings.redis_url.split('@')[-1]}")
    written = seed(settings.redis_url)
    print(f"\n{written} records written. Register the entities in the console next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
