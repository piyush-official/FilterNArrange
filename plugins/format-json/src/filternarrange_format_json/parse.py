"""Parse JSON to TabularData (array of objects) or TreeData (anything else)."""
from __future__ import annotations
import json
from typing import Any, BinaryIO, Union

from filternarrange_engine.core.canonical import Column, Node, TabularData, TreeData
from filternarrange_engine.core.types import TypeTag


def parse_json(source: BinaryIO) -> Union[TabularData, TreeData]:
    text = source.read().decode("utf-8-sig")
    obj = json.loads(text)

    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        return _to_tabular(obj)
    return _to_tree(obj)


def _to_tabular(rows: list[dict]) -> TabularData:
    columns: dict[str, TypeTag] = {}
    for r in rows:
        for k, v in r.items():
            columns.setdefault(k, _type_of(v))
    schema = [Column(name=n, type=t, nullable=True) for n, t in columns.items()]
    return TabularData(schema=schema, rows=_aiter(rows), meta={"row_count": len(rows)})


def _to_tree(value: Any, key: str = "$") -> TreeData:
    root = _node(key, value)
    return TreeData(root=root, meta={"depth": _depth(root), "total_nodes": _count(root)})


def _node(key: str, value: Any) -> Node:
    if isinstance(value, dict):
        children = [_node(k, v) for k, v in value.items()]
        return Node(key=key, value=None, type=TypeTag.NULL, children=children)
    if isinstance(value, list):
        children = [_node(f"[{i}]", v) for i, v in enumerate(value)]
        return Node(key=key, value=None, type=TypeTag.NULL, children=children)
    return Node(key=key, value=value, type=_type_of(value), children=[])


def _type_of(v: Any) -> TypeTag:
    if v is None: return TypeTag.NULL
    if isinstance(v, bool): return TypeTag.BOOLEAN
    if isinstance(v, int): return TypeTag.INTEGER
    if isinstance(v, float): return TypeTag.NUMBER
    if isinstance(v, str): return TypeTag.STRING
    return TypeTag.STRING


def _depth(n: Node) -> int:
    return 1 + max((_depth(c) for c in n.children), default=0)


def _count(n: Node) -> int:
    return 1 + sum(_count(c) for c in n.children)


async def _aiter(items):
    for it in items: yield it


__all__ = ["parse_json"]
