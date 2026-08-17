# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY packages/ipost packages/ipost
COPY apps/api apps/api

RUN uv sync --package ipost-api --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080
CMD ["uvicorn", "ipost_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
