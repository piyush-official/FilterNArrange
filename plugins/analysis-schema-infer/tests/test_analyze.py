import pytest
from filternarrange_engine.core.canonical import Node, TreeData
from filternarrange_engine.core.types import TypeTag
from filternarrange_analysis_schema_infer import plugin


@pytest.mark.asyncio
async def test_infer_paths_and_depth():
    root = Node(key="$", value=None, type=TypeTag.NULL, children=[
        Node(key="name", value="Ada", type=TypeTag.STRING, children=[]),
        Node(key="addr", value=None, type=TypeTag.NULL, children=[
            Node(key="city", value="London", type=TypeTag.STRING, children=[]),
        ]),
    ])
    td = TreeData(root=root, meta={})
    res = await plugin.analyze(td, {})
    paths = {p["path"]: p for p in res.payload["paths"]}
    assert "$.name" in paths
    assert "$.addr.city" in paths
    assert paths["$.name"]["types"] == ["string"]
    assert res.payload["depth"] == 3
    assert res.payload["leaf_count"] == 2
