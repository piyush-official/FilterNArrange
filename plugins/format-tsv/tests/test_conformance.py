import pathlib
from filternarrange_engine.testing.conformance import run_format_conformance
from filternarrange_format_tsv import plugin


def test_conformance():
    fixture = pathlib.Path(__file__).parent / "fixtures/sample.tsv"
    run_format_conformance(plugin, fixture)
