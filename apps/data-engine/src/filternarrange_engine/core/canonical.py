# SPDX-License-Identifier: Apache-2.0
"""Canonical intermediate model: TabularData and TreeData."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from .types import TypeTag


@dataclass(frozen=True)
class Column:
    name: str
    type: TypeTag
    nullable: bool


@dataclass
class TabularData:
    schema: list[Column]
    rows: AsyncIterator[dict[str, Any]]
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    key: str
    value: Any
    type: TypeTag
    children: list["Node"] = field(default_factory=list)


@dataclass
class TreeData:
    root: Node
    meta: dict[str, Any] = field(default_factory=dict)


__all__ = ["Column", "TabularData", "Node", "TreeData"]
