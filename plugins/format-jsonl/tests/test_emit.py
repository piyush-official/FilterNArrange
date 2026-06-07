import io
import json
import pathlib
from filternarrange_format_jsonl import plugin


def test_roundtrip():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.jsonl", "rb") as f:
        td = plugin.parse(f)
    sink = io.BytesIO()
    plugin.emit(td, sink)
    lines = sink.getvalue().decode().strip().splitlines()
    assert len(lines) == 3
    first = json.loads(lines[0])
    assert first["name"] == "Ada"
