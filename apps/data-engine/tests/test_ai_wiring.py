import pytest
from httpx import ASGITransport, AsyncClient

from filternarrange_engine.core.llm import AIOutput
from filternarrange_engine.main import create_app


class _StubOrch:
    async def run(self, name, payload):
        return AIOutput(capability=name, result={"ok": True, "name": name})


@pytest.mark.asyncio
async def test_ai_endpoints_registered_with_default_set():
    app = create_app(
        orchestrator_override=_StubOrch(),
        enabled_names={
            "nl_to_filter",
            "auto_summary",
            "chart_suggest",
            "anomaly_detect",
        },
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
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
        assert r.status_code == 200
        assert r.json() == {"ok": True, "name": "auto_summary"}


@pytest.mark.asyncio
async def test_disabled_via_enabled_names_does_not_expose():
    app = create_app(
        orchestrator_override=_StubOrch(),
        enabled_names={"nl_to_filter", "auto_summary", "chart_suggest"},
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
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
    assert r.json()["detail"]["code"] == "AI_CAPABILITY_DISABLED"
