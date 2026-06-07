import pathlib
from filternarrange_engine.testing.conformance import run_format_conformance
from filternarrange_format_jsonl import plugin


def test_conformance():
    run_format_conformance(plugin, pathlib.Path(__file__).parent / "fixtures/sample.jsonl")
