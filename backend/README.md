# ContextDesk Lab — backend

FastAPI service behind the context engineering playground. Every AI request
produces two things: a user-facing response and an execution record describing
how that response was produced.

```bash
uv sync                                   # install
uv run fastapi dev app/main.py            # run on :8000
uv run pytest                             # 43 tests, no network required
uv run python -m app.data.seed_redis      # load synthetic data into Redis
uv run python -m app.data.seed_memories   # seed the demo's long-term memories
```

Without Redis Iris credentials the three Iris components run as in-process
stubs and report their status as `STUB` — never as `OK`.

- `../architecture.md` — how the backend is put together and why
- `../PLAN.md` — the product spec, demo scenarios, and build sequence
- `../CLAUDE.md` — conventions and Redis Iris API details
