"""Plan G §T12 — verifies that a ``traceparent`` header on a gateway request
propagates through the OTel pipeline into Tempo.

Opt-in: needs the full compose stack up (``gateway``, ``otel-collector``,
``tempo``) and the gateway image built with the OTel Java agent (Plan G §T12,
Dockerfile additions). Skipped unless ``TRACING_E2E=1`` so the regular
``pytest`` suite doesn't try to hit a live stack.

Run locally with:
    docker compose -f infra/docker-compose/docker-compose.yml up -d \\
        gateway otel-collector tempo
    TRACING_E2E=1 pytest tests/integration/test_trace_propagation.py -v
"""
from __future__ import annotations

import os
import time

import pytest
import requests

pytestmark = pytest.mark.skipif(
    os.environ.get("TRACING_E2E") != "1",
    reason="set TRACING_E2E=1 with the compose stack up to run",
)


GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
TEMPO_URL = os.environ.get("TEMPO_URL", "http://localhost:3200")


def test_trace_id_propagates_from_gateway_to_tempo() -> None:
    trace_id = "0af7651916cd43dd8448eb211c80319c"
    headers = {"traceparent": f"00-{trace_id}-b7ad6b7169203331-01"}

    r = requests.post(
        f"{GATEWAY_URL}/api/v1/detect",
        headers=headers,
        files={"file": ("x.csv", b"a,b\n1,2")},
        timeout=10,
    )
    # 200/401/415 are all acceptable — the request hit the gateway and the
    # OTel agent recorded a span. We only care that *some* span carrying our
    # trace_id eventually lands in Tempo.
    assert r.status_code in (200, 401, 415, 400)

    # Tempo's ingester batches; give it a couple of seconds to flush.
    deadline = time.monotonic() + 10
    last_status = None
    while time.monotonic() < deadline:
        t = requests.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=5)
        last_status = t.status_code
        if t.status_code == 200 and t.json().get("batches"):
            return
        time.sleep(1)

    pytest.fail(
        f"trace {trace_id} did not appear in Tempo within 10s "
        f"(last Tempo status: {last_status})"
    )
