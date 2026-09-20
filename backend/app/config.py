"""Application configuration, read once from the root `.env`.

No model name, endpoint, or threshold is hardcoded in application code: every
value a deployment might change lives here and arrives from the environment.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The .env lives at the repository root so the backend and the seed scripts
# read the same file regardless of which directory they are launched from.
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")

    # --- LLM ---
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    # Unset means "do not send the parameter at all" and let the model use its
    # own default. Several current models accept only their default temperature
    # and reject the request outright rather than clamping it, so sending a
    # value nobody asked for turns a working model into a 400.
    llm_temperature: float | None = None
    llm_max_output_tokens: int = 600

    # Cost is an estimate derived from token counts; these rates are published
    # per 1M tokens by the provider and change often, so they are configuration.
    llm_input_cost_per_1m: float = 0.15
    llm_output_cost_per_1m: float = 0.60

    # --- Iris: forced fakes ---
    contextdesk_stub_mode: bool = False

    # --- Redis (seed script only; the Iris services reach Redis themselves) ---
    redis_url: str = ""

    # --- LangCache ---
    langcache_endpoint: str = ""
    langcache_id: str = ""
    langcache_key: str = ""
    # The bar a lookup must clear to count as a hit. Applied in
    # `app/cache/langcache_client.py` rather than by the service, so it can be
    # tuned here instead of by recreating the LangCache service. It can only be
    # lowered as far as the service's own threshold allows — see the search
    # floor below.
    langcache_similarity_threshold: float = 0.92

    # How wide a lookup searches. Kept below the decision threshold so a miss
    # still reports the score that produced it; the gap between the two is the
    # band of near-misses the Context Inspector can show. Raising this to match
    # the threshold makes every miss scoreless again.
    langcache_search_floor: float = 0.5

    # The stubs score prompts by word overlap, which runs lower than embedding
    # similarity for the same pair, so they judge against their own bar.
    stub_similarity_threshold: float = 0.6

    # --- Agent Memory ---
    agent_memory_endpoint: str = ""
    agent_memory_store_id: str = ""
    agent_memory_key: str = ""
    memory_relevance_threshold: float = 0.6
    memory_result_limit: int = 5

    # --- Context Retriever ---
    context_retriever_agent_key: str = ""
    context_retriever_api_url: str = ""
    context_retriever_mcp_url: str = ""

    # --- Context assembly ---
    # A budget is what makes selection visible: past it, context is excluded and
    # the inspector reports why.
    context_budget_tokens: int = 1200

    # --- Telemetry ---
    telemetry_history_limit: int = 200

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def cache_configured(self) -> bool:
        return bool(self.langcache_endpoint and self.langcache_id and self.langcache_key)

    @property
    def memory_configured(self) -> bool:
        return bool(
            self.agent_memory_endpoint
            and self.agent_memory_store_id
            and self.agent_memory_key
        )

    @property
    def retrieval_configured(self) -> bool:
        return bool(self.context_retriever_agent_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
