import io
import pytest
from filternarrange_engine.core.types import TypeTag
from filternarrange_format_csv.parse import parse_csv


@pytest.mark.asyncio
async def test_parse_infers_columns_and_streams_rows(people_csv_bytes):
    data = parse_csv(io.BytesIO(people_csv_bytes))
    names = [c.name for c in data.schema]
    assert names == ["name", "age", "active"]
    assert data.schema[1].type is TypeTag.INTEGER
    rows = [r async for r in data.rows]
    assert rows[0]["name"] == "Alice"
    assert rows[1]["age"] == "25"
