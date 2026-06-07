"""Job-kind → plugin-chain dispatch (Plan D §3 worker pipeline).

This is the boundary between the Kafka consumer (``worker.handle_job``) and
the in-process plugin services that actually transform data. Plan D wires the
*envelope* (queue, idempotency, heartbeat, result-emit); the heavyweight plugin
orchestration — driving FilterService / ConvertService / AnalysisService end-to-end
with real MinIO uploads — is staged for Plan E refinement, where the worker
gains direct ObjectStore access and the legitimate execution profile is settled.

For now ``run`` returns a deterministic ``result_ref`` so the gateway can persist
it and the WebSocket can broadcast a completion envelope. Integration tests in
Plan D §T19-T22 assert on the envelope semantics, not on the plugin output.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

log = logging.getLogger(__name__)

_KIND_TO_PREFIX = {
    "batch-filter":     "filter",
    "convert":          "convert",
    "analyze":          "analyze",
    # Plan E §T19 — long-running anomaly scan. Real implementation streams the
    # full dataset through AnomalyDetectCapability and writes findings to
    # MinIO; for now the worker emits a deterministic result_ref so the
    # gateway can persist it and the WS can broadcast completion.
    "ai-anomaly-full":  "ai/anomaly",
}


async def run(payload: Mapping[str, Any], cpu_pool=None) -> str:
    kind = payload["kind"]
    job_id = payload["job_id"]
    user_id = payload["user_id"]
    prefix = _KIND_TO_PREFIX.get(kind)
    if prefix is None:
        raise ValueError(f"Unknown job kind: {kind}")
    log.info("Pipeline dispatch: kind=%s job=%s user=%s", kind, job_id, user_id)
    return f"results/{user_id}/{prefix}/{job_id}.json"
