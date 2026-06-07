"""Cancel a queued job before the worker picks it up (Plan D §T22).

Opt-in; requires a running compose stack. Run locally with:

    pytest tests/integration/test_cancel.py -m integration -v
"""
from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest

GATEWAY = os.getenv("FILTERNARRANGE_GATEWAY_URL", "http://localhost:8080")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_before_worker_pickup_blocks_processing():
    async with httpx.AsyncClient(timeout=10.0) as c:
        idem = str(uuid.uuid4())
        job = await c.post(
            f"{GATEWAY}/api/v1/jobs",
            headers={"Idempotency-Key": idem},
            json={
                "kind": "batch-filter",
                "params": {"input": {"ref": "uploads/none.csv"}},
            },
        )
        assert job.status_code == 202
        job_id = job.json()["jobId"]

        cancel = await c.delete(f"{GATEWAY}/api/v1/jobs/{job_id}")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        await asyncio.sleep(3)
        get = await c.get(f"{GATEWAY}/api/v1/jobs/{job_id}")
        assert get.json()["status"] == "cancelled"
