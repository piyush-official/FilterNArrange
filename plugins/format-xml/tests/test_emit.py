import io
import pathlib
from lxml import etree
from filternarrange_format_xml import plugin


def test_roundtrip():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.xml", "rb") as f:
        td = plugin.parse(f)
    sink = io.BytesIO()
    plugin.emit(td, sink)
    out = sink.getvalue()
    root = etree.fromstring(out)
    assert root.tag == "people"
    assert len(root.findall("person")) == 2
