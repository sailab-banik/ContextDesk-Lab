# ContextDesk Lab

An interactive context engineering playground for exploring
[Redis Iris](https://redis.io/). It looks like an AI support chat for a
fictional SaaS platform, but the chat is only the interface. The product is what
it makes visible: where each answer got its context, what was left out, whether
the cache answered instead of the model, and what every step cost.

> Every AI request produces two things: a user-facing response **and** an
> execution record. No component is ever hidden behind the chat, and none is
> ever reported as having worked when it didn't.

## What's in the app

| Page | What it shows |
|---|---|
| **Console** | The support chat, and beside it the Context Inspector for the selected answer: the path through cache, memory, retrieval, and the model; what reached the model against its token budget; what was left out and why |
| **Compare** | One message run four ways (model only, plus memory, plus retrieval, full system), compared on latency, context size, and estimated cost |
| **Analytics** | Latency, cache, model, and context metrics, latency per request, and the request history. Any request replays step by step |
| **Lab** | One page each for Agent Memory, Context Retriever, and LangCache: why it exists, what it stores, how it's queried, its tradeoffs, and what it has done in your requests |

## Quick start

Requires Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node.js 20.9 or
later.

```bash
cp .env.example .env          # optional; see Stub mode below
```

```bash
# Terminal 1 — backend on :8000
cd backend
uv sync
uv run fastapi dev app/main.py
```

```bash
# Terminal 2 — frontend on :3000
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### Stub mode

No credentials are needed to run it. Any component whose keys are blank or
missing runs as an in-process stub: the LLM, LangCache, Agent Memory, and
Context Retriever each have one. Skipping `.env` entirely stubs everything. If
you copy `.env.example`, replace or blank its placeholder `OPENAI_API_KEY`;
otherwise the backend tries the real provider and reports the model as
unavailable. A stub is never reported as working. The header shows each
component as **OK** or **Stub**, and so does every execution record. The stub
LLM doesn't pretend to be a model: it answers by printing the context it was
handed.

- Add `OPENAI_API_KEY` and `LLM_MODEL` for real answers.
- Provision the three Iris services on Redis Cloud for the rest.
  [PLAN.md, Milestone 0](PLAN.md#milestone-0--provision-redis-iris) walks
  through it. Then load the synthetic data:

  ```bash
  cd backend
  uv run python -m app.data.seed_redis       # records Context Retriever reads
  uv run python -m app.data.seed_memories    # the demo's long-term memories
  ```

## Try the three scenarios

| Ask | What it demonstrates |
|---|---|
| "My API is slow again." | Memory: "again" only makes sense with the earlier latency report, which the inspector shows being used |
| "What plan am I currently on?" | Retrieval: turn Retrieval off in the message box, or open Compare, and the model has nothing to answer from |
| "How do I reset my API key?" | The semantic cache: ask it, then ask again in other words, and watch the similarity against the threshold and the model call it skipped |

Repeating a message hits the cache. Turn the Cache toggle off when you want to
watch another component work.

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the system is put together and why: request flow, the four-state status, context assembly, telemetry, the frontend |
| [docs/CODEBASE_GUIDE.md](docs/CODEBASE_GUIDE.md) | A guided reading of the backend code, with recipes and gotchas |
| [docs/FRONTEND_GUIDE.md](docs/FRONTEND_GUIDE.md) | A guided reading of the frontend code, with recipes and gotchas |
| [PLAN.md](PLAN.md) | The product spec, demo scenarios, and build sequence |
| [CLAUDE.md](CLAUDE.md) | Working conventions and Redis Iris API notes |

## Repository layout

```
backend/     FastAPI service: orchestration, the Iris clients and their stubs, telemetry
frontend/    Next.js app: console, compare, analytics, replay, lab
docs/        architecture and codebase guides
PLAN.md      product spec and build sequence
```

## Checks

```bash
(cd backend && uv run pytest)                                      # 50 tests, no network
(cd frontend && npm run lint && npx tsc --noEmit && npm run build)
```

## License

[MIT](LICENSE)
