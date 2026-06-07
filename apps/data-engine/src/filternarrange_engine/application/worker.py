"""Worker entrypoint (Plan D foundations stub).

The full async-path worker — Kafka consumer + bulkheaded plugin dispatch +
heartbeat — lands in Plan D PR-3 (T13–T15). This stub exists so the MODE
switch in ``filternarrange_engine.main`` can import + invoke ``run_worker``
today without crashing.
"""
from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)


async def run_worker() -> None:
    """Placeholder worker loop. Sleeps until the process is killed.

    The real implementation will:
    - Connect to the Kafka broker at ``KAFKA_BROKERS``.
    - Consume ``topic.v1.jobs`` with a unique consumer group per worker.
    - For each job: validate the message, fetch the input blob from MinIO,
      dispatch to the matching plugin via the bulkheaded thread pool, and
      publish a ``topic.v1.job-results`` event with status / progress /
      result_ref or error.
    - Emit a heartbeat on the same topic every 5s while a job is running.
    """
    brokers = os.getenv("KAFKA_BROKERS", "redpanda:9092")
    log.warning(
        "worker mode is stubbed — KAFKA_BROKERS=%s. Real consumer lands in "
        "Plan D PR-3. Sleeping until SIGINT.",
        brokers,
    )
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        log.info("worker stub cancelled, shutting down")
        raise


__all__ = ["run_worker"]
