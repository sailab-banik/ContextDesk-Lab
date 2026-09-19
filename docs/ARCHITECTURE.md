# ContextDesk Lab — Architecture

ContextDesk Lab is a support chat for a fictional SaaS platform. The chat is the
interface; the product is the **execution record** that accompanies every
response, and the frontend that makes it readable.

> **The invariant:** every AI request produces two things — a user-facing
> response and an execution record. No component is ever hidden behind the chat,
> and no component is ever reported as having worked when it did not.

```
Browser  ─ Next.js 16, :3000 ────────────────────────────────────────────────
  Console     chat + Context Inspector ─── POST /api/chat ──────────┐
  Compare     four configurations ──────── POST /api/chat/compare ──┤
  Analytics   metrics, history, replay ─── GET  /api/analytics/* ───┤
  Lab         one page per component ───── GET  /health + analytics ┤
  (header)    live component status ────── GET  /health ────────────┤
                                                                    ▼
Backend  ─ FastAPI, :8000 ───────────────────────────────────────────────────
  ChatService ──► cache · memory · retrieval · context builder · LLM
       │
       └──► ExecutionRecord ──► TelemetryService (history, aggregates)
```

Sections 1–10 describe the backend. Section 11 describes the frontend. For a
file-by-file reading of the code, see `CODEBASE_GUIDE.md` (backend) and
`FRONTEND_GUIDE.md` (frontend).

---

## 1. Request flow

```
POST /api/chat
      │
      ▼
ChatService.handle_message(request)          orchestration only
      │
      ├─ 1. cache lookup ───────────► SemanticCache ──► hit ──► return, stop here
      │                                                   │
      │                                                   ▼
      │                                      memory, retrieval, and the LLM
      │                                      are all skipped — that is the saving
      │
      ├─ 2. memory ─────────────────► MemoryService       (long-term memories)
      ├─ 3. structured retrieval ───► ContextRetrieval    (5 business sources)
      ├─ 4. context assembly ───────► ContextBuilder      (selects + explains)
      ├─ 5. llm ────────────────────► LLMService          (response + usage)
      ├─ 6. cache store ────────────► SemanticCache
      └─ 7. record turn ────────────► MemoryService       (session events)
                │
                ▼
      ExecutionRecord ──► TelemetryService ──► history, replay, analytics
                │
                ▼
      ChatResponse { response, execution }
```

Steps 2 and 3 are independent of each other but run in sequence. Each retrieval
source is one round trip, and the per-source durations are reported: the cost of
retrieval is meant to be visible, not smoothed away by concurrency.

### Cache-hit short circuit

A hit ends the request. Memory, retrieval, and the LLM are each marked
`DISABLED` with `skipped_reason = "response served from the semantic cache"`,
and the context summary carries the same explanation so the inspector shows a
reason rather than an empty panel. A hit that still did all the downstream work
would save nothing and prove nothing.

---

## 2. Service boundaries

| Layer | Package | Owns | Never does |
|---|---|---|---|
| Orchestration | `app/services/chat_service.py` | Reads the execution config, sequences the steps, assembles the record | Contains Redis or provider-specific code |
| Context assembly | `app/services/context_builder.py` | Decides what reaches the model and states why anything was left out | Fetches anything |
| Memory | `app/memory/` | `get_relevant_memory()`, `store_memory()` | Decides whether memory is enabled |
| Retrieval | `app/retrieval/` | Fetches customer, subscription, usage, tickets, incidents | Lets Redis keys or MCP envelopes leak upward |
| Cache | `app/cache/` | Lookup, similarity match, store; returns an explicit hit/miss | Hides a miss or a similarity score |
| LLM | `app/llm/` | Message + prepared context → response + usage | Retrieves context, touches memory, reads cache |
| Telemetry | `app/telemetry/`, `app/services/telemetry_service.py` | The record, the history store, the aggregates | Alters request behavior |

The components never call each other. Only `ChatService` knows the sequence, and
it learns each component's outcome from the report that component returns.

---

## 3. The four-state status

```python
class ComponentStatus(StrEnum):
    OK = "ok"                    # the real Redis Iris service ran
    STUB = "stub"                # an in-process fake stood in for it
    UNAVAILABLE = "unavailable"  # it was asked and it failed
    DISABLED = "disabled"        # it was not asked
```

A boolean would collapse "the user switched this off" into "this broke". Both
appear in the UI, and they mean opposite things. `skipped_reason` separates the
two flavours of `DISABLED` in words: switched off for this request, or made
unnecessary by an earlier step. Both carry a reason, so the frontend tells them
apart by reading `execution_config` (§11).

Failure is never softened. A failed LLM call returns a response that says the
model could not be reached and sets `record.error`; it is not cached and it is
not replaced with a canned answer that would read like a working system.
Partial retrieval failure marks the whole retrieval report `UNAVAILABLE` — a
half-retrieved context must not look healthy.

---

## 4. Stub mode

Each Iris component has a real client and an in-process fake behind the same
protocol, chosen once at startup in `app/api/dependencies.py`:

```python
def build_semantic_cache(settings):
    if settings.contextdesk_stub_mode or not settings.cache_configured:
        return StubSemanticCache(settings)
    return LangCacheService(settings)
```

A component is stubbed when its keys are absent, or when
`CONTEXTDESK_STUB_MODE=true` forces it. The whole app — chat, inspector,
analytics, experiment mode, and all 50 tests — runs with no Redis Cloud account,
no API key, and no network.

**A stub is not a silent success.** It reports `STUB`, `/health` reports `STUB`,
and the stubs decline to imitate what they cannot do:

- The **stub LLM** answers by printing the context it was handed and labelling
  itself. It does not invent plausible support answers.
- The **stub cache** scores prompts by word overlap, not embeddings, so it
  judges against its own `STUB_SIMILARITY_THRESHOLD` (0.6) rather than
  LangCache's 0.92. Reporting 0.92 against a lexical score would make every
  lookup miss and misrepresent what the component does.
- The **stub memory** serves the seeded memories and never promotes session
  events to long-term memory, because Agent Memory's promotion is a background
  process it cannot imitate.

Milestone 0 is complete when `/health` reports `ok` for all three Iris
components instead of `stub`.

---

## 5. Context assembly — the centre of the project

`ContextBuilder.build(memory, retrieval)` returns the prompt block **and** a
`ContextSummary` accounting for everything that did not make it in.

Candidates are assembled in a fixed priority order — identity first, then what
is already known about the customer, then live data in descending specificity:

```
customer → subscription → api_usage → support_tickets → regional_incidents → memory
```

Every omission carries a reason:

| `ExclusionReason` | Raised when |
|---|---|
| `NO_DATA` | The source was queried and returned nothing usable |
| `NOT_RELEVANT` | A row is history rather than context — a resolved ticket, a closed incident |
| `BELOW_RELEVANCE_THRESHOLD` | A scored memory did not clear `MEMORY_RELEVANCE_THRESHOLD` |
| `CONTEXT_BUDGET_EXCEEDED` | The section did not fit in `CONTEXT_BUDGET_TOKENS` |
| `COMPONENT_DISABLED` | The component was switched off for this request |
| `COMPONENT_UNAVAILABLE` | The component or one of its sources failed |

Exclusion is per row where that matters: a resolved ticket is excluded by id,
with `detail = "status=resolved"`, so the inspector can show precisely what was
dropped.

**Relevance scoring is honest about its two sources.** Agent Memory ranks
semantically but returns no score, so real memories arrive with
`relevance = None` and are trusted to the service that ranked them. The stub
scores by lexical overlap. The builder only applies the threshold to entries
that actually carry a score.

---

## 6. Telemetry

One `ExecutionRecord` per request, shaped to mirror the Context Inspector's
sections so the UI never has to reassemble it:

```
request_id · user_id · session_id · message · response
started_at · completed_at · total_duration_ms · execution_config

memory     { status, duration_ms, entries[], used_count, skipped_reason, error }
retrieval  { status, duration_ms, sources[], skipped_reason, error }
cache      { status, duration_ms, hit, similarity, matched_prompt, threshold, stored }
llm        { status, called, duration_ms, model, input_tokens, output_tokens,
             estimated_cost_usd, skipped_reason, error }
context    { sources[], size_chars, estimated_tokens, budget_tokens,
             included[], excluded[] }
steps      [ { name, status, duration_ms, detail } ]   ← the replay view
```

`ExecutionRecordBuilder` accumulates this as the request runs, which is what
keeps `chat_service.py` readable as a sequence of named steps. Reports default
to `DISABLED`, so a component that never ran is correctly described even if the
orchestrator never touches it.

Records live in a bounded in-process deque (`TELEMETRY_HISTORY_LIMIT`, default
200). This is a single-process learning tool; history does not survive a
restart, and nothing in telemetry is consulted while a request is being served.

**Timing.** `Stopwatch` reports elapsed time when read from inside its block as
well as after it, because error paths return early — a component that failed
after 300 ms still cost 300 ms, and the record says so.

**Cost is always an estimate.** `estimate_cost_usd()` multiplies token counts by
configured per-million rates. The saving from a cache hit cannot be measured at
all — there is no call to measure — so it is estimated by pricing the skipped
call at the average of the calls that did happen. `AnalyticsSummary` carries
`cost_is_estimated: true`.

**Aggregates make one careful distinction:** only requests that actually
consulted the cache count toward its hit rate. A request that ran with the cache
switched off is not a miss. Percentiles use nearest rank (`ceil(P/100 × N)`) —
with the handful of requests a demo produces, interpolating would invent
precision that is not there.

---

## 7. Experiment mode

`POST /api/chat/compare` runs one message across a ladder of configurations:

| Label | memory | retrieval | cache |
|---|---|---|---|
| `llm only` | ✗ | ✗ | ✗ |
| `llm + memory` | ✓ | ✗ | ✗ |
| `llm + retrieval` | ✗ | ✓ | ✗ |
| `llm + memory + retrieval + cache` | ✓ | ✓ | ✓ |

Each run is a full request producing its own execution record, so a comparison
is made of exactly the evidence the inspector shows. Turns are **not** written
back to memory during a comparison: four runs of one message would distort the
history the next real request reads.

The Compare page labels these runs "Model only", "Model + memory", "Model +
retrieval", and "Full system", and draws each numeric row (latency, context
size, estimated cost) as bars scaled within the row, without crowning a winner.

The full system is not assumed to win. A plan lookup does not need memory, and
more context means more tokens, more latency, and more cost — which is what the
comparison exists to show.

---

## 8. Redis Iris integration

| Component | Package | Module | Key calls |
|---|---|---|---|
| LangCache | `langcache` | `langcache` | `search_async(prompt=…)`, `set_async(prompt=…, response=…)` |
| Agent Memory | `redis-agent-memory` | `redis_agent_memory` | `search_long_term_memory_async(request={…})`, `add_session_event_async(…)`, `bulk_create_long_term_memories_async(…)` |
| Context Retriever | `redis-context-retriever` | `context_surfaces` | `query_tool(agent_key=…, tool_name=…, arguments={…})` |

Things that cost time to discover, encoded in the code:

1. The Context Retriever **package** is `redis-context-retriever`; the **module**
   is `context_surfaces`.
2. Every SDK call is async.
3. LangCache's similarity threshold is fixed when the service is created and is
   not a per-request argument. `LANGCACHE_SIMILARITY_THRESHOLD` records what you
   chose so the UI can display it — it does not change the service.
4. Agent Memory promotes session events to long-term memory asynchronously,
   minutes later. Nothing waits for it; `app/data/seed_memories.py` writes the
   demo's memories outright.
5. Context Retriever results arrive MCP-shaped and are unwrapped inside the
   retrieval layer, so nothing above it knows MCP exists:
   ```python
   json.loads(response["content"][0]["text"])["results"]
   ```
6. Context Retriever reads **RedisJSON documents**, so `seed_redis.py` writes
   with `JSON.SET`, not `HSET`. TAG fields must already be strings when written
   directly rather than through a `ContextModel`.

### Optional LLM parameters

`LLM_TEMPERATURE` is unset by default, and the parameter is then not sent at
all. Several current models — `gpt-5.6-luna` among them — support only their own
default temperature and reject the request with a 400 rather than clamping the
value, so a default that "looks safe" turns a working model into a failed
component. The knob still exists for models that accept it.

A rejected parameter is reported, not worked around: the provider does not retry
without it. Silently dropping a parameter the operator configured would hide the
misconfiguration and leave the model behaving differently from what the `.env`
says.

### Generated tool names

Context Retriever generates one MCP tool per entity and index type. The names
the retrieval client calls are constants at the top of
`app/retrieval/context_retriever_client.py`:

```python
TOOL_GET_CUSTOMER        = "get_customer_by_id"
TOOL_FILTER_SUBSCRIPTION = "filter_subscription_by_customer_id"
TOOL_FILTER_API_USAGE    = "filter_api_usage_by_customer_id"
TOOL_FILTER_TICKETS      = "filter_ticket_by_customer_id"
TOOL_FILTER_INCIDENTS    = "filter_incident_by_region"
```

These follow the entity names registered in the Redis Cloud console. **If an
entity is registered under a different name, correct these constants** — they
are the one place tool names appear, and `UnifiedClient.list_tools(agent_key)`
will show what was actually generated.

---

## 9. Configuration

Everything comes from the root `.env` through `app/config.py`. No model name,
endpoint, threshold, or price is hardcoded in application code, and execution
configuration (`memory_enabled`, `retrieval_enabled`, `cache_enabled`) is passed
explicitly on every request — there is no global switch that silently changes
behavior.

| Variable | Used by |
|---|---|
| `OPENAI_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_OUTPUT_TOKENS` | `app/llm/` |
| `LLM_INPUT_COST_PER_1M`, `LLM_OUTPUT_COST_PER_1M` | `app/telemetry/metrics.py` |
| `CONTEXTDESK_STUB_MODE` | Every component factory |
| `REDIS_URL` | `app/data/seed_redis.py` |
| `LANGCACHE_*`, `LANGCACHE_SIMILARITY_THRESHOLD` | `app/cache/` |
| `AGENT_MEMORY_*`, `MEMORY_RESULT_LIMIT`, `MEMORY_RELEVANCE_THRESHOLD` | `app/memory/` |
| `CONTEXT_RETRIEVER_AGENT_KEY`, `CONTEXT_RETRIEVER_*_URL` | `app/retrieval/` |
| `CONTEXT_BUDGET_TOKENS` | `app/services/context_builder.py` |
| `TELEMETRY_HISTORY_LIMIT` | `app/services/telemetry_service.py` |
| `STUB_SIMILARITY_THRESHOLD` | `app/cache/stub.py` |

The frontend has a single setting, `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`). Next.js reads it from `frontend/.env.local`, not from
the root `.env`.

---

## 10. HTTP API

| Method | Path | Returns | Called by |
|---|---|---|---|
| `GET` | `/health` | Per-component status: `ok` or `stub` | The header on every page; the Lab |
| `POST` | `/api/chat` | `{ response, execution }` | The console, once per message |
| `POST` | `/api/chat/compare` | One run per configuration, each with its own record | Compare |
| `GET` | `/api/analytics/summary` | Latency, cache, LLM, and context aggregates | Analytics; the Lab; the inspector's cache-saving estimate |
| `GET` | `/api/analytics/history?limit=` | Recent requests as history rows | Analytics; the Lab |
| `GET` | `/api/analytics/history/{request_id}` | The full record — the replay view | Replay; the Lab's most recent run |

Interactive docs at `http://localhost:8000/docs`. CORS admits only
`http://localhost:3000`, the frontend's dev origin.

---

## 11. Frontend

A Next.js 16 App Router app (React 19, TypeScript, Tailwind CSS v4, React
Compiler on) in `frontend/`. It owns no business logic: every number it shows
is a field the backend sent, and its job is to render the execution record next
to the response without hiding any component.

### Surfaces

| Route | Surface | What it answers |
|---|---|---|
| `/` | **Console**: the chat, and the Context Inspector for the selected answer | Where did this answer's context come from, what was left out, what did each step cost? |
| `/compare` | **Experiment mode**: one message across the four-configuration ladder | What does each component add, and what does it cost? |
| `/analytics` | **Analytics**: the four metric groups, latency per request, sources used, request history | How does the system behave across many requests? |
| `/analytics/[requestId]` | **Replay**: every step in order as a waterfall, the response, and the full inspector | What exactly happened in this one request? |
| `/lab/[component]` | **Technology Lab**: one page each for memory, retrieval, and cache | Why does this component exist, and what has it done here? |

### The inspector mirrors the record

The execution record's shape was designed to match the inspector, so the
frontend renders it top to bottom without reassembling anything:

```
Signal path        record.steps, matched to six fixed stations by step name
What reached …     record.context: included[] as solid segments, excluded[] as dashed ghosts
Semantic cache     record.cache: hit/miss, similarity against threshold, matched prompt
Memory             record.memory: each entry, its relevance, used or left out
Structured context record.retrieval: each tool call, its arguments, the rows returned
Model              record.llm: called or not, tokens, estimated cost
```

The stations are fixed rather than built from `record.steps`, so a request that
ended early (a cache hit) still shows every station, and what it skipped reads
as skipped rather than missing.

### Status on screen

The four-state status (§3) is drawn as a glyph whose **fill** carries the state
and whose **hue** carries the component: solid for `ok`, half-filled for `stub`,
hollow for `disabled`, red with a cross for `unavailable`, always with a word
label. Each component owns one color everywhere it appears.

`disabled` is split into **Off** and **Skipped** on screen. The backend sets
`skipped_reason` in both cases, so the frontend tells them apart by reading
`execution_config`: if the request turned the component off, it's Off;
otherwise an earlier step made it unnecessary, and it's Skipped.

### Data and state

- **Reads** go through one hook, `useBackendResource`, which refetches on a key
  change or an explicit reload and keeps the previous data during a refetch.
  Nothing is cached or prerendered, because telemetry is in-process and live.
- **The conversation** lives in a provider in the root layout, so it survives
  navigation. Each turn captures the configuration it was sent with. A reload
  clears the chat, but the records remain reachable from Analytics.
- **A failed call** is shown as a failure with the action that fixes it: "Can't
  reach the backend at … Start it with …", never an empty panel.

### Contracts with the backend

Things the frontend reads that the backend must keep stable:

| Contract | Where the frontend depends on it |
|---|---|
| Step names (`cache lookup`, `memory`, `structured retrieval`, `context assembly`, `llm`, `cache store`) | `signal-path.tsx`, `step-waterfall.tsx` |
| Context section names `memory: <id>` | Memory section: which memories were used |
| `ExecutionSummary.config_label` lists exactly the enabled components | History table: Off vs Skipped for history rows |
| `ExclusionReason` and `ComponentStatus` values | `frontend/types/api.ts`; exhaustively labeled |
| `/api/analytics/summary` saving fields | The inspector's per-hit saving estimate |

`frontend/types/api.ts` mirrors `backend/app/models`. A field added to the record
needs adding there before the UI can show it.

---

## 12. Demo scenarios, and where each one lives

| Scenario | Exercises | Verified by | Seen in the UI |
|---|---|---|---|
| **1.** "My API is slow again." | Memory + retrieval + composition | `test_stub_components_never_report_ok`, and the 4 sources + memory visible in the record | Console: memory `MEM-5001` used, the open ticket and active incident in the budget bar |
| **2.** "What plan am I currently on?" | Retrieval alone; disabling it visibly breaks the answer | `test_retrieval_off_removes_the_data_the_answer_needs` | Compare, or the Console with Retrieval off: zero tokens reach the model |
| **3.** "How do I reset my API key?" | Semantic cache against a differently worded cached prompt | `test_cache_hit_skips_every_downstream_step` | Console: the similarity meter against its threshold, the matched prompt, and memory, retrieval, and the model shown as skipped |

The synthetic dataset in `app/data/sample_data.py` is built for these: CUST-1001
(Aurora Labs, us-east, Pro) sits at 93% of its API limit with 812 ms average
latency, has one open latency ticket and one resolved one, an active us-east
incident and a resolved one, and three seeded long-term memories of which
exactly one is relevant to a latency complaint.

---

## 13. Testing

```bash
cd backend && uv run pytest        # 50 tests
```

Everything runs against the stubs: no network, no credentials, no Redis.

| File | Covers |
|---|---|
| `test_chat_flow.py` | Orchestration, the cache short circuit, disabled vs failed, LLM failure reporting, step ordering |
| `test_context_builder.py` | Every exclusion reason, priority order, budget enforcement, scored vs unscored memory |
| `test_metrics.py` | Hit-rate accounting, nearest-rank percentiles, cost estimation, empty-history behavior |
| `test_components.py` | MCP unwrapping, stub honesty, memory ownership scoping, seed key templates |
| `test_llm_provider.py` | Optional parameters omitted when unset, the output cap, context labeling, usage, rejected parameters reported rather than retried |
| `test_api.py` | Every endpoint, validation, history and replay, the comparison ladder |

The frontend has no test suite yet. Its checks are the linter, the type checker,
and a production build:

```bash
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```

---

## 14. Deliberately out of scope

No authentication, user management, payments, real ticketing, admin
permissions, or background job infrastructure. The caller states its own
`user_id`, and the console always sends as `CUST-1001`, the customer the demo
scenarios are written against. History is in-process and does not survive a
restart, and the chat is not persisted. There is one LLM provider, built well,
with a seam small enough that a second could be added.

A good addition makes it easier to answer: *where did this response get its
context, what did each step cost, and what tradeoff does this component
introduce?*
