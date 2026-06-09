import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_analysis_chart_suggest import plugin


async def _aiter(items):
    for r in items:
        yield r


@pytest.mark.asyncio
async def test_two_numerics_scatter():
    td = TabularData(
        schema=[Column("x", TypeTag.NUMBER, False), Column("y", TypeTag.NUMBER, False)],
        rows=_aiter([{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}]),
    )
    res = await plugin.analyze(td, {})
    kinds = [c["mark"] for c in res.payload["charts"]]
    assert "point" in kinds


@pytest.mark.asyncio
async def test_datetime_numeric_line():
    td = TabularData(
        schema=[Column("ts", TypeTag.DATETIME, False), Column("v", TypeTag.NUMBER, False)],
        rows=_aiter([{"ts": "2026-01-01T00:00:00Z", "v": 1.0}]),
    )
    res = await plugin.analyze(td, {})
    assert res.payload["charts"][0]["mark"] == "line"


@pytest.mark.asyncio
async def test_categorical_numeric_bar():
    td = TabularData(
        schema=[Column("c", TypeTag.STRING, False), Column("n", TypeTag.NUMBER, False)],
        rows=_aiter([{"c": "a", "n": 1}, {"c": "b", "n": 2}]),
    )
    res = await plugin.analyze(td, {})
    assert res.payload["charts"][0]["mark"] == "bar"


@pytest.mark.asyncio
async def test_bar_data_is_sum_aggregated_by_category():
    """Bar chart data must be [category, sum(numeric)] pairs so the
    frontend can render bars without a follow-up call. Previously the
    plugin emitted specs only and ChartsPanel hardcoded data: []."""
    td = TabularData(
        schema=[Column("c", TypeTag.STRING, False), Column("n", TypeTag.NUMBER, False)],
        rows=_aiter([
            {"c": "a", "n": 1},
            {"c": "b", "n": 2},
            {"c": "a", "n": 3},
        ]),
    )
    res = await plugin.analyze(td, {})
    bar = next(c for c in res.payload["charts"] if c["mark"] == "bar")
    assert sorted(bar["data"]) == [["a", 4], ["b", 2]]


@pytest.mark.asyncio
async def test_scatter_data_is_raw_xy_pairs():
    """Scatter (point) chart data is the raw (x, y) pairs in row order."""
    td = TabularData(
        schema=[Column("x", TypeTag.NUMBER, False), Column("y", TypeTag.NUMBER, False)],
        rows=_aiter([{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}]),
    )
    res = await plugin.analyze(td, {})
    scatter = next(c for c in res.payload["charts"] if c["mark"] == "point")
    assert scatter["data"] == [[1.0, 2.0], [3.0, 4.0]]


@pytest.mark.asyncio
async def test_line_data_sorted_by_temporal_axis():
    """Line chart data is (timestamp, numeric) sorted by x. Rows can
    arrive out of order; the spec is temporal-x, so order matters for
    ECharts to draw a sensible line."""
    td = TabularData(
        schema=[Column("ts", TypeTag.DATETIME, False), Column("v", TypeTag.NUMBER, False)],
        rows=_aiter([
            {"ts": "2026-01-03T00:00:00Z", "v": 3.0},
            {"ts": "2026-01-01T00:00:00Z", "v": 1.0},
            {"ts": "2026-01-02T00:00:00Z", "v": 2.0},
        ]),
    )
    res = await plugin.analyze(td, {})
    line = next(c for c in res.payload["charts"] if c["mark"] == "line")
    assert line["data"] == [
        ["2026-01-01T00:00:00Z", 1.0],
        ["2026-01-02T00:00:00Z", 2.0],
        ["2026-01-03T00:00:00Z", 3.0],
    ]


@pytest.mark.asyncio
async def test_scatter_data_capped_at_sample_limit():
    """For datasets larger than the sample limit, scatter data is
    capped — otherwise the JSON payload and the ECharts render both
    grind on very wide tables."""
    rows = [{"x": float(i), "y": float(i) * 2} for i in range(2500)]
    td = TabularData(
        schema=[Column("x", TypeTag.NUMBER, False), Column("y", TypeTag.NUMBER, False)],
        rows=_aiter(rows),
    )
    res = await plugin.analyze(td, {})
    scatter = next(c for c in res.payload["charts"] if c["mark"] == "point")
    assert len(scatter["data"]) <= 1000
