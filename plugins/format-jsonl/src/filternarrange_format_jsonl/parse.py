"""JSONL parsing — union schema, dict-shaped rows."""
from __future__ import annotations
import json
from typing import AsyncIterator, BinaryIO

from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.inference import infer_type_tag


def parse(source: BinaryIO) -> TabularData:
    raw = source.read().decode("utf-8", errors="replace")
    sample_objs: list[dict] = []
    all_lines: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        all_lines.append(ln)
        if len(sample_objs) < 200:
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                sample_objs.append(obj)

    keys: list[str] = []
    seen: set[str] = set()
    for obj in sample_objs:
        for k in obj.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    schema = [
        Column(
            name=k,
            type=infer_type_tag([o[k] for o in sample_objs if k in o and o[k] is not None]),
            nullable=True,
        )
        for k in keys
    ]
    rows = [json.loads(ln) for ln in all_lines]
    return TabularData(schema=schema, rows=_aiter(rows), meta={"row_count": len(rows)})


async def _aiter(items) -> AsyncIterator[dict]:
    for r in items:
        yield r


__all__ = ["parse"]
