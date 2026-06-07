import asyncio
import pytest

from filternarrange_engine.application.heartbeat import Heartbeat


@pytest.mark.asyncio
async def test_heartbeat_emits_periodic_running_messages():
    sent: list[str] = []

    async def emit():
        sent.append("tick")

    hb = Heartbeat(interval_s=0.05, emit=emit)
    task = asyncio.create_task(hb.run())
    await asyncio.sleep(0.18)
    await hb.stop()
    await task
    assert len(sent) >= 3


@pytest.mark.asyncio
async def test_heartbeat_stops_cleanly():
    sent: list[str] = []

    async def emit():
        sent.append("tick")

    hb = Heartbeat(interval_s=10.0, emit=emit)
    task = asyncio.create_task(hb.run())
    await asyncio.sleep(0.01)
    await hb.stop()
    await asyncio.wait_for(task, timeout=1.0)
    assert sent == ["tick"]
