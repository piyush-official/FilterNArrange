import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_analysis_summary_stats import plugin


async def _aiter(items):
    for r in items:
        yield r


def _make(rows):
    return TabularData(
        schema=[
            Column("id", TypeTag.INTEGER, False),
            Column("name", TypeTag.STRING, False),
            Column("age", TypeTag.INTEGER, True),
        ],
        rows=_aiter(rows),
    )


@pytest.mark.asyncio
async def test_summary_basics():
    td = _make([
        {"id": 1, "name": "Ada",   "age": 37},
        {"id": 2, "name": "Grace", "age": 85},
        {"id": 3, "name": "Ada",   "age": None},
    ])
    res = await plugin.analyze(td, {})
    cols = {c["name"]: c for c in res.payload["columns"]}
    assert cols["age"]["count"] == 2
    assert cols["age"]["nulls"] == 1
    assert cols["age"]["min"] == 37
    assert cols["age"]["max"] == 85
    assert cols["name"]["distinct"] == 2
    assert any(t["value"] == "Ada" and t["count"] == 2 for t in cols["name"]["top"])
