import io
import pytest
from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_format_json.parse import parse_json


@pytest.mark.asyncio
async def test_array_becomes_tabular(people_json):
    data = parse_json(io.BytesIO(people_json))
    assert isinstance(data, TabularData)
    names = [c.name for c in data.schema]
    assert "name" in names and "age" in names
    rows = [r async for r in data.rows]
    assert len(rows) == 2


def test_object_becomes_tree(nested_json):
    data = parse_json(io.BytesIO(nested_json))
    assert isinstance(data, TreeData)
    assert data.root.key == "$"
    keys = [c.key for c in data.root.children]
    assert "company" in keys and "departments" in keys
