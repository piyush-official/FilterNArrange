import pytest
from filternarrange_engine.core.analysis import AnalysisSpec
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_analysis_group_by import plugin


async def _aiter(items):
    for r in items:
        yield r


def _make(rows):
    return TabularData(
        schema=[
            Column("country", TypeTag.STRING, False),
            Column("amount", TypeTag.NUMBER, False),
        ],
        rows=_aiter(rows),
    )


@pytest.mark.asyncio
async def test_group_sum_count():
    td = _make([
        {"country": "IN", "amount": 10.0},
        {"country": "US", "amount": 5.0},
        {"country": "IN", "amount": 2.0},
        {"country": "US", "amount": 7.0},
    ])
    res = await plugin.analyze(td, {"by": ["country"], "agg": {"amount": ["sum", "count", "avg"]}})
    groups = {g["country"]: g for g in res.payload["groups"]}
    assert groups["IN"]["amount_sum"] == 12.0
    assert groups["IN"]["amount_count"] == 2
    assert groups["US"]["amount_avg"] == 6.0


def test_validate_unknown_col():
    schema = [Column("a", TypeTag.NUMBER, False)]
    errs = plugin.validate(
        AnalysisSpec(kind="group_by", options={"by": ["nope"], "agg": {}}),
        schema=schema,
    )
    assert errs and "unknown column" in errs[0].lower()
