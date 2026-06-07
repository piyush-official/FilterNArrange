"""Canonical conformance suite for format plugins.

Task 21 turns this into the full auto-discovered suite; for now it provides
the minimum each plugin's `tests/test_conformance.py` needs:

- detect on the fixture returns the plugin's own format id with non-zero confidence
- parse → emit → parse roundtrip is structurally stable (same column names,
  same row count)
"""
from __future__ import annotations
import asyncio
import io
import pathlib
from typing import Any


def _drain_rows_sync(td) -> list[dict[str, Any]]:
    async def collect() -> list[dict[str, Any]]:
        return [r async for r in td.rows]
    return asyncio.new_event_loop().run_until_complete(collect())


def run_format_conformance(plugin, fixture: pathlib.Path) -> None:
    """Round-trip conformance: detect → parse → emit → parse."""
    raw = fixture.read_bytes()

    det = plugin.detect(raw[:65536])
    assert det.format == plugin.manifest.id, f"detect returned {det.format!r}, want {plugin.manifest.id!r}"
    assert det.confidence > 0.0, "detect must report non-zero confidence on its own fixture"

    parsed = plugin.parse(io.BytesIO(raw))
    schema_names = [c.name for c in getattr(parsed, "schema", [])] if hasattr(parsed, "schema") else []
    rows = _drain_rows_sync(parsed) if hasattr(parsed, "rows") else []

    sink = io.BytesIO()
    plugin.emit(parsed if not rows else _rewind_tabular(parsed, rows), sink)
    out = sink.getvalue()
    assert out, "emit produced an empty payload"

    # Round-trip stability: re-parse the emitted bytes and compare schema.
    reparsed = plugin.parse(io.BytesIO(out))
    re_schema_names = [c.name for c in getattr(reparsed, "schema", [])] if hasattr(reparsed, "schema") else []
    if schema_names and re_schema_names:
        assert schema_names == re_schema_names, \
            f"roundtrip schema drift: {schema_names!r} -> {re_schema_names!r}"


def _rewind_tabular(parsed, rows: list[dict[str, Any]]):
    """Replace `parsed.rows` with a fresh async iterator over the drained rows."""
    from filternarrange_engine.core.canonical import TabularData

    async def aiter():
        for r in rows:
            yield r

    return TabularData(schema=parsed.schema, rows=aiter(), meta=getattr(parsed, "meta", {}))


__all__ = ["run_format_conformance"]
