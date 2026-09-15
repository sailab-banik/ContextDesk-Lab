"""The orchestrator.

Reads the execution config, gathers context from the components, checks the
cache, builds the context, calls the LLM, and returns the response together
with its execution record. It contains no Redis or provider-specific code: the
components each own that, and this file only coordinates them.
"""

from app.cache.service import SemanticCacheService
from app.config import Settings
from app.llm.service import LLMService
from app.memory.service import MemoryService
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonRun,
)
from app.models.execution import (
    ComponentStatus,
    ContextSummary,
    ExcludedContext,
    ExclusionReason,
    ExecutionConfig,
    LLMReport,
    MemoryReport,
    RetrievalReport,
)
from app.models.results import BuiltContext, CacheLookup
from app.retrieval.service import ContextRetrievalService
from app.services.context_builder import ContextBuilder
from app.services.telemetry_service import TelemetryService
from app.telemetry.execution_record import ExecutionRecordBuilder
from app.telemetry.metrics import estimate_cost_usd
from app.telemetry.timing import Stopwatch

# Experiment mode's default ladder: the same message with one more component
# each time. The full system is not assumed to win — that is the point of
# running all four.
COMPARISON_CONFIGS = [
    ExecutionConfig(memory_enabled=False, retrieval_enabled=False, cache_enabled=False),
    ExecutionConfig(memory_enabled=True, retrieval_enabled=False, cache_enabled=False),
    ExecutionConfig(memory_enabled=False, retrieval_enabled=True, cache_enabled=False),
    ExecutionConfig(memory_enabled=True, retrieval_enabled=True, cache_enabled=True),
]

CACHE_HIT_SKIP = "response served from the semantic cache"


class ChatService:
    def __init__(
        self,
        settings: Settings,
        memory: MemoryService,
        retrieval: ContextRetrievalService,
        cache: SemanticCacheService,
        llm: LLMService,
        context_builder: ContextBuilder,
        telemetry: TelemetryService,
    ) -> None:
        self._settings = settings
        self._memory = memory
        self._retrieval = retrieval
        self._cache = cache
        self._llm = llm
        self._context_builder = context_builder
        self._telemetry = telemetry

    async def handle_message(self, request: ChatRequest, record_turn: bool = True) -> ChatResponse:
        builder = ExecutionRecordBuilder(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message,
            config=request.config,
        )

        cached = await self._check_semantic_cache(builder, request)
        if cached is not None and cached.report.hit and cached.response is not None:
            return self._finish_from_cache(builder, request, cached.response, record_turn)

        builder.memory = await self._gather_memory(builder, request)
        builder.retrieval = await self._retrieve_structured_context(builder, request)

        context = self._build_context(builder)
        response, error = await self._call_llm(builder, request.message, context)

        if not error:
            await self._store_in_cache(builder, request.message, response)
        if record_turn:
            await self._record_turn(request, response)

        record = builder.finish(response=response, error=error)
        self._telemetry.record(record)
        return ChatResponse(response=response, execution=record)

    async def compare(self, request: ComparisonRequest) -> ComparisonResponse:
        """Run one message across several configurations.

        Each run is a full request and produces its own execution record, so the
        comparison is made of the same evidence the inspector shows. Turns are
        not written back to memory: four runs of one message would distort the
        history the next request reads.
        """
        configs = request.configs or COMPARISON_CONFIGS
        runs: list[ComparisonRun] = []
        for config in configs:
            result = await self.handle_message(
                ChatRequest(
                    message=request.message,
                    user_id=request.user_id,
                    session_id=request.session_id,
                    config=config,
                ),
                record_turn=False,
            )
            runs.append(
                ComparisonRun(
                    label=config.label(),
                    config=config,
                    response=result.response,
                    execution=result.execution,
                )
            )
        return ComparisonResponse(message=request.message, runs=runs)

    # --- steps -------------------------------------------------------------

    async def _check_semantic_cache(
        self, builder: ExecutionRecordBuilder, request: ChatRequest
    ) -> CacheLookup | None:
        if not request.config.cache_enabled:
            builder.cache.skipped_reason = "cache_enabled=false for this request"
            builder.add_step(
                "cache lookup", ComponentStatus.DISABLED, 0.0, "cache disabled for this request"
            )
            return None

        lookup = await self._cache.lookup(request.message)
        builder.cache = lookup.report
        builder.add_step(
            "cache lookup",
            lookup.report.status,
            lookup.report.duration_ms,
            _describe_cache(lookup),
        )
        return lookup

    async def _gather_memory(
        self, builder: ExecutionRecordBuilder, request: ChatRequest
    ) -> MemoryReport:
        if not request.config.memory_enabled:
            builder.add_step(
                "memory", ComponentStatus.DISABLED, 0.0, "memory disabled for this request"
            )
            return MemoryReport(
                status=ComponentStatus.DISABLED,
                skipped_reason="memory_enabled=false for this request",
            )

        report = await self._memory.get_relevant_memory(request.user_id, request.message)
        builder.add_step(
            "memory",
            report.status,
            report.duration_ms,
            report.error or f"{len(report.entries)} memories retrieved for {request.user_id}",
        )
        return report

    async def _retrieve_structured_context(
        self, builder: ExecutionRecordBuilder, request: ChatRequest
    ) -> RetrievalReport:
        if not request.config.retrieval_enabled:
            builder.add_step(
                "structured retrieval",
                ComponentStatus.DISABLED,
                0.0,
                "retrieval disabled for this request",
            )
            return RetrievalReport(
                status=ComponentStatus.DISABLED,
                skipped_reason="retrieval_enabled=false for this request",
            )

        report = await self._retrieval.retrieve_customer_context(request.user_id)
        records = sum(source.record_count for source in report.sources)
        builder.add_step(
            "structured retrieval",
            report.status,
            report.duration_ms,
            report.error or f"{len(report.sources)} sources queried, {records} records returned",
        )
        return report

    def _build_context(self, builder: ExecutionRecordBuilder) -> BuiltContext:
        with Stopwatch() as timer:
            context = self._context_builder.build(builder.memory, builder.retrieval)

        builder.context = context.summary
        builder.memory.used_count = len(
            [s for s in context.summary.included if s.origin == "memory"]
        )
        builder.add_step(
            "context assembly",
            ComponentStatus.OK,
            timer.elapsed_ms,
            f"{len(context.summary.included)} sections included "
            f"(~{context.summary.estimated_tokens} tokens), "
            f"{len(context.summary.excluded)} excluded",
        )
        return context

    async def _call_llm(
        self, builder: ExecutionRecordBuilder, message: str, context: BuiltContext
    ) -> tuple[str, str | None]:
        result = await self._llm.generate(message, context.prompt)
        builder.llm = LLMReport(
            status=result.status,
            called=True,
            duration_ms=result.duration_ms,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=estimate_cost_usd(
                result.input_tokens, result.output_tokens, self._settings
            ),
            error=result.error,
        )
        builder.add_step(
            "llm",
            result.status,
            result.duration_ms,
            result.error
            or f"{result.model}: {result.input_tokens} in / {result.output_tokens} out",
        )

        if result.status is ComponentStatus.UNAVAILABLE:
            # Reported as a failure rather than papered over with a canned
            # answer that would read like a working system.
            return (f"The language model could not be reached: {result.error}", result.error)
        return result.text, None

    async def _store_in_cache(
        self, builder: ExecutionRecordBuilder, message: str, response: str
    ) -> None:
        if builder.cache.status not in (ComponentStatus.OK, ComponentStatus.STUB):
            return
        builder.cache.stored = await self._cache.store(message, response)
        builder.add_step(
            "cache store",
            builder.cache.status,
            0.0,
            "response cached for future lookups"
            if builder.cache.stored
            else "cache write failed",
        )

    async def _record_turn(self, request: ChatRequest, response: str) -> None:
        if not request.config.memory_enabled:
            return
        await self._memory.store_memory(
            request.session_id, request.user_id, "user", request.message
        )
        await self._memory.store_memory(
            request.session_id, request.user_id, "assistant", response
        )

    def _finish_from_cache(
        self,
        builder: ExecutionRecordBuilder,
        request: ChatRequest,
        response: str,
        record_turn: bool,
    ) -> ChatResponse:
        """A hit ends the request: no memory read, no retrieval, no LLM call.

        Those skipped steps are the saving the cache exists to produce, so each
        is recorded with the reason rather than silently missing.
        """
        builder.memory = MemoryReport(
            status=ComponentStatus.DISABLED, skipped_reason=CACHE_HIT_SKIP
        )
        builder.retrieval = RetrievalReport(
            status=ComponentStatus.DISABLED, skipped_reason=CACHE_HIT_SKIP
        )
        builder.llm = LLMReport(
            status=ComponentStatus.DISABLED, called=False, skipped_reason=CACHE_HIT_SKIP
        )
        for step in ("memory", "structured retrieval", "llm"):
            builder.add_step(step, ComponentStatus.DISABLED, 0.0, f"skipped: {CACHE_HIT_SKIP}")

        # No context was assembled because no model was called. The summary says
        # so explicitly instead of rendering as an empty panel.
        builder.context = ContextSummary(
            budget_tokens=self._settings.context_budget_tokens,
            excluded=[
                ExcludedContext(
                    name=name,
                    origin=origin,
                    reason=ExclusionReason.COMPONENT_DISABLED,
                    detail=CACHE_HIT_SKIP,
                )
                for name, origin in (("memory", "memory"), ("structured retrieval", "retrieval"))
            ],
        )

        record = builder.finish(response=response)
        self._telemetry.record(record)
        return ChatResponse(response=response, execution=record)


def _describe_cache(lookup: CacheLookup) -> str:
    report = lookup.report
    if report.error:
        return report.error
    if report.hit:
        return f"hit at similarity {report.similarity} (threshold {report.threshold})"
    if report.similarity is not None:
        return f"miss — best similarity {report.similarity} below threshold {report.threshold}"
    return f"miss — nothing above threshold {report.threshold}"
