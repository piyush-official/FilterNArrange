import pathlib
import pytest
from filternarrange_format_xlsx import plugin


def test_list_sheets():
    with open(pathlib.Path(__file__).parent / "fixtures/two_sheets.xlsx", "rb") as f:
        assert plugin.list_sheets(f) == ["people", "orders"]


@pytest.mark.asyncio
async def test_parse_specific_sheet():
    with open(pathlib.Path(__file__).parent / "fixtures/two_sheets.xlsx", "rb") as f:
        td = plugin.parse(f, sheet_name="orders")
    assert [c.name for c in td.schema] == ["order_id", "total"]
    rows = [r async for r in td.rows]
    assert rows[0] == {"order_id": 1001, "total": 25.5}
