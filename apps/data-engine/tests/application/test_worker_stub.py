"""Plan D Task 11 — worker stub.

PR-3 lands the real Kafka consumer; for now we just assert the stub awaits
without raising until it's cancelled.
"""
from __future__ import annotations
import asyncio
import pytest

from filternarrange_engine.application.worker import run_worker


@pytest.mark.asyncio
async def test_stub_is_cancellable():
    task = asyncio.create_task(run_worker())
    # Let the loop step into the stub so the cancel hits inside sleep().
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
