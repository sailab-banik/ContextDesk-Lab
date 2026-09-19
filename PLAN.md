# ContextDesk Lab — Product Plan

## Goal

Build an application that demonstrates what changes when an AI app has **memory**, **structured
context retrieval**, and **semantic caching** — and makes the difference measurable.

> **The question the project answers:** what does each context component actually contribute to an
> AI response, and what does it cost in latency and tokens?

The chat is a fictional SaaS support assistant. The real product is everything shown alongside the
answer. Architecture, service boundaries, and Redis Iris API details live in `CLAUDE.md`.

---

## Milestone 0 — Provision Redis Iris

Iris is fully managed on **Redis Cloud** and cannot run locally. Until this is done, the app runs in
**stub mode** (in-process fakes; see CLAUDE.md). Everything through M1 can be built without it.

**Each service key is displayed exactly once. Copy it immediately.**

### 1. Create the database

Redis Cloud console → **New Database** → *Try 30 MB for free*. Name it `contextdesk`.
Its connection string becomes `REDIS_URL`.

### 2. Create the three services

| Console page | Settings that matter | Copy into `.env` |
|---|---|---|
| **LangCache** | Select the `contextdesk` DB. Embedding provider: OpenAI (reuse `OPENAI_API_KEY`). **Similarity threshold: 0.92** — record whatever you pick, the UI must display it. TTL optional. | `LANGCACHE_ENDPOINT`, `LANGCACHE_ID`, `LANGCACHE_KEY` |
| **Agent Memory** | Select the `contextdesk` DB. Short-term TTL 1h, long-term TTL 365d (defaults are fine). | `AGENT_MEMORY_ENDPOINT`, `AGENT_MEMORY_STORE_ID`, `AGENT_MEMORY_KEY` |
| **Context Retriever** | Requires data in Redis **first** — run the seed script before this step. Define the five entities below, then **Auto-detect fields**, then mark index types. | Agent key tab → **New Agent Key** → `CONTEXT_RETRIEVER_AGENT_KEY` |

Endpoints and IDs are on each service's **Configuration → Connectivity** page.

### 3. Entities for Context Retriever

Run `uv run python -m app.data.seed_redis` first, then register:

| Entity | Key template | Fields to index |
|---|---|---|
| Customer | `customer:{id}` | `region` TAG, `name` TEXT |
| Subscription | `subscription:{id}` | `customer_id` TAG, `plan` TAG, `api_limit` NUMERIC |
| ApiUsage | `api_usage:{id}` | `customer_id` TAG, `requests_today` NUMERIC, `average_latency` NUMERIC |
| Ticket | `ticket:{id}` | `customer_id` TAG, `status` TAG, `issue_type` TEXT |
| Incident | `incident:{id}` | `region` TAG, `status` TAG, `description` TEXT |

The entity name is what the generated tool is named after, not the Python class: the ticket entity
is registered as `Ticket` (not `SupportTicket`) so the generated tool matches
`TOOL_FILTER_TICKETS` in `app/retrieval/context_retriever_client.py`. Whatever the console actually
generates wins — `await UnifiedClient().list_tools(agent_key)` shows it, and the five `TOOL_*`
constants are the one place to correct.

A field belongs to exactly one index — marking it both TAG and TEXT errors. The index type decides
which tool is generated (`TAG` → `filter_…`, `TEXT` → `search_…_by_text`, `NUMERIC` → `find_…_range`).

**Done when:** `/health` reports all three components `OK` rather than `STUB`.

---

## Demo scenarios

These are the acceptance tests. Each must be reproducible in the UI.

### 1. Persistent context — "My API is slow again."

The word *again* is the whole point: it cannot be answered without history.

- **Exercises:** Agent Memory + Context Retrieval + composition
- **Retrieves:** prior latency complaint (memory) · subscription + current usage · open tickets ·
  active incidents in the customer's region
- **Expected:** references the earlier report, states usage against plan limits, surfaces the active
  regional incident
- **Inspector must show:** four sources contributing, memory `OK`, cache `MISS`, LLM `CALLED`
- **Note:** seed the prior-issue memory via `bulk_create_long_term_memories_async`. Automatic
  promotion takes minutes and will not fire during a demo.

### 2. Structured retrieval — "What plan am I currently on?"

- **Exercises:** Context Retrieval alone
- **Retrieves:** Customer → Subscription (`get_customer_by_id`, `filter_subscription_by_customer_id`)
- **Expected:** the plan name, from data — not from conversation history
- **Contrast:** with retrieval disabled, the model cannot answer. That gap is the demonstration.

### 3. Semantic cache — "How do I reset my API key?"

Against a cached *"How do I generate a new API key?"* — different words, same meaning.

- **Exercises:** LangCache
- **Expected:** hit above the configured threshold; cached response returned
- **Inspector must show:** similarity score, the matched prompt, LLM `NOT CALLED`, and the latency
  and token cost avoided

---

## Surfaces

### Chat
The interaction surface. Deliberately plain — the value sits beside it.

### Context Inspector
Updates after every request.

| Section | Shows |
|---|---|
| Memory | Used / not used / stub · the entries retrieved |
| Structured context | Which sources were queried · what came back |
| Cache | Hit or miss · similarity score · matched prompt |
| LLM | Called or not · token usage |
| Context summary | What actually reached the model — **and what was available but excluded** |

That last row is the core idea: the system selects context rather than sending everything.

### Analytics

| Group | Metrics |
|---|---|
| Latency | Average · P50 · P95 · average LLM duration · average cache-hit duration |
| Cache | Hit rate · total hits / misses · average lookup time · LLM calls avoided |
| LLM | Total requests · total LLM calls · input / output tokens · estimated cost · estimated saved |
| Context | Memory / retrieval / cache usage counts · average context size · sources used |

Cost is an **estimate** derived from token counts and must be labeled as such.

**Request history** — recent executions with time, message, components used, cache decision, and
latency. Selecting one opens its **replay**: each step in order with its duration, the context it
contributed, and the final result.

### Technology Lab
Explains each component from inside the app: why it exists, what it stores, how it is retrieved, and
how it changed the response. One page per component, driven by real request data, not screenshots.

---

## Experiment mode

Every request carries an explicit configuration:

```
memory_enabled · retrieval_enabled · cache_enabled
```

Toggling these is how the tradeoffs become visible. The same message can be run across:

1. Plain LLM 2. + Memory 3. + Retrieval 4. Full system

compared on: LLM called · memory used · structured context · cache used · total latency · context
size · estimated cost.

**Do not assume the full system wins.** More context means more tokens and more latency. A plan
lookup does not need memory. The comparison is honest or it is worthless.

| Component | Improves | Costs |
|---|---|---|
| Agent Memory | Historical awareness, personalization, continuity | Retrieval latency; relevance is hard — stale memory actively misleads |
| Context Retrieval | Accuracy, access to live application data | Extra round trips; more tokens; schema upkeep |
| Semantic Cache | Latency and token cost on repeats | Threshold tuning; a near-miss returns a subtly wrong answer; invalidation |

---

## Domain model

Synthetic and deliberately small — it exists only to make retrieval demonstrable.

| Entity | Fields |
|---|---|
| Customer | `id`, `name`, `region`, `plan_id` |
| Subscription | `id`, `customer_id`, `plan`, `api_limit` |
| ApiUsage | `customer_id`, `requests_today`, `average_latency`, `error_rate` |
| SupportTicket | `id`, `customer_id`, `issue_type`, `status`, `created_at` |
| Incident | `id`, `service`, `region`, `status`, `description` |

Defined in `app/data/sample_data.py` and written to Redis by `app/data/seed_redis.py` under the key
templates in Milestone 0. Context Retriever reads from Redis, so the seed step is mandatory.

---

## Telemetry

Every request produces one execution record:

```
request_id · user_id · message
started_at · completed_at · total_duration

memory_status   (ok|stub|unavailable|disabled) · memory_duration
context_status  (ok|stub|unavailable|disabled) · context_duration
cache_status    (ok|stub|unavailable|disabled) · cache_duration
cache_hit · cache_similarity · cache_matched_prompt

llm_called · llm_duration · input_tokens · output_tokens

context_sources · context_size · execution_config
```

Status is a four-state enum, not a boolean — "disabled by the user" and "failed" must never look
alike. One record feeds the inspector, history, replay, analytics, and comparisons.

---

## Build sequence

Vertical slices. Finish one before starting the next.

| # | Slice | Done when |
|---|---|---|
| **M1** | Skeleton: chat UI → FastAPI → LLM → response + execution record → inspector. Stubs for all three Iris components. | A message round-trips and the inspector shows real timings with all components `STUB` |
| **M2** | Context Retrieval: sample data, `seed_redis.py`, retriever client, MCP unwrapping | Scenario 2 answers from data; disabling retrieval visibly breaks it |
| **M3** | Agent Memory: session events, seeded long-term memories, relevance filtering | Scenario 1 references the earlier issue |
| **M4** | LangCache: lookup before LLM, store after, similarity in telemetry | Scenario 3 returns a hit with no LLM call |
| **M5** | Experiment mode: per-request toggles wired end to end | The same message produces different, explainable execution records |
| **M6** | Analytics, request history, replay | Metrics aggregate across requests; any past request replays step by step |
| **M7** | Technology Lab | Each component explained from real request data |

M1 is the priority: an honest end-to-end path with visible telemetry is worth more than three
half-built integrations.

---

## MVP bar

Complete when a developer opening the app can answer all of these from the UI alone:

- Where did this response get its context?
- What was retrieved, and what was available but deliberately left out?
- Was memory used? Was the cache hit, and at what similarity?
- Was the LLM called — and if not, what did skipping it save?
- How long did each step take?
- What breaks when I turn this component off?
- What does this component cost me?

The weakest outcome is proving Redis Iris works. The strongest is making it obvious *why each
component exists and what it changes*.
