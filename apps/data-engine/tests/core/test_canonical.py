# SPDX-License-Identifier: Apache-2.0
import pytest
from filternarrange_engine.core.types import TypeTag
from filternarrange_engine.core.canonical import Column, TabularData, Node, TreeData


async def _aiter(rows):
    for r in rows:
        yield r


@pytest.mark.asyncio
async def test_tabular_data_iterates_rows():
    cols = [Column("name", TypeTag.STRING, False), Column("age", TypeTag.INTEGER, True)]
    data = TabularData(schema=cols, rows=_aiter([{"name": "A", "age": 1}]), meta={})
    out = [r async for r in data.rows]
    assert out == [{"name": "A", "age": 1}]
    assert data.schema[0].name == "name"
    assert data.schema[0].type is TypeTag.STRING


def test_tree_data_holds_nodes():
    leaf = Node(key="x", value=1, type=TypeTag.INTEGER, children=[])
    root = Node(key="root", value=None, type=TypeTag.NULL, children=[leaf])
    tree = TreeData(root=root, meta={"depth": 1, "total_nodes": 2})
    assert tree.root.children[0].value == 1


def test_typetag_enum_values():
    assert {t.value for t in TypeTag} == {
        "string", "number", "integer", "boolean", "datetime", "null"
    }
