"""OpenAI-backed LLM provider."""

from openai import AsyncOpenAI

from app.config import Settings
from app.models.execution import ComponentStatus
from app.models.results import LLMResult
from app.telemetry.timing import Stopwatch

SYSTEM_PROMPT = """You are the support assistant for ContextDesk, a SaaS API platform.

You are given a CONTEXT block assembled for this specific request. It may contain
customer records, subscription and usage data, support tickets, active incidents,
and memories of earlier conversations.

Rules:
- Answer only from the CONTEXT block and the user's message. Do not invent
  account details, numbers, ticket IDs, or incidents.
- If the CONTEXT block does not contain what you need, say plainly that you do
  not have that information. Never guess a plan name or a usage figure.
- Cite concrete values when they are present: plan names, limits, request
  counts, latencies, ticket and incident IDs.
- Be concise. Two or three short paragraphs at most."""


class OpenAIProvider:
    """Chat completions via OpenAI.

    Temperature and the output cap come from configuration: some models accept
    only the default temperature, so `LLM_TEMPERATURE` is the knob to change
    rather than this code.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._temperature = settings.llm_temperature
        self._max_output_tokens = settings.llm_max_output_tokens
        self.model = settings.llm_model

    async def generate(self, message: str, context: str) -> LLMResult:
        user_content = f"CONTEXT:\n{context}\n\nUSER MESSAGE:\n{message}" if context else message

        # Sent only when configured: a model that supports one temperature
        # rejects the request rather than ignoring the parameter.
        optional_params = {} if self._temperature is None else {"temperature": self._temperature}

        with Stopwatch() as timer:
            try:
                completion = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    max_completion_tokens=self._max_output_tokens,
                    **optional_params,
                )
            except Exception as exc:
                return LLMResult(
                    text="",
                    model=self.model,
                    status=ComponentStatus.UNAVAILABLE,
                    duration_ms=timer.elapsed_ms,
                    error=str(exc),
                )

        usage = completion.usage
        return LLMResult(
            text=completion.choices[0].message.content or "",
            model=self.model,
            status=ComponentStatus.OK,
            duration_ms=timer.elapsed_ms,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
