"""Plan G §T10 — Prometheus scrape endpoint at /metrics.

Mounted on the FastAPI app by ``build_app`` (api/main.py) so Prometheus
config at infra/observability/prometheus/prometheus.yml can scrape it
out-of-the-box.
"""
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
