import json
import pytest

from filternarrange_engine.adapters.kafka.consumer import JobConsumer


@pytest.mark.asyncio
async def test_consumer_dispatches_one_message_per_handler_call():
    received: list = []

    async def handler(payload):
        received.append(payload)

    c = JobConsumer(
        bootstrap_servers="dummy:9092",
        group_id="python-worker-free",
        handler=handler,
    )
    await c._dispatch(json.dumps({
        "job_id":     "11111111-1111-1111-1111-111111111111",
        "user_id":    "22222222-2222-2222-2222-222222222222",
        "kind":       "batch-filter",
        "params":     {},
        "priority":   0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id":   "t",
    }))
    assert len(received) == 1


@pytest.mark.asyncio
async def test_consumer_skips_invalid_messages():
    received: list = []

    async def handler(payload):
        received.append(payload)

    c = JobConsumer("dummy:9092", "python-worker-free", handler)
    await c._dispatch('{"job_id":"not-a-uuid"}')
    assert received == []


@pytest.mark.asyncio
async def test_consumer_skips_non_json_messages():
    received: list = []

    async def handler(payload):
        received.append(payload)

    c = JobConsumer("dummy:9092", "python-worker-free", handler)
    await c._dispatch("this is not json")
    assert received == []
