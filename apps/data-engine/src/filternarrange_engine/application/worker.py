"""Async worker — consume jobs, run the pipeline, publish results (Plan D §3)."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Mapping

from filternarrange_engine.adapters.kafka.consumer import JobConsumer
from filternarrange_engine.adapters.kafka.producer import JobResultsProducer
from filternarrange_engine.adapters.kafka.topics import JOB_RESULTS
from filternarrange_engine.application.heartbeat import Heartbeat
from filternarrange_engine.platform import bulkheads
from filternarrange_engine.platform.audit import audit_event_publish

log = logging.getLogger(__name__)

_BOOTSTRAP = os.getenv("REDPANDA_BROKERS", os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092"))
_HEARTBEAT_S = float(os.getenv("WORKER_HEARTBEAT_S", "5.0"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _load_job_status(job_id: str) -> str | None:
    """Ask the gateway for the canonical job status. Idempotency gate per Plan D §6."""
    import httpx
    base = os.getenv("GATEWAY_INTERNAL_URL", "http://gateway:8080")
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{base}/api/v1/jobs/{job_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()["status"]


async def _pipeline(payload: Mapping[str, Any]) -> str:
    from filternarrange_engine.application import pipeline
    bulkheads.init()
    assert bulkheads.plugin_async is not None
    async with bulkheads.plugin_async:
        return await pipeline.run(payload, cpu_pool=bulkheads.data_cpu_pool)


async def handle_job(
    payload: Mapping[str, Any],
    *,
    producer: JobResultsProducer,
    heartbeat_interval_s: float = _HEARTBEAT_S,
) -> None:
    job_id = payload["job_id"]
    trace_id = payload["trace_id"]
    user_id = payload["user_id"]

    try:
        current = await _load_job_status(job_id)
    except Exception:
        current = None
    if current in ("running", "completed", "failed", "cancelled"):
        log.info("Skipping job %s — gateway reports status=%s", job_id, current)
        return

    async def emit_running() -> None:
        await producer.send(JOB_RESULTS, key=job_id, payload={
            "job_id":      job_id,
            "status":      "running",
            "progress":    0,
            "finished_at": _now(),
            "trace_id":    trace_id,
        })

    hb = Heartbeat(heartbeat_interval_s, emit_running) if heartbeat_interval_s > 0 else None
    hb_task = asyncio.create_task(hb.run()) if hb else None
    try:
        await audit_event_publish(
            producer, user_id=user_id, action="job.running",
            target=job_id, trace_id=trace_id,
        )

        result_ref = await _pipeline(payload)

        await producer.send(JOB_RESULTS, key=job_id, payload={
            "job_id":      job_id,
            "status":      "completed",
            "progress":    100,
            "result_ref":  result_ref,
            "finished_at": _now(),
            "trace_id":    trace_id,
        })
        await audit_event_publish(
            producer, user_id=user_id, action="job.completed",
            target=job_id, metadata={"result_ref": result_ref},
            trace_id=trace_id,
        )
    except Exception as e:
        log.exception("Job %s failed", job_id)
        await producer.send(JOB_RESULTS, key=job_id, payload={
            "job_id":      job_id,
            "status":      "failed",
            "error": {
                "code":     "PLUGIN_FAILURE",
                "message":  str(e),
                "trace_id": trace_id,
            },
            "finished_at": _now(),
            "trace_id":    trace_id,
        })
        await audit_event_publish(
            producer, user_id=user_id, action="job.failed",
            target=job_id, metadata={"error": str(e)}, trace_id=trace_id,
        )
    finally:
        if hb:
            await hb.stop()
        if hb_task:
            await hb_task


async def run_worker() -> None:
    bulkheads.init()
    producer = JobResultsProducer(_BOOTSTRAP)
    await producer.start()

    async def handler(payload: Mapping[str, Any]) -> None:
        await handle_job(payload, producer=producer)

    paid = JobConsumer(_BOOTSTRAP, "python-worker-paid", handler)
    free = JobConsumer(_BOOTSTRAP, "python-worker-free", handler)
    await paid.start()
    await free.start()

    try:
        await asyncio.gather(paid.run(), free.run())
    finally:
        await paid.stop()
        await free.stop()
        await producer.stop()
        bulkheads.shutdown()


__all__ = ["run_worker", "handle_job"]
