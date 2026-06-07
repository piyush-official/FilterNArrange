"""Cover the four FilterSpec kinds dispatching through /filter."""
import io
import pytest
from fastapi.testclient import TestClient

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.api.main import build_app
from filternarrange_filter_column import plugin as col_filter_plugin
from filternarrange_filter_expression import plugin as expr_filter_plugin
from filternarrange_filter_regex import plugin as regex_filter_plugin
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
    registry.register_filter(col_filter_plugin)
    registry.register_filter(row_filter_plugin)
    registry.register_filter(expr_filter_plugin)
    registry.register_filter(regex_filter_plugin)
    app = build_app(store=store, registry=registry)
    body = b"name,age\nAlice,37\nBob,17\nCarol,40\n"
    store.put("uploads/u/people.csv", io.BytesIO(body), len(body), "text/csv")
    return TestClient(app), "uploads/u/people.csv"


def test_column_kind_still_works(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/filter", json={
        "ref": ref,
        "filter": {"kind": "column", "keep": ["name"]},
        "sampleSize": 10,
    })
    assert res.status_code == 200, res.text
    assert [c["name"] for c in res.json()["schema"]] == ["name"]


def test_row_kind_dispatches(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/filter", json={
        "ref": ref,
        "filter": {"kind": "row", "predicate": {"col": "age", "op": "gt", "value": "30"}},
        "sampleSize": 10,
    })
    assert res.status_code == 200, res.text
    rows = res.json()["rows"]
    assert {r["name"] for r in rows} == {"Alice", "Carol"}


def test_expression_kind_dispatches(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/filter", json={
        "ref": ref,
        "filter": {"kind": "expression", "expr": "name = 'Alice'"},
        "sampleSize": 10,
    })
    assert res.status_code == 200, res.text
    rows = res.json()["rows"]
    assert [r["name"] for r in rows] == ["Alice"]


def test_regex_kind_dispatches(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/filter", json={
        "ref": ref,
        "filter": {"kind": "regex", "pattern": "^A"},
        "sampleSize": 10,
    })
    assert res.status_code == 200, res.text
    rows = res.json()["rows"]
    assert [r["name"] for r in rows] == ["Alice"]


def test_row_unknown_column_validates(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/filter", json={
        "ref": ref,
        "filter": {"kind": "row", "predicate": {"col": "nope", "op": "eq", "value": 1}},
        "sampleSize": 10,
    })
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "VALIDATION_FAILED"


def test_unknown_kind_returns_422(client_and_ref):
    client, ref = client_and_ref
    res = client.post("/filter", json={
        "ref": ref,
        "filter": {"kind": "nope"},
        "sampleSize": 10,
    })
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "UNKNOWN_FILTER"
