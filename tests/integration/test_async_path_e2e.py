"""End-to-end async path against the full docker-compose stack (Plan D §T19).

This test is opt-in: it requires a running compose stack with the Kafka worker
and is marked ``@pytest.mark.integration`` so CI does not pick it up by default.
Run locally with:

    docker compose -f infra/docker-compose/docker-compose.yml up -d
    pytest tests/integration/test_async_path_e2e.py -m integration -v
"""
from __future__ import annotations

import json
import os
import pathlib
import time
import uuid

import httpx
import pytest

GATEWAY = os.getenv("FILTERNARRANGE_GATEWAY_URL", "http://localhost:8080")
WS_HOST = os.getenv("FILTERNARRANGE_WS_HOST", "localhost:8080")


@pytest.fixture
def sample_csv(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "sample.csv"
    header = "id,age,country\n"
    rows = "\n".join(f"{i},{20 + (i % 60)},IN" for i in range(1_000_000))
    p.write_text(header + rows)
    assert p.stat().st_size > 25 * 1024 * 1024
    return p


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_path_completes_via_websocket(sample_csv):
    websockets = pytest.importorskip("websockets")

    async with httpx.AsyncClient(timeout=60.0) as c:
        upload = await c.post(
            f"{GATEWAY}/api/v1/uploads", json={"filename": "sample.csv"}
        )
        assert upload.status_code == 200
        upload_ref = upload.json()["ref"]
        signed_url = upload.json()["upload_url"]
        with open(sample_csv, "rb") as f:
            r = await c.put(signed_url, content=f.read())
            assert r.status_code in (200, 204)

        idem = str(uuid.uuid4())
        job = await c.post(
            f"{GATEWAY}/api/v1/jobs",
            headers={"Idempotency-Key": idem},
            json={
                "kind": "batch-filter",
                "params": {
                    "input": {"ref": upload_ref, "detected_format": "csv"},
                    "operations": [
                        {"kind": "filter", "mode": "row", "predicate": "age > 18"}
                    ],
                },
            },
        )
        assert job.status_code == 202
        job_id = job.json()["jobId"]

    seen: list[str] = []
    async with websockets.connect(f"ws://{WS_HOST}/ws/jobs/{job_id}") as ws:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            msg = json.loads(await ws.recv())
            seen.append(msg["status"])
            if msg["status"] in ("completed", "failed", "cancelled"):
                break

    assert "running" in seen
    assert seen[-1] == "completed"

    async with httpx.AsyncClient(timeout=60.0) as c:
        get = await c.get(f"{GATEWAY}/api/v1/jobs/{job_id}")
        assert get.status_code == 200
        result_ref = get.json()["resultRef"]
        assert result_ref is not None
        dl = await c.get(
            f"{GATEWAY}/api/v1/files/{result_ref}", follow_redirects=True
        )
        assert dl.status_code == 200
        assert len(dl.content) > 0
