"""Write the demo's long-term memories directly into Agent Memory.

Agent Memory promotes session events to long-term memory on its own, but
asynchronously and minutes later. Scenario 1 turns on the assistant remembering
an earlier complaint, so those memories are created outright rather than waited
for.

    uv run python -m app.data.seed_memories
"""

import asyncio
import sys

from redis_agent_memory import AgentMemory

from app.config import get_settings
from app.data.sample_data import SEED_MEMORIES


async def seed(endpoint: str, store_id: str, api_key: str) -> int:
    memory = AgentMemory(endpoint, store_id=store_id, api_key=api_key)
    await memory.bulk_create_long_term_memories_async(
        memories=[
            {
                "id": str(record["id"]),
                "text": str(record["text"]),
                "owner_id": str(record["owner_id"]),
                "memory_type": "semantic",
                "topics": list(record["topics"]),  # type: ignore[arg-type]
            }
            for record in SEED_MEMORIES
        ]
    )
    return len(SEED_MEMORIES)


def main() -> int:
    settings = get_settings()
    if not settings.memory_configured:
        print(
            "Agent Memory is not configured. Create the service first (PLAN.md, "
            "Milestone 0) and put its endpoint, store id, and key in the root .env.",
            file=sys.stderr,
        )
        return 1

    written = asyncio.run(
        seed(
            settings.agent_memory_endpoint,
            settings.agent_memory_store_id,
            settings.agent_memory_key,
        )
    )
    print(f"{written} long-term memories created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
