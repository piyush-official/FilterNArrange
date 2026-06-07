import pytest

from filternarrange_engine.adapters.llm.cache import AiCache
from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.adapters.llm.registry import AiCapabilityRegistry
from filternarrange_engine.application.ai_orchestrator import AiOrchestrator


class _CountingCap:
    name = "auto_summary"
    required_tier = "free"
    default_model_setting = "auto_summary"

    def __init__(self):
        self.calls = 0

    async def run(self, llm, payload):
        self.calls += 1
        return {"summary": "x", "key_observations": []}


class _InMemRedis:
    def __init__(self):
        self.data: dict[str, str] = {}

    async def get(self, k):
        return self.data.get(k)

    async def set(self, k, v, *, ex=None):
        self.data[k] = v


@pytest.mark.asyncio
async def test_second_identical_call_is_cache_hit():
    cap = _CountingCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AiCache(redis=_InMemRedis(), ttl_seconds=3600)
    orch = AiOrchestrator(
        registry=reg,
        llm=MockLLMProvider(),
        cache=cache,
        max_concurrent=4,
        models={"auto_summary": "llama3.1:8b"},
    )
    payload = {
        "schema": [],
        "sample_rows": [],
        "total_rows": 0,
        "total_size_bytes": 0,
    }
    a = await orch.run("auto_summary", payload)
    b = await orch.run("auto_summary", payload)
    assert a.cache_hit is False
    assert b.cache_hit is True
    assert cap.calls == 1


@pytest.mark.asyncio
async def test_different_payload_is_separate_cache_entry():
    cap = _CountingCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AiCache(redis=_InMemRedis(), ttl_seconds=3600)
    orch = AiOrchestrator(
        registry=reg,
        llm=MockLLMProvider(),
        cache=cache,
        max_concurrent=4,
        models={"auto_summary": "llama3.1:8b"},
    )
    await orch.run(
        "auto_summary",
        {
            "schema": [],
            "sample_rows": [],
            "total_rows": 1,
            "total_size_bytes": 0,
        },
    )
    await orch.run(
        "auto_summary",
        {
            "schema": [],
            "sample_rows": [],
            "total_rows": 2,
            "total_size_bytes": 0,
        },
    )
    assert cap.calls == 2
