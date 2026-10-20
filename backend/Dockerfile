FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/
WORKDIR /srv/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend /srv/backend
RUN uv sync --frozen --no-dev
ENV PATH="/srv/backend/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    APP_ENV=demo \
    HOST=0.0.0.0 \
    PORT=8105 \
    ALLOW_NETWORK_BIND=true \
    DATABASE_URL=postgresql+psycopg://hr:hr@db:5432/skillgraph \
    AUTO_SEED=true \
    RUN_MIGRATIONS=true \
    EMBEDDINGS_ENABLED=false
EXPOSE 8105
CMD ["python", "-m", "app"]
