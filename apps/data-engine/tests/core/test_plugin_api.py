import io
import pytest
from filternarrange_engine.core.types import TypeTag
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.plugin_api import (
    FormatManifest, FilterManifest, DetectResult,
    FormatPlugin, FilterPlugin, FilterSpec, PluginResult,
)


def test_format_manifest_validates():
    m = FormatManifest(
        id="csv", display_name="CSV", version="1.0.0",
        license="Apache-2.0", author="x",
        mime_types=["text/csv"], extensions=[".csv"],
        shape="tabular", parse=True, emit=True, streaming=True,
    )
    assert m.id == "csv"
    assert m.shape == "tabular"


def test_plugin_result_ok_and_error():
    ok = PluginResult.ok({"a": 1})
    assert ok.is_ok and ok.value == {"a": 1}
    err = PluginResult.error("PARSE_FAILED", "csv", "1.0.0", "bad row", "trace-1")
    assert not err.is_ok
    assert err.code == "PARSE_FAILED"
    assert err.plugin_id == "csv"


def test_filter_spec_is_dict_like():
    spec: FilterSpec = {"kind": "column", "keep": ["a"]}
    assert spec["kind"] == "column"


def test_format_plugin_protocol_is_structural():
    class DummyPlugin:
        manifest = FormatManifest(
            id="csv", display_name="CSV", version="1.0.0",
            license="Apache-2.0", author="x",
            mime_types=[], extensions=[], shape="tabular",
            parse=True, emit=True, streaming=True,
        )
        def detect(self, sample: bytes) -> DetectResult:
            return DetectResult(format="csv", confidence=0.5)
        def parse(self, source):
            raise NotImplementedError
        def emit(self, data, sink):
            raise NotImplementedError

    p: FormatPlugin = DummyPlugin()  # structural check
    assert p.manifest.id == "csv"
