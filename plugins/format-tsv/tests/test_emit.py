import io
import pathlib
from filternarrange_format_tsv import plugin


def test_roundtrip():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.tsv", "rb") as f:
        td = plugin.parse(f)
    sink = io.BytesIO()
    plugin.emit(td, sink)
    out = sink.getvalue().decode()
    assert "id\tname\tage" in out
    assert "Ada" in out
