"""Prometheus metrics for the data-engine (Plan G §T10).

Counters / histograms live as module-level globals so the rest of the
codebase can import and increment without plumbing the registry through.
The /metrics endpoint is wired up in ``api.metrics_routes``.
"""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

# AI capability metrics — emitted by the orchestrator on every dispatch.
ai_capability_requests = Counter(
    "fna_ai_capability_requests_total",
    "Total AI capability dispatches.",
    ["capability", "cache_hit"],
)

ai_capability_duration = Histogram(
    "fna_ai_capability_seconds",
    "AI capability wall-clock seconds.",
    ["capability"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

# Worker metrics — emitted by the Kafka worker on each handled job.
worker_jobs_handled = Counter(
    "fna_worker_jobs_total",
    "Total Kafka jobs handled.",
    ["kind", "status"],
)

# Retention worker — exposes the last-successful-run timestamp so the
# RetentionWorkerStalled alert can fire on >36h staleness.
retention_last_run_timestamp = Gauge(
    "fna_retention_worker_last_run_timestamp_seconds",
    "Unix timestamp of the most recent successful retention sweep.",
)
