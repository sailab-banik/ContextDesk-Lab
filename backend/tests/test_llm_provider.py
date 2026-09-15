"""The OpenAI provider's request shape.

Optional parameters are the fragile part: a model that supports only its own
default temperature rejects the whole request rather than ignoring the value,
so what is *not* sent matters as much as what is.
"""

from types import SimpleNamespace

from app.config import Settings
from app.llm.openai_provider import SYSTEM_PROMPT, OpenAIProvider
from app.models.execution import ComponentStatus


class RecordingCompletions:
    """Stands in for `client.chat.completions`, capturing the kwargs sent."""

    def __init__(self) -> None:
        self.kwargs: dict = {}

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return Completion()


def Completion() -> SimpleNamespace:
    """The shape of the completion the provider reads: choices and usage."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="an answer"))],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=34),
    )


def make_provider(settings: Settings) -> OpenAIProvider:
    # The SDK refuses to construct a client without a key; no request reaches it
    # in these tests, so a placeholder is enough.
    return OpenAIProvider(settings.model_copy(update={"openai_api_key": "test-key"}))


def provider_with_recorder(settings: Settings) -> tuple[OpenAIProvider, RecordingCompletions]:
    provider = make_provider(settings)
    recorder = RecordingCompletions()
    provider._client.chat.completions = recorder  # noqa: SLF001
    return provider, recorder


async def test_temperature_is_omitted_when_it_is_not_configured(settings: Settings):
    provider, recorder = provider_with_recorder(
        settings.model_copy(update={"llm_temperature": None})
    )

    await provider.generate("hello", "")

    assert "temperature" not in recorder.kwargs


async def test_temperature_is_sent_when_it_is_configured(settings: Settings):
    provider, recorder = provider_with_recorder(
        settings.model_copy(update={"llm_temperature": 0.2})
    )

    await provider.generate("hello", "")

    assert recorder.kwargs["temperature"] == 0.2


async def test_the_output_cap_uses_max_completion_tokens(settings: Settings):
    provider, recorder = provider_with_recorder(
        settings.model_copy(update={"llm_max_output_tokens": 256})
    )

    await provider.generate("hello", "")

    assert recorder.kwargs["max_completion_tokens"] == 256
    assert "max_tokens" not in recorder.kwargs


async def test_context_is_labeled_for_the_model(settings: Settings):
    provider, recorder = provider_with_recorder(settings)

    await provider.generate("What plan am I on?", "## subscription\n- plan=Pro")

    system, user = recorder.kwargs["messages"]
    assert system["content"] == SYSTEM_PROMPT
    assert "CONTEXT:" in user["content"]
    assert "USER MESSAGE:" in user["content"]


async def test_a_message_without_context_is_sent_on_its_own(settings: Settings):
    provider, recorder = provider_with_recorder(settings)

    await provider.generate("hello", "")

    assert recorder.kwargs["messages"][1]["content"] == "hello"


async def test_usage_is_carried_onto_the_result(settings: Settings):
    provider, _ = provider_with_recorder(settings)

    result = await provider.generate("hello", "")

    assert result.status is ComponentStatus.OK
    assert (result.input_tokens, result.output_tokens) == (120, 34)


class RejectingCompletions:
    async def create(self, **kwargs):
        raise RuntimeError("Unsupported value: 'temperature' does not support 0.2")


async def test_a_rejected_parameter_is_reported_not_retried(settings: Settings):
    """A bad parameter is a configuration error. It surfaces as a failed
    component with the provider's own message, rather than being silently
    retried without the parameter — which would hide the misconfiguration."""
    provider = make_provider(settings.model_copy(update={"llm_temperature": 0.2}))
    provider._client.chat.completions = RejectingCompletions()  # noqa: SLF001

    result = await provider.generate("hello", "")

    assert result.status is ComponentStatus.UNAVAILABLE
    assert "temperature" in (result.error or "")
    assert result.text == ""
