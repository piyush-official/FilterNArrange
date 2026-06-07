"""Auto-discovered plugin conformance suite (Plan C T21).

For each entry-point-registered format plugin we run the canonical
detect→parse→emit→reparse roundtrip from
``filternarrange_engine.testing.conformance``. We also assert that the
expected filter and analysis kinds are discoverable.

The suite is collected by pytest from any process that has the plugin
packages installed (CI's `plugin-tests` matrix or the `conformance` job).
"""
from __future__ import annotations
import pathlib
import pytest
from importlib.metadata import entry_points

PLUGINS_ROOT = pathlib.Path(__file__).resolve().parents[2] / "plugins"

# Map plugin id → fixture relative path under plugins/.
FIXTURES: dict[str, str] = {
    "csv":   "format-csv/tests/fixtures/people.csv",
    "tsv":   "format-tsv/tests/fixtures/sample.tsv",
    "json":  "format-json/tests/fixtures/people.json",
    "jsonl": "format-jsonl/tests/fixtures/sample.jsonl",
    "xml":   "format-xml/tests/fixtures/sample.xml",
    "yaml":  "format-yaml/tests/fixtures/sample.yaml",
    "xlsx":  "format-xlsx/tests/fixtures/two_sheets.xlsx",
}


def _registered_format_plugin(fmt: str):
    for ep in entry_points(group="filternarrange.formats"):
        if ep.name == fmt:
            return ep.load()
    return None


@pytest.mark.parametrize("fmt", list(FIXTURES))
def test_format_plugin_roundtrip(fmt: str) -> None:
    plugin = _registered_format_plugin(fmt)
    if plugin is None:
        pytest.skip(f"{fmt!r} not registered as a filternarrange.formats entry-point")
    fixture = PLUGINS_ROOT / FIXTURES[fmt]
    if not fixture.exists():
        pytest.skip(f"fixture missing at {fixture}")
    from filternarrange_engine.testing.conformance import run_format_conformance
    run_format_conformance(plugin, fixture)


def test_all_filter_kinds_registered() -> None:
    eps = {ep.name for ep in entry_points(group="filternarrange.filters")}
    assert {"column", "row", "expression", "regex"} <= eps, eps


def test_all_analyses_registered() -> None:
    eps = {ep.name for ep in entry_points(group="filternarrange.analyses")}
    assert {"summary_stats", "group_by", "chart_suggest", "schema_infer"} <= eps, eps
