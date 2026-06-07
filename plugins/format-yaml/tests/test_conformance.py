"""YAML is a tree-shaped plugin: the shared format-conformance helper
asserts schema parity which only applies to tabular plugins. We still
exercise a detect/parse/emit/re-parse roundtrip here."""
import io
import pathlib
import yaml
from filternarrange_format_yaml import plugin


def test_roundtrip_conformance():
    fixture = pathlib.Path(__file__).parent / "fixtures/sample.yaml"
    raw = fixture.read_bytes()
    det = plugin.detect(raw[:65536])
    assert det.format == plugin.manifest.id
    assert det.confidence > 0.0

    td = plugin.parse(io.BytesIO(raw))
    sink = io.BytesIO()
    plugin.emit(td, sink)
    out = sink.getvalue()
    assert out

    re_obj = yaml.safe_load(io.BytesIO(out).read().decode())
    orig_obj = yaml.safe_load(raw.decode())
    assert re_obj == orig_obj
