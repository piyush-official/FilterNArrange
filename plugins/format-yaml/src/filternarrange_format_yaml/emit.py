"""YAML emit — convert TreeData back to a Python object then safe_dump."""
from __future__ import annotations
import io
from typing import Any, BinaryIO

import yaml

from filternarrange_engine.core.canonical import Node, TreeData


def _from_node(n: Node) -> Any:
    if n.children:
        keys = [c.key for c in n.children]
        if keys and all(k.isdigit() for k in keys):
            return [_from_node(c) for c in n.children]
        return {c.key: _from_node(c) for c in n.children}
    return n.value


def emit(data: TreeData, sink: BinaryIO) -> None:
    obj = _from_node(data.root)
    buf = io.StringIO()
    yaml.safe_dump(obj, buf, sort_keys=False, allow_unicode=True)
    sink.write(buf.getvalue().encode("utf-8"))


__all__ = ["emit"]
