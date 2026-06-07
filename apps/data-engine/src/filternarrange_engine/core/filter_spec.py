"""Filter spec discriminated union: Column/Row/Expression/Regex.

Plan C extends Plan B's `ColumnFilterSpec` (in plugin_api.py) with three
additional kinds. The plan_api.ColumnFilterSpec remains for the v1 TypedDict
boundary; this module provides the dataclass-based domain types used by
the dispatcher and filter plugins.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal, Union

RowOp = Literal[
    "eq", "ne", "gt", "gte", "lt", "lte",
    "contains", "starts_with", "ends_with",
    "regex", "in", "not_in", "is_null", "is_not_null",
]


@dataclass(frozen=True)
class RowPredicate:
    col: str
    op: RowOp
    value: Any = None


@dataclass(frozen=True)
class ColumnSpec:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    kind: Literal["column"] = "column"


@dataclass(frozen=True)
class RowSpec:
    predicate: RowPredicate
    kind: Literal["row"] = "row"


@dataclass(frozen=True)
class ExpressionSpec:
    expr: str
    kind: Literal["expression"] = "expression"


@dataclass(frozen=True)
class RegexSpec:
    pattern: str
    flags: list[str] = field(default_factory=list)
    kind: Literal["regex"] = "regex"


FilterSpec = Union[ColumnSpec, RowSpec, ExpressionSpec, RegexSpec]


def parse_filter_spec(payload: dict) -> FilterSpec:
    kind = payload.get("kind")
    if kind == "column":
        return ColumnSpec(
            include=list(payload.get("include", [])),
            exclude=list(payload.get("exclude", [])),
        )
    if kind == "row":
        p = payload["predicate"]
        return RowSpec(predicate=RowPredicate(col=p["col"], op=p["op"], value=p.get("value")))
    if kind == "expression":
        return ExpressionSpec(expr=payload["expr"])
    if kind == "regex":
        return RegexSpec(pattern=payload["pattern"], flags=list(payload.get("flags", [])))
    raise ValueError(f"unknown filter kind: {kind!r}")


__all__ = [
    "RowOp", "RowPredicate",
    "ColumnSpec", "RowSpec", "ExpressionSpec", "RegexSpec",
    "FilterSpec", "parse_filter_spec",
]
