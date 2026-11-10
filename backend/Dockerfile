FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY netvault ./netvault
COPY alembic ./alembic
COPY alembic.ini ./

RUN uv sync --frozen --no-dev

RUN groupadd --system netvault \
    && useradd --system --gid netvault --home-dir /app netvault \
    && chown -R netvault:netvault /app

USER netvault

ENV NETVAULT_STATIC_DIR=/srv/frontend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status == 200 else 1)"

CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev uvicorn netvault.main:app --host 0.0.0.0 --port 8000"]
