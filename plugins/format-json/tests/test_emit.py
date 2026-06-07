import io
import json
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_format_json.emit import emit_json


async def _rows(items):
    for r in items: yield r


def test_emit_tabular_writes_json_array():
    data = TabularData(
        schema=[Column("a", TypeTag.STRING, False)],
        rows=_rows([{"a": "1"}, {"a": "2"}]),
        meta={},
    )
    buf = io.BytesIO()
    emit_json(data, buf)
    parsed = json.loads(buf.getvalue())
    assert parsed == [{"a": "1"}, {"a": "2"}]
