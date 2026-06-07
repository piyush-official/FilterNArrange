"""XML is tree-shaped; use a local roundtrip rather than the format conformance
helper (which expects tabular schema parity)."""
import io
import pathlib
from lxml import etree
from filternarrange_format_xml import plugin


def test_roundtrip_conformance():
    fixture = pathlib.Path(__file__).parent / "fixtures/sample.xml"
    raw = fixture.read_bytes()
    det = plugin.detect(raw[:65536])
    assert det.format == plugin.manifest.id
    assert det.confidence > 0.0

    td = plugin.parse(io.BytesIO(raw))
    sink = io.BytesIO()
    plugin.emit(td, sink)
    out = sink.getvalue()
    assert out

    re_root = etree.fromstring(out)
    assert re_root.tag == etree.fromstring(raw).tag
