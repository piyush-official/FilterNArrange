"""YAML parse → TreeData via PyYAML safe_load."""
from __future__ import annotations
from typing import Any, BinaryIO

import yaml

from filternarrange_engine.core.canonical import Node, TreeData
from filternarrange_engine.core.inference import value_to_type_tag
from filternarrange_engine.core.types import TypeTag


def _to_node(key: str, val: Any) -> Node:
    if isinstance(val, dict):
        return Node(
            key=key, value=None, type=TypeTag.NULL,
            children=[_to_node(k, v) for k, v in val.items()],
        )
    if isinstance(val, list):
        return Node(
            key=key, value=None, type=TypeTag.NULL,
            children=[_to_node(str(i), v) for i, v in enumerate(val)],
        )
    return Node(key=key, value=val, type=value_to_type_tag(val), children=[])


def parse(source: BinaryIO) -> TreeData:
    raw = source.read().decode("utf-8")
    doc = yaml.safe_load(raw)
    root = _to_node("$", doc if doc is not None else {})
    return TreeData(root=root, meta={"loader": "PyYAML.safe"})


__all__ = ["parse"]
