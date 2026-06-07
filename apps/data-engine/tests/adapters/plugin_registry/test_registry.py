import pytest
from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.plugin_api import FormatManifest, DetectResult


class _FakeCsv:
    manifest = FormatManifest(
        id="csv", display_name="CSV", version="1.0.0",
        license="Apache-2.0", author="x",
        mime_types=["text/csv"], extensions=[".csv"],
        shape="tabular", parse=True, emit=True, streaming=True,
    )
    def detect(self, sample): return DetectResult(format="csv", confidence=0.9)
    def parse(self, src): raise NotImplementedError
    def emit(self, data, sink): raise NotImplementedError


def test_register_and_lookup_format():
    r = PluginRegistry()
    p = _FakeCsv()
    r.register_format(p)
    assert r.get_format("csv") is p
    assert "csv" in r.list_formats()


def test_disabled_plugins_skip(monkeypatch):
    monkeypatch.setenv("FILTERNARRANGE_DISABLED_PLUGINS", "csv,parquet")
    r = PluginRegistry()
    assert r.is_disabled("csv")
    assert not r.is_disabled("json")


def test_missing_format_raises():
    r = PluginRegistry()
    with pytest.raises(KeyError):
        r.get_format("xml")
