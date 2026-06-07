import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_filter_column.plugin import plugin as filter_plugin


async def _rows(items):
    for r in items: yield r


@pytest.mark.asyncio
async def test_apply_keeps_only_listed_columns():
    data = TabularData(
        schema=[
            Column("name", TypeTag.STRING, False),
            Column("age", TypeTag.INTEGER, True),
            Column("email", TypeTag.STRING, True),
        ],
        rows=_rows([
            {"name": "A", "age": 1, "email": "a@x"},
            {"name": "B", "age": 2, "email": "b@x"},
        ]),
        meta={},
    )
    out = filter_plugin.apply(data, {"kind": "column", "keep": ["name", "age"]})
    assert [c.name for c in out.schema] == ["name", "age"]
    rows = [r async for r in out.rows]
    assert rows == [{"name": "A", "age": 1}, {"name": "B", "age": 2}]


def test_explain():
    spec = {"kind": "column", "keep": ["a", "b"]}
    text = filter_plugin.explain(spec)
    assert "keep" in text.lower()
    assert "a" in text and "b" in text
