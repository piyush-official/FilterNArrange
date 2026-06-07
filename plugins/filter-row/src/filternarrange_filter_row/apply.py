"""Row predicate evaluation against dict-shaped rows."""
from __future__ import annotations
import re as _re
from typing import AsyncIterator

from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.core.filter_spec import RowSpec


_OPS = {
    "eq":  lambda a, b: a == b,
    "ne":  lambda a, b: a != b,
    "gt":  lambda a, b: a is not None and a >  b,
    "gte": lambda a, b: a is not None and a >= b,
    "lt":  lambda a, b: a is not None and a <  b,
    "lte": lambda a, b: a is not None and a <= b,
    "contains":    lambda a, b: a is not None and str(b) in str(a),
    "starts_with": lambda a, b: a is not None and str(a).startswith(str(b)),
    "ends_with":   lambda a, b: a is not None and str(a).endswith(str(b)),
    "regex":       lambda a, b: a is not None and bool(_re.search(str(b), str(a))),
    "in":     lambda a, b: a in (b or []),
    "not_in": lambda a, b: a not in (b or []),
    "is_null":     lambda a, _b: a is None,
    "is_not_null": lambda a, _b: a is not None,
}


def apply(data: TabularData, spec: RowSpec) -> TabularData:
    col = spec.predicate.col
    if not any(c.name == col for c in data.schema):
        raise ValueError(f"unknown column: {col!r}")
    fn = _OPS[spec.predicate.op]
    value = spec.predicate.value

    async def out() -> AsyncIterator[dict]:
        async for row in data.rows:
            if fn(row.get(col), value):
                yield row

    return TabularData(schema=data.schema, rows=out(), meta=data.meta)


__all__ = ["apply"]
