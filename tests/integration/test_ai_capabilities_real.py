"""Real Ollama integration test (Plan E §T15).

SKIPPED unless ``RUN_OLLAMA_TESTS=1``. Designed for a self-hosted runner with
Ollama up and ``llama3.1:8b`` + ``qwen2.5:7b`` pulled.
"""
import os

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_OLLAMA_TESTS") != "1",
    reason="set RUN_OLLAMA_TESTS=1 to run against a live Ollama",
)


BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


@pytest.mark.asyncio
async def test_auto_summary_against_real_ollama():
    from filternarrange_ai_auto_summary.plugin import AutoSummaryCapability
    from filternarrange_engine.adapters.llm.ollama import OllamaProvider

    async with OllamaProvider(
        base_url=BASE, timeout_seconds=60, default_model="llama3.1:8b"
    ) as llm:
        cap = AutoSummaryCapability()
        out = await cap.run(
            llm,
            {
                "schema": [
                    {"name": "country", "type": "string"},
                    {"name": "signups", "type": "integer"},
                ],
                "sample_rows": [
                    {"country": "IN", "signups": 220},
                    {"country": "US", "signups": 130},
                    {"country": "DE", "signups": 90},
                ],
                "total_rows": 3,
                "total_size_bytes": 256,
            },
        )
    assert isinstance(out["summary"], str) and len(out["summary"]) > 10
    assert isinstance(out["key_observations"], list)


@pytest.mark.asyncio
async def test_nl_to_filter_against_real_ollama():
    from filternarrange_ai_nl_to_filter.plugin import NlToFilterCapability
    from filternarrange_engine.adapters.llm.ollama import OllamaProvider

    async with OllamaProvider(
        base_url=BASE, timeout_seconds=60, default_model="qwen2.5:7b"
    ) as llm:
        cap = NlToFilterCapability()
        out = await cap.run(
            llm,
            {
                "query": "rows where signups > 100",
                "schema": [
                    {"name": "country", "type": "string"},
                    {"name": "signups", "type": "integer"},
                ],
            },
        )
    assert out["filter_spec"]["kind"] in {"column", "row", "expression", "regex"}
    assert 0.0 <= out["confidence"] <= 1.0
