"""TSV parsing into TabularData with row dicts keyed by column name."""
from __future__ import annotations
import csv
import io
from typing import AsyncIterator, BinaryIO

from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.inference import infer_type_tag


def parse(source: BinaryIO) -> TabularData:
    raw = source.read()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    rows_list = list(reader)
    if not rows_list:
        return TabularData(schema=[], rows=_aiter([]), meta={"row_count": 0})

    header = rows_list[0]
    body = rows_list[1:]
    types = [
        infer_type_tag([r[i] for r in body[:200] if i < len(r)])
        for i in range(len(header))
    ]
    schema = [Column(name=h, type=t, nullable=True) for h, t in zip(header, types)]
    dicts = [dict(zip(header, r)) for r in body]
    return TabularData(schema=schema, rows=_aiter(dicts), meta={"row_count": len(dicts)})


async def _aiter(items) -> AsyncIterator[dict]:
    for r in items:
        yield r


__all__ = ["parse"]
