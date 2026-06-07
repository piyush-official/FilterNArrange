import asyncio
import pytest
from unittest.mock import AsyncMock

from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.adapters.llm.registry import (
    AiCapabilityRegistry,
    CapabilityNotFoundError,
)
from filternarrange_engine.application.ai_orchestrator import AiOrchestrator


class _FakeCap:
    name = "auto_summary"
    required_tier = "free"
    default_model_setting = "auto_summary"

    def __init__(self):
        self.calls = 0

    async def run(self, llm, payload):
        self.calls += 1
        await asyncio.sleep(0.05)
        return {"summary": f"v={payload['n']}", "key_observations": []}


@pytest.mark.asyncio
async def test_runs_capability_and_returns_result():
    cap = _FakeCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AsyncMock()
    cache.get.return_value = None
    orch = AiOrchestrator(
        registry=reg,
        llm=MockLLMProvider(),
        cache=cache,
        max_concurrent=4,
        models={"auto_summary": "llama3.1:8b"},
    )
    out = await orch.run("auto_summary", {"n": 1})
    assert out.result == {"summary": "v=1", "key_observations": []}
    assert out.cache_hit is False
    assert out.model == "llama3.1:8b"
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_returns_cached_result_without_calling_capability():
    cap = _FakeCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AsyncMock()
    cache.get.return_value = {"summary": "cached", "key_observations": []}
    orch = AiOrchestrator(
        registry=reg,
        llm=MockLLMProvider(),
        cache=cache,
        max_concurrent=4,
        models={"auto_summary": "llama3.1:8b"},
    )
    out = await orch.run("auto_summary", {"n": 1})
    assert out.cache_hit is True
    assert out.result["summary"] == "cached"
    assert cap.calls == 0
    cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_capability_raises():
    reg = AiCapabilityRegistry({})
    cache = AsyncMock()
    cache.get.return_value = None
    orch = AiOrchestrator(
        registry=reg,
        llm=MockLLMProvider(),
        cache=cache,
        max_concurrent=4,
        models={},
    )
    with pytest.raises(CapabilityNotFoundError):
        await orch.run("nope", {})


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    peak = 0
    current = 0
    lock = asyncio.Lock()

    class _Cap:
        name = "auto_summary"
        required_tier = "free"
        default_model_setting = "auto_summary"

        async def run(self, llm, payload):
            nonlocal peak, current
            async with lock:
                current += 1
                peak = max(peak, current)
            await asyncio.sleep(0.05)
            async with lock:
                current -= 1
            return {"summary": "x", "key_observations": []}

    cap = _Cap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AsyncMock()
    cache.get.return_value = None
    orch = AiOrchestrator(
        registry=reg,
        llm=MockLLMProvider(),
        cache=cache,
        max_concurrent=4,
        models={"auto_summary": "llama3.1:8b"},
    )
    await asyncio.gather(
        *[orch.run("auto_summary", {"n": i}) for i in range(10)]
    )
    assert peak <= 4
