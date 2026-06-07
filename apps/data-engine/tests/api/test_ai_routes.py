import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from filternarrange_engine.adapters.llm.registry import CapabilityNotFoundError
from filternarrange_engine.api.ai_routes import build_ai_router
from filternarrange_engine.core.llm import AIOutput, SchemaValidationError


def _make_app(orch, enabled=None):
    app = FastAPI()
    names = enabled or {
        "nl_to_filter",
        "auto_summary",
        "chart_suggest",
        "anomaly_detect",
    }
    app.include_router(build_ai_router(orch, enabled_names=names), prefix="/ai")
    return app


@pytest.mark.asyncio
async def test_nl_to_filter_endpoint():
    orch = AsyncMock()
    orch.run.return_value = AIOutput(
        capability="nl_to_filter",
        result={"filter_spec": {"kind": "row"}, "confidence": 0.9},
        model="qwen2.5:7b",
    )
    app = _make_app(orch)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/ai/nl-to-filter",
            json={
                "ref": "uploads/x.csv",
                "query": "age > 18",
                "schema": [{"name": "age", "type": "integer"}],
            },
        )
    assert r.status_code == 200
    assert r.json()["filter_spec"]["kind"] == "row"
    assert r.json()["confidence"] == 0.9


@pytest.mark.asyncio
async def test_summary_endpoint():
    orch = AsyncMock()
    orch.run.return_value = AIOutput(
        capability="auto_summary",
        result={"summary": "ok", "key_observations": []},
    )
    app = _make_app(orch)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/ai/summary",
            json={
                "ref": "uploads/x.csv",
                "schema": [],
                "sample_rows": [],
                "total_rows": 0,
                "total_size_bytes": 0,
            },
        )
    assert r.status_code == 200
    assert r.json() == {"summary": "ok", "key_observations": []}


@pytest.mark.asyncio
async def test_disabled_capability_returns_404():
    orch = AsyncMock()
    app = _make_app(orch, enabled={"auto_summary"})
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/ai/anomaly",
            json={
                "ref": "x",
                "schema": [],
                "sample_rows": [],
                "summary_stats": {},
            },
        )
    assert r.status_code == 404
    body = r.json()
    assert body["detail"]["code"] == "AI_CAPABILITY_DISABLED"


@pytest.mark.asyncio
async def test_capability_not_found_propagates_as_404():
    orch = AsyncMock()
    orch.run.side_effect = CapabilityNotFoundError("nl_to_filter")
    app = _make_app(orch)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/ai/nl-to-filter",
            json={"ref": "x", "query": "q", "schema": []},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_schema_validation_error_returns_502():
    orch = AsyncMock()
    orch.run.side_effect = SchemaValidationError("bad llm output")
    app = _make_app(orch)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/ai/summary",
            json={
                "ref": "x",
                "schema": [],
                "sample_rows": [],
                "total_rows": 0,
                "total_size_bytes": 0,
            },
        )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "AI_LLM_OUTPUT_INVALID"
