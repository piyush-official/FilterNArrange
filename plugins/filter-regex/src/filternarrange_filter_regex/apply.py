"""Regex search across string columns of a TabularData."""
from __future__ import annotations
import re
from typing import AsyncIterator

from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.core.filter_spec import RegexSpec
from filternarrange_engine.core.types import TypeTag


_FLAG = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


def _compile(spec: RegexSpec) -> re.Pattern:
    flags = 0
    for f in spec.flags:
        flags |= _FLAG.get(f, 0)
    return re.compile(spec.pattern, flags)


def apply(data: TabularData, spec: RegexSpec) -> TabularData:
    pat = _compile(spec)
    string_cols = [c.name for c in data.schema if c.type == TypeTag.STRING]

    async def out() -> AsyncIterator[dict]:
        async for row in data.rows:
            for name in string_cols:
                v = row.get(name)
                if v is not None and pat.search(str(v)):
                    yield row
                    break

    return TabularData(schema=data.schema, rows=out(), meta=data.meta)


__all__ = ["apply"]
