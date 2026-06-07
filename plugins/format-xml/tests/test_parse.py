import pathlib
from filternarrange_engine.core.canonical import TreeData
from filternarrange_format_xml import plugin


def test_parse_sample():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.xml", "rb") as f:
        td = plugin.parse(f)
    assert isinstance(td, TreeData)
    assert td.root.key == "people"
    person_keys = [c.key for c in td.root.children]
    assert person_keys.count("person") == 2
