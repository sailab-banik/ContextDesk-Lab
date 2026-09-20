"""Print the MCP tools the Context Retriever surface actually generates.

Context Retriever derives its tools from the registered surface, not from
`surface_models.py` on disk, so the two drift apart silently: the models file
declares an index, nobody re-registers the surface, and every call to the tool
that index would have generated comes back as `unknown tool`. That failure
names the tool but never says what does exist, which is the one thing needed to
tell a missing entity from a missing index.

Run it whenever retrieval reports UNAVAILABLE:

    uv run python -m app.data.inspect_surface
"""

import asyncio
import json

from context_surfaces import UnifiedClient

from app.config import get_settings
from app.retrieval.context_retriever_client import (
    TOOL_FILTER_API_USAGE,
    TOOL_FILTER_INCIDENTS,
    TOOL_FILTER_SUBSCRIPTION,
    TOOL_FILTER_TICKETS,
    TOOL_GET_CUSTOMER,
)

# Kept in step with the TOOL_* constants rather than re-spelling them, so this
# check cannot drift from what the retrieval client calls.
TOOLS_THE_APP_CALLS = (
    TOOL_GET_CUSTOMER,
    TOOL_FILTER_SUBSCRIPTION,
    TOOL_FILTER_API_USAGE,
    TOOL_FILTER_TICKETS,
    TOOL_FILTER_INCIDENTS,
)


async def inspect_surface() -> None:
    settings = get_settings()
    if not settings.context_retriever_agent_key:
        raise SystemExit("CONTEXT_RETRIEVER_AGENT_KEY is not set — nothing to inspect.")

    client = UnifiedClient(
        api_url=settings.context_retriever_api_url or None,
        mcp_url=settings.context_retriever_mcp_url or None,
    )
    # Both URLs fall back to Redis Cloud defaults when unset, and the default
    # MCP host is region-pinned, so printing what was resolved turns a wrong
    # region from a silent empty tool list into an obvious one.
    print(f"api_url: {client.api_url}")
    print(f"mcp_url: {client.mcp_url}\n")

    tools = await client.list_tools(agent_key=settings.context_retriever_agent_key)
    available = {tool.get("name") for tool in tools}

    print(f"{len(tools)} tool(s) registered:")
    for tool in sorted(tools, key=lambda item: item.get("name") or ""):
        schema = tool.get("inputSchema") or tool.get("input_schema") or {}
        properties = list((schema.get("properties") or {}).keys())
        required = schema.get("required") or []
        print(f"  {tool.get('name')}")
        print(f"      arguments={properties} required={required}")

    print("\nWhat the retrieval client calls:")
    for name in TOOLS_THE_APP_CALLS:
        print(f"  {'present' if name in available else 'MISSING'}  {name}")

    missing = [name for name in TOOLS_THE_APP_CALLS if name not in available]
    if missing:
        print(
            "\nMissing: "
            + ", ".join(missing)
            + "\n\nA tool goes missing for one of two reasons, and the list above tells"
            "\nthem apart: if the entity has no tools at all, the surface never"
            "\nregistered that model; if it has some but not this one, the index that"
            "\ngenerates it was never declared. The first needs a re-register:"
            "\n  ctxctl surface update <surface_id> --models app/data/surface_models.py"
            "\nThe second needs the index added to surface_models.py first."
        )

    print("\nFull schema dump:")
    print(json.dumps(tools, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(inspect_surface())
