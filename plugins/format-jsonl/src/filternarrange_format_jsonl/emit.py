"""JSONL emit — one JSON object per line, only the declared columns."""
from __future__ import annotations
import asyncio
import json
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData


def emit(data: TabularData, sink: BinaryIO) -> None:
    keys = [c.name for c in data.schema]

    async def collect() -> list[dict]:
        return [r async for r in data.rows]

    rows = asyncio.new_event_loop().run_until_complete(collect())
    out: list[str] = []
    for r in rows:
        obj = {k: r.get(k) for k in keys}
        out.append(json.dumps(obj, ensure_ascii=False))
    sink.write(("\n".join(out) + ("\n" if out else "")).encode("utf-8"))


__all__ = ["emit"]
