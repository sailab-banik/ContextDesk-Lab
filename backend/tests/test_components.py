"""Component boundaries: stub honesty, MCP unwrapping, and the seed key templates."""

import json

import pytest

from app.cache import build_semantic_cache
from app.config import Settings
from app.data.seed_redis import KEY_TEMPLATES
from app.llm import build_llm_service
from app.memory import build_memory_service
from app.models.execution import ComponentStatus
from app.retrieval import build_retrieval_service
from app.retrieval.context_retriever_client import _unwrap_mcp_results


def mcp_response(payload: object) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def test_mcp_envelope_is_unwrapped_to_plain_records():
    records = _unwrap_mcp_results(mcp_response({"results": [{"id": "CUST-1001"}]}))

    assert records == [{"id": "CUST-1001"}]


def test_a_single_record_response_is_still_a_list():
    """`get_..._by_id` returns one record; callers should not branch on shape."""
    assert _unwrap_mcp_results(mcp_response({"id": "CUST-1001"})) == [{"id": "CUST-1001"}]


def test_a_malformed_envelope_raises_at_the_boundary():
    with pytest.raises((KeyError, IndexError, json.JSONDecodeError)):
        _unwrap_mcp_results({"unexpected": True})


def test_stub_mode_forces_every_component_to_a_stub(settings: Settings):
    assert build_memory_service(settings).status is ComponentStatus.STUB
    assert build_retrieval_service(settings).status is ComponentStatus.STUB
    assert build_semantic_cache(settings).status is ComponentStatus.STUB


async def test_stub_llm_declares_itself_rather_than_inventing_an_answer(settings: Settings):
    llm = build_llm_service(settings)

    result = await llm.generate("What plan am I currently on?", "## subscription\n- plan=Pro")

    assert result.status is ComponentStatus.STUB
    assert "stub" in result.text.lower()
    assert result.input_tokens > 0


async def test_stub_cache_reports_its_own_threshold_not_langcache_default(settings: Settings):
    cache = build_semantic_cache(settings)

    assert cache.threshold == settings.stub_similarity_threshold
    assert cache.threshold != settings.langcache_similarity_threshold


async def test_a_near_miss_reports_the_score_that_produced_it(settings: Settings):
    """A miss has to say how close it came, or the threshold is unreadable."""
    cache = build_semantic_cache(settings)
    await cache.store("how do I reset my password", "Use the sign-in page.")

    lookup = await cache.lookup("what is my current api limit")

    assert lookup.report.hit is False
    assert lookup.response is None
    assert lookup.report.similarity is not None
    assert lookup.report.similarity < lookup.report.threshold
    assert lookup.report.matched_prompt == "how do I reset my password"


async def test_stub_retrieval_reports_the_tool_it_stands_in_for(settings: Settings):
    report = await build_retrieval_service(settings).retrieve_customer_context("CUST-1001")

    tools = {source.name: source.tool for source in report.sources}
    assert tools["customer"] == "get_customer_by_id"
    assert tools["regional_incidents"] == "filter_incident"
    assert report.status is ComponentStatus.STUB


async def test_retrieval_of_an_unknown_customer_returns_empty_sources(settings: Settings):
    report = await build_retrieval_service(settings).retrieve_customer_context("CUST-9999")

    assert all(source.record_count == 0 for source in report.sources)
    # No customer record means no region, so the regional source is not queried.
    assert "regional_incidents" not in {source.name for source in report.sources}


async def test_memory_is_scoped_to_its_owner(settings: Settings):
    memory = build_memory_service(settings)

    report = await memory.get_relevant_memory("CUST-1002", "Tell me about my plan")

    assert report.entries
    assert all("Northwind" in entry.text for entry in report.entries)


def test_seed_keys_match_the_templates_registered_in_the_console():
    keys = [
        template.format(**record.model_dump())
        for template, records in KEY_TEMPLATES
        for record in records
    ]

    assert "customer:CUST-1001" in keys
    assert "subscription:SUB-2001" in keys
    assert "api_usage:USAGE-1001" in keys
    assert "ticket:TICK-3001" in keys
    assert "incident:INC-4001" in keys
