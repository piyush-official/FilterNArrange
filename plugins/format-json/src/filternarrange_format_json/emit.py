"""Emit TabularData (or TreeData) as JSON."""
from __future__ import annotations
import asyncio
import json
from typing import BinaryIO, Union

from filternarrange_engine.core.canonical import TabularData, TreeData, Node


def emit_json(data: Union[TabularData, TreeData], sink: BinaryIO) -> None:
    if isinstance(data, TabularData):
        rows = _drain(data)
        sink.write(json.dumps(rows, default=_default).encode("utf-8"))
    else:
        sink.write(json.dumps(_node_to_obj(data.root), default=_default).encode("utf-8"))


def _drain(data: TabularData) -> list[dict]:
    loop = asyncio.new_event_loop()
    try:
        async def collect():
            return [r async for r in data.rows]
        return loop.run_until_complete(collect())
    finally:
        loop.close()


def _node_to_obj(n: Node):
    if not n.children:
        return n.value
    if all(c.key.startswith("[") for c in n.children):
        return [_node_to_obj(c) for c in n.children]
    return {c.key: _node_to_obj(c) for c in n.children}


def _default(o):
    try:
        return str(o)
    except Exception:
        return None


__all__ = ["emit_json"]
