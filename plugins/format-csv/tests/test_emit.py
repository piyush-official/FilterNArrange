import io
import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_format_csv.emit import emit_csv


async def _rows(items):
    for r in items: yield r


def test_emit_writes_csv():
    data = TabularData(
        schema=[Column("name", TypeTag.STRING, False), Column("age", TypeTag.INTEGER, True)],
        rows=_rows([{"name": "A", "age": "1"}, {"name": "B", "age": "2"}]),
        meta={},
    )
    buf = io.BytesIO()
    emit_csv(data, buf)
    text = buf.getvalue().decode()
    assert text.splitlines()[0] == "name,age"
    assert "A,1" in text
    assert "B,2" in text
