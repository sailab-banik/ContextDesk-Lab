"""In-process LLM fake."""

from app.config import Settings
from app.models.execution import ComponentStatus
from app.models.results import LLMResult
from app.telemetry.text import estimate_tokens
from app.telemetry.timing import Stopwatch


class StubLLM:
    """Answers by reporting the context it was handed.

    This is not a model and does not imitate one. It exists so the execution
    path — context assembly, telemetry, caching, the inspector — is exercisable
    without an API key, and so a missing key produces a visibly stubbed answer
    rather than a plausible invented one.
    """

    def __init__(self, settings: Settings) -> None:
        self.model = f"{settings.llm_model} (stub)"

    async def generate(self, message: str, context: str) -> LLMResult:
        with Stopwatch() as timer:
            lines = [
                "[stub LLM] No language model was called for this response.",
                "",
                f'You asked: "{message}"',
            ]
            if context:
                lines += [
                    "",
                    "The following context was assembled and would have been sent to the model:",
                    "",
                    context,
                ]
            else:
                lines += ["", "No context was assembled for this request."]
            text = "\n".join(lines)

        return LLMResult(
            text=text,
            model=self.model,
            status=ComponentStatus.STUB,
            duration_ms=timer.elapsed_ms,
            # Counted the same way context size is, so the stub still produces
            # comparable numbers in analytics.
            input_tokens=estimate_tokens(message) + estimate_tokens(context),
            output_tokens=estimate_tokens(text),
        )
