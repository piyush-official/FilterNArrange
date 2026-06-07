"""Plan E §T25 — independent concurrency check on the orchestrator's semaphore.

This complements ``test_ai_orchestrator.py::test_semaphore_caps_concurrency``
by exercising the real Redis-shaped cache adapter (with the in-memory backing
mock) so the path that runs in production is what's measured.
"""
from __future__ import annotations

import asyncio

import pytest

from filternarrange_engine.adapters.llm.cache import AiCache
from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.adapters.llm.registry import AiCapabilityRegistry
from filternarrange_engine.application.ai_orchestrator import AiOrchestrator


class _InMemRedis:
    def __init__(self):
        self.data: dict[str, str] = {}

    async def get(self, k):
        return self.data.get(k)

    async def set(self, k, v, *, ex=None):
        self.data[k] = v


@pytest.mark.asyncio
async def test_semaphore_caps_concurrent_calls_at_four():
    current = 0
    peak = 0
    lock = asyncio.Lock()

    class _Cap:
        name = "nl_to_filter"
        required_tier = "free"
        default_model_setting = "nl_to_filter"

        async def run(self, llm, payload):
            nonlocal current, peak
            async with lock:
                current += 1
                peak = max(peak, current)
            await asyncio.sleep(0.08)
            async with lock:
                current -= 1
            return {"filter_spec": {"kind": "row"}, "confidence": 0.5}

    cap = _Cap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AiCache(redis=_InMemRedis(), ttl_seconds=3600)
    orch = AiOrchestrator(
        registry=reg,
        llm=MockLLMProvider(),
        cache=cache,
        max_concurrent=4,
        models={"nl_to_filter": "qwen2.5:7b"},
    )

    coros = [orch.run("nl_to_filter", {"q": i}) for i in range(10)]
    results = await asyncio.gather(*coros)
    assert all(r.result["filter_spec"]["kind"] == "row" for r in results)
    assert peak <= 4
