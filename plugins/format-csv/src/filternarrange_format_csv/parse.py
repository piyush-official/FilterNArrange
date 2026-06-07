"""CSV parsing into TabularData with async row iteration."""
from __future__ import annotations
import csv
import io
from typing import AsyncIterator, BinaryIO

from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag


def parse_csv(source: BinaryIO) -> TabularData:
    raw = source.read()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows_list: list[list[str]] = list(reader)
    if not rows_list:
        return TabularData(schema=[], rows=_aiter([]), meta={"row_count": 0})

    header = rows_list[0]
    body = rows_list[1:]
    schema = [Column(name=h, type=_infer_type(h, body, i), nullable=True)
              for i, h in enumerate(header)]
    dicts = [dict(zip(header, r)) for r in body]
    return TabularData(schema=schema, rows=_aiter(dicts), meta={"row_count": len(dicts)})


def _infer_type(col_name: str, body: list[list[str]], idx: int) -> TypeTag:
    values = [r[idx] for r in body if idx < len(r) and r[idx] != ""]
    if not values:
        return TypeTag.STRING
    if all(_is_int(v) for v in values):
        return TypeTag.INTEGER
    if all(_is_float(v) for v in values):
        return TypeTag.NUMBER
    if all(_is_bool(v) for v in values):
        return TypeTag.BOOLEAN
    return TypeTag.STRING


def _is_int(v: str) -> bool:
    try:
        int(v); return True
    except ValueError:
        return False


def _is_float(v: str) -> bool:
    try:
        float(v); return True
    except ValueError:
        return False


def _is_bool(v: str) -> bool:
    return v.lower() in {"true", "false", "0", "1", "yes", "no"}


async def _aiter(items):
    for it in items:
        yield it


__all__ = ["parse_csv"]
