import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.filter_spec import RowPredicate, RowSpec
from filternarrange_engine.core.types import TypeTag
from filternarrange_filter_row import plugin


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
async def test_gt():
    td = _make([
        {"id": 1, "name": "Ada",  "age": 37},
        {"id": 2, "name": "Grace", "age": 85},
        {"id": 3, "name": "Kid",  "age": 10},
    ])
    out = plugin.apply(td, RowSpec(predicate=RowPredicate(col="age", op="gt", value=18)))
    rows = [r async for r in out.rows]
    assert [r["id"] for r in rows] == [1, 2]


@pytest.mark.asyncio
async def test_contains():
    td = _make([
        {"id": 1, "name": "Ada", "age": 37},
        {"id": 2, "name": "Grace Hopper", "age": 85},
    ])
    out = plugin.apply(td, RowSpec(predicate=RowPredicate(col="name", op="contains", value="Hopper")))
    rows = [r async for r in out.rows]
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_is_null():
    td = _make([
        {"id": 1, "name": "Ada", "age": 37},
        {"id": 2, "name": "Grace", "age": None},
    ])
    out = plugin.apply(td, RowSpec(predicate=RowPredicate(col="age", op="is_null")))
    rows = [r async for r in out.rows]
    assert len(rows) == 1 and rows[0]["name"] == "Grace"


def test_validate_unknown_column():
    schema = [Column("age", TypeTag.INTEGER, False)]
    errors = plugin.validate(
        RowSpec(predicate=RowPredicate(col="nope", op="eq", value=1)),
        schema=schema,
    )
    assert errors and "unknown column" in errors[0].lower()
