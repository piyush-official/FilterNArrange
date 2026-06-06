# SPDX-License-Identifier: Apache-2.0
"""Health endpoint contract test."""

from fastapi.testclient import TestClient

from filternarrange_engine.api.main import app


def test_health_returns_up() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "UP"}
