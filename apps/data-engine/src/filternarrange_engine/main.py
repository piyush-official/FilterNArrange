"""Data-engine entrypoint — MODE-aware boot (Plan D §2 loose-coupling rule 6).

Plan B/C left the HTTP app under ``filternarrange_engine.api.main:app``. Plan D
introduces this top-level ``main`` module that reads ``MODE`` and dispatches:

- ``full``   — HTTP serving via uvicorn + worker as a background task.
- ``data``   — HTTP only (the Plan B/C sync path).
- ``worker`` — pure Kafka consumer; no HTTP.
- ``ai``     — placeholder for Plan E.

The existing ``api.main:app`` is unchanged so docker-compose entries that
reference it directly keep working.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI

from filternarrange_engine.api.ai_routes import build_ai_router
from filternarrange_engine.api.main import build_app
from filternarrange_engine.application.worker import run_worker
from filternarrange_engine.platform.mode import Mode, serves_http, serves_worker


log = logging.getLogger(__name__)


def create_app(
    *,
    orchestrator_override: Any | None = None,
    enabled_names: set[str] | None = None,
) -> FastAPI:
    """Build the FastAPI app and attach the Plan E AI surface.

    Tests pass ``orchestrator_override`` + ``enabled_names`` so the AI routes
    can be exercised without bringing up Ollama / Redis. Production boot wires
    a real orchestrator in the lifespan handler (see ``main()`` below).
    """
    app = build_app()
    names = set(enabled_names or set())
    app.include_router(
        build_ai_router(orchestrator_override, enabled_names=names),
        prefix="/ai",
    )
    return app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    mode = Mode.current()
    log.info("Booting filternarrange-data-engine in MODE=%s", mode.value)

    http_only = serves_http(mode) and not serves_worker(mode)
    worker_only = serves_worker(mode) and not serves_http(mode)

    if http_only:
        import uvicorn
        uvicorn.run(
            "filternarrange_engine.api.main:app",
            host="0.0.0.0", port=8000,
        )
    elif worker_only:
        asyncio.run(run_worker())
    elif mode is Mode.FULL:
        # HTTP serving owns the asyncio loop; we kick off the worker as a
        # background task on the same loop. Plan D PR-3 wires real lifecycle
        # management (graceful shutdown, cancellation propagation).
        import uvicorn

        config = uvicorn.Config(
            "filternarrange_engine.api.main:app",
            host="0.0.0.0", port=8000, loop="asyncio",
        )
        server = uvicorn.Server(config)

        async def _run_both() -> None:
            worker_task = asyncio.create_task(run_worker())
            try:
                await server.serve()
            finally:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

        asyncio.run(_run_both())
    else:
        raise SystemExit(f"MODE={mode.value} not yet implemented")


if __name__ == "__main__":
    main()
