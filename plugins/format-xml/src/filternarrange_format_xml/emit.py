"""XML emit — build an lxml element tree from TreeData and pretty-print."""
from __future__ import annotations
from typing import BinaryIO

from lxml import etree

from filternarrange_engine.core.canonical import Node, TreeData


def _build(node: Node):
    tag = node.key if not node.key.startswith("@") else node.key[1:]
    elem = etree.Element(tag)
    for c in node.children:
        if c.key.startswith("@"):
            elem.set(c.key[1:], str(c.value))
        elif c.key == "#text":
            elem.text = str(c.value)
        else:
            elem.append(_build(c))
    if not node.children and node.value is not None:
        elem.text = str(node.value)
    return elem


def emit(data: TreeData, sink: BinaryIO) -> None:
    root = _build(data.root)
    sink.write(etree.tostring(root, xml_declaration=True, encoding="utf-8", pretty_print=True))


__all__ = ["emit"]
