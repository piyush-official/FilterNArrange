import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.filter_spec import ExpressionSpec
from filternarrange_engine.core.types import TypeTag
from filternarrange_filter_expression import plugin


async def _aiter(items):
    for r in items:
        yield r


def _make(rows):
    return TabularData(
        schema=[
            Column("id", TypeTag.INTEGER, False),
            Column("name", TypeTag.STRING, False),
            Column("age", TypeTag.INTEGER, True),
            Column("country", TypeTag.STRING, True),
        ],
        rows=_aiter(rows),
    )


@pytest.mark.asyncio
async def test_and():
    td = _make([
        {"id": 1, "name": "Ada",  "age": 37, "country": "UK"},
        {"id": 2, "name": "Grace", "age": 85, "country": "US"},
        {"id": 3, "name": "Kid",  "age": 10, "country": "IN"},
    ])
    out = plugin.apply(td, ExpressionSpec(expr="age > 18 AND country = 'UK'"))
    rows = [r async for r in out.rows]
    assert [r["name"] for r in rows] == ["Ada"]


@pytest.mark.asyncio
async def test_or_not():
    td = _make([
        {"id": 1, "name": "Ada",  "age": 37, "country": "UK"},
        {"id": 2, "name": "Grace", "age": 85, "country": "US"},
    ])
    out = plugin.apply(td, ExpressionSpec(expr="NOT (country = 'US') OR age > 80"))
    rows = [r async for r in out.rows]
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_register_function():
    plugin.register_function("double", lambda x: x * 2, "int -> int")
    td = _make([
        {"id": 1, "name": "Ada",  "age": 37, "country": "UK"},
        {"id": 2, "name": "Grace", "age": 85, "country": "US"},
    ])
    out = plugin.apply(td, ExpressionSpec(expr="double(age) > 100"))
    rows = [r async for r in out.rows]
    assert [r["name"] for r in rows] == ["Grace"]


def test_validate_syntax():
    errs = plugin.validate(ExpressionSpec(expr="age > "))
    assert errs
