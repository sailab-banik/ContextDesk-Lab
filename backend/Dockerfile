FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv

# Bytecode is compiled once at build time instead of on first import in the
# container. The image's own Python is used; uv must not download another.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies are installed before the source is copied, so editing app code
# does not invalidate the (slow) dependency layer.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

COPY app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# One worker on purpose: the execution-record history lives in process memory,
# and several workers would each keep their own partial history.
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
