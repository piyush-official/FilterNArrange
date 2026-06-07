import pathlib
import pytest
from filternarrange_format_tsv import plugin


@pytest.mark.asyncio
async def test_parse_sample():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.tsv", "rb") as f:
        td = plugin.parse(f)
    assert [c.name for c in td.schema] == ["id", "name", "age"]
    rows = [r async for r in td.rows]
    assert len(rows) == 3
    assert rows[0] == {"id": "1", "name": "Ada", "age": "37"}
