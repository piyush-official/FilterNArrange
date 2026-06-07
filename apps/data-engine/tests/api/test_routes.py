import io
import pytest
from fastapi.testclient import TestClient

from filternarrange_engine.api.main import build_app
from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_format_csv import plugin as csv_plugin
from filternarrange_format_json import plugin as json_plugin
from filternarrange_filter_column import plugin as col_filter_plugin


class _InMemoryStore:
    def __init__(self): self._blobs: dict[str, bytes] = {}
    def put(self, ref, data, size, content_type):
        self._blobs[ref] = data.read()
    def get(self, ref):
        if ref not in self._blobs:
            raise FileNotFoundError(ref)
        return io.BytesIO(self._blobs[ref])
    def ensure_bucket(self, b): pass


@pytest.fixture
def app_and_store():
    store = _InMemoryStore()
    registry = PluginRegistry()
    registry.register_format(csv_plugin)
    registry.register_format(json_plugin)
    registry.register_filter(col_filter_plugin)
    app = build_app(store=store, registry=registry)
    return TestClient(app), store


def _put_csv(store, ref):
    body = b"name,age\nA,1\nB,2\n"
    store.put(ref, io.BytesIO(body), len(body), "text/csv")


def test_detect_returns_csv(app_and_store):
    client, store = app_and_store
    _put_csv(store, "uploads/u/x.csv")
    res = client.post("/detect", json={"ref": "uploads/u/x.csv"})
    assert res.status_code == 200
    body = res.json()
    assert body["format"] == "csv"
    assert any(c["name"] == "name" for c in body["schema"])


def test_filter_returns_subset_rows(app_and_store):
    client, store = app_and_store
    _put_csv(store, "uploads/u/x.csv")
    res = client.post("/filter", json={
        "ref": "uploads/u/x.csv",
        "filter": {"kind": "column", "keep": ["name"]},
        "sampleSize": 10,
    })
    assert res.status_code == 200
    body = res.json()
    assert [c["name"] for c in body["schema"]] == ["name"]
    assert body["rows"] == [{"name": "A"}, {"name": "B"}]


def test_convert_writes_result_blob(app_and_store):
    client, store = app_and_store
    _put_csv(store, "uploads/u/x.csv")
    res = client.post("/convert", json={
        "ref": "uploads/u/x.csv",
        "filter": {"kind": "column", "keep": ["name"]},
        "outputFormat": "json",
    })
    assert res.status_code == 200
    ref = res.json()["resultRef"]
    out = store.get(ref).read()
    assert b"\"name\"" in out
    assert b"A" in out and b"B" in out


def test_detect_unknown_ref_returns_envelope(app_and_store):
    client, _ = app_and_store
    res = client.post("/detect", json={"ref": "uploads/u/missing.csv"})
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert "traceId" in body
