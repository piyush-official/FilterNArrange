import pytest
from unittest.mock import AsyncMock

from filternarrange_engine.application import worker


@pytest.mark.asyncio
async def test_handle_job_writes_completed_message_on_success(monkeypatch):
    producer = AsyncMock()
    monkeypatch.setattr(worker, "_pipeline",
                        AsyncMock(return_value="results/22222222-2222-2222-2222-222222222222/filter/11111111-1111-1111-1111-111111111111.json"))
    monkeypatch.setattr(worker, "_load_job_status",
                        AsyncMock(return_value=None))

    payload = {
        "job_id":     "11111111-1111-1111-1111-111111111111",
        "user_id":    "22222222-2222-2222-2222-222222222222",
        "kind":       "batch-filter",
        "params":     {"input": {"ref": "uploads/x.csv"}, "operations": []},
        "priority":   0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id":   "t",
    }
    await worker.handle_job(payload, producer=producer, heartbeat_interval_s=0.0)

    sent_topics = [c.args[0] for c in producer.send.await_args_list]
    assert "topic.v1.job-results" in sent_topics
    statuses = [
        c.kwargs.get("payload", {}).get("status")
        for c in producer.send.await_args_list
        if c.args[0] == "topic.v1.job-results"
    ]
    assert "completed" in statuses


@pytest.mark.asyncio
async def test_handle_job_skips_when_already_terminal(monkeypatch):
    producer = AsyncMock()
    monkeypatch.setattr(worker, "_load_job_status",
                        AsyncMock(return_value="completed"))
    payload = {
        "job_id":     "11111111-1111-1111-1111-111111111111",
        "user_id":    "22222222-2222-2222-2222-222222222222",
        "kind":       "batch-filter",
        "params":     {},
        "priority":   0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id":   "t",
    }
    await worker.handle_job(payload, producer=producer, heartbeat_interval_s=0.0)
    producer.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_job_emits_failed_on_pipeline_exception(monkeypatch):
    producer = AsyncMock()
    monkeypatch.setattr(worker, "_pipeline",
                        AsyncMock(side_effect=RuntimeError("plugin blew up")))
    monkeypatch.setattr(worker, "_load_job_status",
                        AsyncMock(return_value=None))
    payload = {
        "job_id":     "11111111-1111-1111-1111-111111111111",
        "user_id":    "22222222-2222-2222-2222-222222222222",
        "kind":       "batch-filter",
        "params":     {},
        "priority":   0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id":   "t",
    }
    await worker.handle_job(payload, producer=producer, heartbeat_interval_s=0.0)
    statuses = [
        c.kwargs.get("payload", {}).get("status")
        for c in producer.send.await_args_list
        if c.args[0] == "topic.v1.job-results"
    ]
    assert "failed" in statuses
