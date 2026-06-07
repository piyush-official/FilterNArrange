import io
import pathlib
import yaml
from filternarrange_format_yaml import plugin


def test_roundtrip():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.yaml", "rb") as f:
        td = plugin.parse(f)
    sink = io.BytesIO()
    plugin.emit(td, sink)
    obj = yaml.safe_load(sink.getvalue().decode())
    assert obj["name"] == "Ada"
    assert obj["languages"] == ["python", "ada"]
