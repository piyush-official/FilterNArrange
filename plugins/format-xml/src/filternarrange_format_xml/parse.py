"""XML parse → TreeData via lxml.etree (safe parser)."""
from __future__ import annotations
from typing import BinaryIO

from lxml import etree

from filternarrange_engine.core.canonical import Node, TreeData
from filternarrange_engine.core.inference import value_to_type_tag
from filternarrange_engine.core.types import TypeTag


def _to_node(elem) -> Node:
    children: list[Node] = []
    if elem.attrib:
        for k, v in elem.attrib.items():
            children.append(Node(key=f"@{k}", value=v, type=TypeTag.STRING, children=[]))
    for ch in elem:
        children.append(_to_node(ch))
    text = (elem.text or "").strip() if elem.text else ""
    if children:
        if text:
            children.insert(0, Node(key="#text", value=text, type=TypeTag.STRING, children=[]))
        return Node(key=elem.tag, value=None, type=TypeTag.NULL, children=children)
    return Node(
        key=elem.tag,
        value=text or None,
        type=value_to_type_tag(text or None),
        children=[],
    )


def parse(source: BinaryIO) -> TreeData:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    tree = etree.parse(source, parser)
    return TreeData(root=_to_node(tree.getroot()), meta={"parser": "lxml.safe"})


__all__ = ["parse"]
