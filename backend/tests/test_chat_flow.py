"""The orchestration path: what runs, what is skipped, and what the record says."""

import pytest

from app.cache import build_semantic_cache
from app.config import Settings
from app.llm import build_llm_service
from app.memory import build_memory_service
from app.models.chat import ChatRequest
from app.models.execution import ComponentStatus, ExecutionConfig, ExclusionReason
from app.models.results import LLMResult
from app.retrieval import build_retrieval_service
from app.services.chat_service import ChatService
from app.services.context_builder import ContextBuilder
from app.services.telemetry_service import TelemetryService


def make_chat_service(settings: Settings, llm=None) -> ChatService:
    return ChatService(
        settings=settings,
        memory=build_memory_service(settings),
        retrieval=build_retrieval_service(settings),
        cache=build_semantic_cache(settings),
        llm=llm or build_llm_service(settings),
        context_builder=ContextBuilder(settings),
        telemetry=TelemetryService(settings),
    )


async def test_stub_components_never_report_ok(settings: Settings):
    chat = make_chat_service(settings)

    result = await chat.handle_message(ChatRequest(message="My API is slow again."))

    record = result.execution
    assert record.memory.status is ComponentStatus.STUB
    assert record.retrieval.status is ComponentStatus.STUB
    assert record.cache.status is ComponentStatus.STUB
    assert record.llm.status is ComponentStatus.STUB


async def test_disabled_component_is_not_reported_as_failed(settings: Settings):
    chat = make_chat_service(settings)

    result = await chat.handle_message(
        ChatRequest(
            message="What plan am I currently on?",
            config=ExecutionConfig(memory_enabled=False, retrieval_enabled=True),
        )
    )

    memory = result.execution.memory
    assert memory.status is ComponentStatus.DISABLED
    assert memory.status is not ComponentStatus.UNAVAILABLE
    assert "memory_enabled=false" in (memory.skipped_reason or "")


async def test_retrieval_off_removes_the_data_the_answer_needs(settings: Settings):
    """Scenario 2's contrast: with retrieval disabled there is nothing to answer from."""
    chat = make_chat_service(settings)

    with_retrieval = await chat.handle_message(
        ChatRequest(
            message="What plan am I currently on?",
            config=ExecutionConfig(
                retrieval_enabled=True, memory_enabled=False, cache_enabled=False
            ),
        )
    )
    without = await chat.handle_message(
        ChatRequest(
            message="What plan am I currently on?",
            config=ExecutionConfig(
                retrieval_enabled=False, memory_enabled=False, cache_enabled=False
            ),
        )
    )

    assert "subscription" in with_retrieval.execution.context.sources
    assert without.execution.context.sources == []
    assert any(
        excluded.reason is ExclusionReason.COMPONENT_DISABLED
        and excluded.name == "structured retrieval"
        for excluded in without.execution.context.excluded
    )


async def test_cache_hit_skips_every_downstream_step(settings: Settings):
    """Scenario 3: a hit is only worth anything if it actually avoids the work."""
    chat = make_chat_service(settings)
    await chat.handle_message(ChatRequest(message="How do I generate a new API key?"))

    hit = await chat.handle_message(ChatRequest(message="How do I reset my API key?"))

    record = hit.execution
    assert record.cache.hit is True
    assert record.cache.similarity is not None
    assert record.cache.similarity >= record.cache.threshold
    assert record.cache.matched_prompt == "How do I generate a new API key?"
    assert record.llm.called is False
    assert record.llm.input_tokens == 0
    assert record.memory.skipped_reason == record.retrieval.skipped_reason


async def test_unrelated_message_is_a_miss_with_the_score_shown(settings: Settings):
    chat = make_chat_service(settings)
    await chat.handle_message(ChatRequest(message="How do I generate a new API key?"))

    miss = await chat.handle_message(ChatRequest(message="What plan am I currently on?"))

    assert miss.execution.cache.hit is False
    assert miss.execution.cache.similarity is not None
    assert miss.execution.llm.called is True


class FailingLLM:
    model = "unreachable-model"

    async def generate(self, message: str, context: str) -> LLMResult:
        return LLMResult(
            text="",
            model=self.model,
            status=ComponentStatus.UNAVAILABLE,
            duration_ms=12.5,
            error="connection refused",
        )


async def test_llm_failure_is_reported_not_papered_over(settings: Settings):
    chat = make_chat_service(settings, llm=FailingLLM())

    result = await chat.handle_message(ChatRequest(message="My API is slow again."))

    assert result.execution.llm.status is ComponentStatus.UNAVAILABLE
    assert result.execution.error == "connection refused"
    assert "could not be reached" in result.response
    # A failed answer must not be cached as if it had worked.
    assert result.execution.cache.stored is False


async def test_every_request_produces_one_record_with_ordered_steps(settings: Settings):
    telemetry = TelemetryService(settings)
    chat = ChatService(
        settings=settings,
        memory=build_memory_service(settings),
        retrieval=build_retrieval_service(settings),
        cache=build_semantic_cache(settings),
        llm=build_llm_service(settings),
        context_builder=ContextBuilder(settings),
        telemetry=telemetry,
    )

    result = await chat.handle_message(ChatRequest(message="My API is slow again."))

    assert [step.name for step in result.execution.steps] == [
        "cache lookup",
        "memory",
        "structured retrieval",
        "context assembly",
        "llm",
        "cache store",
    ]
    assert telemetry.get(result.execution.request_id) is not None


async def test_comparison_runs_every_configuration_without_writing_memory(settings: Settings):
    from app.models.chat import ComparisonRequest

    chat = make_chat_service(settings)
    memory = chat._memory  # noqa: SLF001 - asserting the turn was not recorded

    comparison = await chat.compare(ComparisonRequest(message="My API is slow again."))

    assert len(comparison.runs) == 4
    assert comparison.runs[0].execution.context.sources == []
    assert comparison.runs[-1].execution.context.sources != []
    assert memory.session_events == []


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (ExecutionConfig(memory_enabled=False, retrieval_enabled=False, cache_enabled=False), "llm only"),
        (ExecutionConfig(memory_enabled=True, retrieval_enabled=False, cache_enabled=False), "llm + memory"),
    ],
)
def test_config_label(config: ExecutionConfig, expected: str):
    assert config.label() == expected
