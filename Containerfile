FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY README.md ./
COPY src ./src
COPY scripts ./scripts
COPY data/isaacguru ./data/isaacguru
RUN uv sync --frozen && uv run scripts/seed_db.py

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY --from=builder /app/data/isaacguru.db ./data/isaacguru.db

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sanic", "tboi_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]