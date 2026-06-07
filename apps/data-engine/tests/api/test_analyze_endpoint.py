"""Cover the /analyze endpoint and the optional filter step."""
import io
import pytest
from fastapi.testclient import TestClient

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.api.main import build_app
from filternarrange_analysis_summary_stats import plugin as summary_plugin
from filternarrange_filter_row import plugin as row_filter_plugin
from filternarrange_format_csv import plugin as csv_plugin


class _InMemoryStore:
    def __init__(self):
        self._blobs: dict[str, bytes] = {}

    def put(self, ref, data, size, content_type):
        self._blobs[ref] = data.read()

    def get(self, ref):
        if ref not in self._blobs:
            raise FileNotFoundError(ref)
        return io.BytesIO(self._blobs[ref])

    def ensure_bucket(self, b):
        return None


@pytest.fixture
def client_and_ref():
    store = _InMemoryStore()
    registry = PluginRegistry()
    registry.register_format(csv_plugin)
    registry.register_filter(row_filter_plugin)
    registry.register_analysis(summary_plugin)
    app = build_app(store=store, registry=registry)
    body = b"name,age\nAlice,37\nBob,17\nCarol,40\n"
    store.put("uploads/u/people.csv", io.BytesIO(body), len(body), "text/csv")
    return TestClient(app), "uploads/u/people.csv"


def test_analyze_summary_stats(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/analyze", json={
        "ref": ref,
        "analysis": {"kind": "summary_stats", "options": {}},
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "summary_stats"
    cols = {c["name"]: c for c in body["payload"]["columns"]}
    assert cols["name"]["count"] == 3


def test_analyze_with_filter(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/analyze", json={
        "ref": ref,
        "filter": {"kind": "row", "predicate": {"col": "age", "op": "gt", "value": "30"}},
        "analysis": {"kind": "summary_stats", "options": {}},
    })
    assert res.status_code == 200, res.text
    cols = {c["name"]: c for c in res.json()["payload"]["columns"]}
    assert cols["name"]["count"] == 2


def test_analyze_unknown_kind(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/analyze", json={
        "ref": ref,
        "analysis": {"kind": "nope"},
    })
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "UNKNOWN_ANALYSIS"
