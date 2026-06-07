# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.2.5

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN uv pip install --system .

RUN useradd --system --uid 1001 --create-home --home-dir /home/engine engine \
    && chown -R engine:engine /app
USER engine

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=10 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Plan D §2: honour MODE at runtime. The Python entrypoint dispatches to
# uvicorn (HTTP modes) or the worker loop (MODE=worker). Override MODE in
# compose / k8s without changing this image.
ENV MODE=full
CMD ["python", "-m", "filternarrange_engine.main"]
