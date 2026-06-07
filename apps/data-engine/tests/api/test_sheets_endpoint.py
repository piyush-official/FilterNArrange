"""Cover POST /sheets for XLSX uploads + non-xlsx rejection."""
import io
import pathlib
import pytest
from fastapi.testclient import TestClient

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.api.main import build_app
from filternarrange_format_csv import plugin as csv_plugin
from filternarrange_format_xlsx import plugin as xlsx_plugin


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


XLSX_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "plugins" / "format-xlsx" / "tests" / "fixtures" / "two_sheets.xlsx"
)


@pytest.fixture
def client():
    store = _InMemoryStore()
    registry = PluginRegistry()
    registry.register_format(csv_plugin)
    registry.register_format(xlsx_plugin)
    app = build_app(store=store, registry=registry)
    blob = XLSX_FIXTURE.read_bytes()
    store.put("uploads/u/wb.xlsx", io.BytesIO(blob), len(blob),
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    csv_body = b"name,age\nA,1\n"
    store.put("uploads/u/x.csv", io.BytesIO(csv_body), len(csv_body), "text/csv")
    return TestClient(app)


def test_sheets_lists_xlsx_sheet_names(client):
    res = client.post("/sheets", json={"ref": "uploads/u/wb.xlsx"})
    assert res.status_code == 200, res.text
    assert res.json()["sheets"] == ["people", "orders"]


def test_sheets_rejects_csv(client):
    res = client.post("/sheets", json={"ref": "uploads/u/x.csv"})
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "NOT_MULTI_SHEET"


def test_sheets_unknown_ref_404(client):
    res = client.post("/sheets", json={"ref": "uploads/u/missing.xlsx"})
    assert res.status_code == 404, res.text
    assert res.json()["code"] == "NOT_FOUND"
