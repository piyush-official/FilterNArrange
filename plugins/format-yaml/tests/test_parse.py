import pathlib
from filternarrange_engine.core.canonical import TreeData
from filternarrange_format_yaml import plugin


def test_parse_sample():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.yaml", "rb") as f:
        td = plugin.parse(f)
    assert isinstance(td, TreeData)
    assert td.root.key == "$"
    keys = [c.key for c in td.root.children]
    assert "name" in keys and "languages" in keys
