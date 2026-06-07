# SPDX-License-Identifier: Apache-2.0
"""Health endpoint contract test."""

from fastapi.testclient import TestClient
from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.api.main import build_app


def test_healthz_returns_ok() -> None:
    app = build_app(store=object(), registry=PluginRegistry())
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["status"] == "ok"
    assert "formats" in body and "filters" in body
