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
