# ContextDesk Lab

An interactive context engineering playground built to explore **Redis Iris**. It looks like an
AI support chat for a fictional SaaS platform, but the chat is only the interface — the product is
what it makes visible about memory, retrieval, caching, latency, and cost.

**The invariant:** every AI request produces two things — a user-facing response **and** an
execution record. Infrastructure stays visible; never hide a component behind the chat.

`PLAN.md` holds the product spec, the demo scenarios, and the build sequence. This file is how to
work in the repo.

---

## Commands

| Task | Command |
|---|---|
| Run backend (`:8000`) | `cd backend && uv run fastapi dev app/main.py` |
| Run frontend (`:3000`) | `cd frontend && npm run dev` |
| Add / remove Python dep | `uv add <pkg>` · `uv remove <pkg>` |
| Install Python deps | `uv sync` |
| Run backend tests | `cd backend && uv run pytest` |
| Lint frontend | `cd frontend && npm run lint` |
| Load synthetic data into Redis | `cd backend && uv run python -m app.data.seed_redis` |

Python is managed entirely by `uv` and `pyproject.toml`. Never use `pip`, `virtualenv`, or a
`requirements.txt`.

---

## Stack

**Frontend** — Next.js 16.3.5 (App Router), React 19.2.8, TypeScript, Tailwind CSS v4.

- The **React Compiler is enabled** (`next.config.ts`). Do not hand-add `useMemo` / `useCallback`
  for memoization the compiler already does.
- Tailwind v4 is **CSS-first**: there is no `tailwind.config.js`. Theme tokens go in
  `frontend/app/globals.css` inside the `@theme` block.
- **Typed routes are on.** Layouts and pages use generated types, e.g. `LayoutProps<"/">`.
- Next 16 differs from model training data. Authoritative docs ship in the package itself:
  `frontend/node_modules/next/dist/docs/` (App Router lives in `01-app/`). Check there before
  writing routing, caching, or data-fetching code.
- `next dev` regenerates `frontend/AGENTS.md` and `frontend/CLAUDE.md` on every run. They are Next's
  own two-line pointer to those docs — commit them rather than fighting them.

**Backend** — Python 3.12, FastAPI, `uv`.

---

## Repo map

```
backend/
  app/
    main.py          FastAPI entry point, CORS, router wiring
    api/             HTTP routes (chat, analytics)
    services/        chat_service, context_builder, telemetry_service
    memory/          Agent Memory client + stub
    retrieval/       Context Retriever client + stub
    cache/           LangCache client + stub
    llm/             LLM provider abstraction
    telemetry/       execution record + metrics
    models/          request / response models
    data/            synthetic data + seed_redis.py
  tests/
frontend/
  app/               page.tsx, analytics/, explorer/, layout.tsx
  components/        chat/ context/ analytics/ explorer/
  lib/api.ts         backend client
  types/  hooks/
```

---

## Architecture

```
Frontend → FastAPI → Chat Service (orchestrator)
                          ├── Memory
                          ├── Context Retrieval
                          └── Cache
                          ↓
                     Context Builder → LLM → Response + Telemetry → Frontend
```

The Chat Service coordinates; the components do not call each other.

---

## Service boundaries

| Service | Owns | Must not |
|---|---|---|
| **Chat Service** | Orchestration: read the execution config, gather context, check cache, build context, call the LLM, return response + execution record | Contain Redis or provider-specific code |
| **Memory Service** | `get_relevant_memory()`, `store_memory()` over Agent Memory | Decide whether memory is enabled |
| **Context Retrieval** | Fetching structured business data (customer, subscription, usage, tickets, incidents) | Leak Redis keys or MCP tool envelopes upward |
| **Semantic Cache** | Lookup, similarity match, store. Returns an explicit hit/miss decision | Silently swallow a miss, or hide the similarity score |
| **LLM Service** | User message + prepared context → response + usage metadata | Retrieve context, touch memory, or read cache |
| **Telemetry** | The execution record and aggregate metrics | Alter request behavior |

---

## Redis Iris

Iris is **Redis Cloud only** and fully managed. Services are created by hand in the console and
each key is shown **once**. See PLAN.md Milestone 0 for the provisioning walkthrough.

| Service | Install | Import |
|---|---|---|
| LangCache | `uv add langcache` | `from langcache import LangCache` |
| Agent Memory | `uv add redis-agent-memory` | `from redis_agent_memory import AgentMemory, models` |
| Context Retriever | `uv add redis-context-retriever` | `from context_surfaces import UnifiedClient` |

```python
cache  = LangCache(server_url=..., cache_id=..., api_key=...)
memory = AgentMemory(endpoint, store_id=..., api_key=...)
tools  = UnifiedClient()

await cache.search_async(prompt=...)              # {} on miss
await cache.set_async(prompt=..., response=...)
await memory.add_session_event_async(session_id=..., actor_id=..., role=..., content=[...])
await memory.search_long_term_memory_async(request={"text": ..., "filter": {...}})
await tools.query_tool(agent_key=..., tool_name=..., arguments={...})
```

**Five things that will otherwise cost you an afternoon:**

1. The Context Retriever package is `redis-context-retriever` but the module is `context_surfaces`.
2. Every SDK call is **async** (`*_async`; `query_tool` is already a coroutine).
3. LangCache's **similarity threshold is fixed when the service is created** (0.5–1.0, default
   0.92) — it is not a per-request argument. Experiment Mode can show the score, but cannot tune
   the threshold without recreating the service.
4. Agent Memory promotes session → long-term memory **asynchronously, minutes later**. Demos must
   not depend on it. Seed long-term memories directly with
   `bulk_create_long_term_memories_async`.
5. Context Retriever reads data **already in Redis** under key templates (`customer:{id}`), and
   generates MCP tools named `get_<entity>_by_id`, `filter_<entity>_by_<field>`,
   `search_<entity>_by_text`, `find_<entity>_by_<field>_range`. Results arrive MCP-shaped and must
   be unwrapped before leaving the retrieval layer:

   ```python
   json.loads(response["content"][0]["text"])["results"]
   ```

### Stub mode

Each Iris component has a real client and an in-process fake behind the same small interface,
chosen by env at startup. This keeps the app runnable end-to-end before any Redis Cloud account
exists.

A stub is **not** a silent success. Telemetry reports component status as one of `OK`, `STUB`, or
`UNAVAILABLE`, and the Context Inspector shows which. A failed component surfaces in the UI as
failed — for a learning project, visible failure is a feature.

---

## Configuration

Everything is read from the root `.env` (see `.env.example`). No model names or endpoints
hardcoded in application code.

| Variable | Used by |
|---|---|
| `OPENAI_API_KEY`, `LLM_MODEL` | `app/llm/` |
| `CONTEXTDESK_STUB_MODE` | Forces fakes even when keys are present |
| `REDIS_URL` | `app/data/seed_redis.py` |
| `LANGCACHE_ENDPOINT`, `LANGCACHE_ID`, `LANGCACHE_KEY` | `app/cache/` |
| `AGENT_MEMORY_ENDPOINT`, `AGENT_MEMORY_STORE_ID`, `AGENT_MEMORY_KEY` | `app/memory/` |
| `CONTEXT_RETRIEVER_AGENT_KEY` | `app/retrieval/` |

Execution configuration (`memory_enabled`, `retrieval_enabled`, `cache_enabled`) is passed
explicitly on every request. No hidden global behavior.

---

## Conventions

1. **Simplest thing that works.** `memory_service.get_relevant_memory(user_id)` — not a
   Manager → Factory → Adapter → Provider chain.
2. **No premature generalization.** No plugin systems, event buses, abstract repositories, or DI
   containers. Build one LLM provider well; keep the seam small enough that another could be added.
3. **One responsibility per module and per function.** Split the long orchestration path into named
   steps; do not split trivial ones.
4. **Explicit data models.** Defined request/response types, not dictionaries passed through layers.
5. **Handle failures at boundaries** — Redis down, LLM error, bad request. Skip defensive checks for
   impossible states, and never write a fallback that pretends a component worked.
6. **Extract components with a real responsibility.** Not wrappers around trivial markup.
7. **Descriptive names.** `retrieve_customer_context`, `check_semantic_cache`,
   `record_request_metrics` — not `process`, `handle`, `data`, `utils`, `manager`.
8. **Build vertically.** Finish one working end-to-end slice before starting the next (PLAN.md).

Comment the *why*, never the *what*:

```python
# Bad
# Get the user memory
memory = get_memory(user_id)

# Good
# Only relevant memory is included to avoid inflating the prompt context.
memory = get_relevant_memory(user_id)
```

---

## Scope

Deliberately **not** in this project: authentication, user management, payments, a real ticketing
system, admin permissions, background job infrastructure. The domain is a small set of synthetic
records that exists only to make context retrieval demonstrable.

A good addition makes it easier to answer: *where did this response get its context, what did each
step cost, and what tradeoff does this component introduce?*
