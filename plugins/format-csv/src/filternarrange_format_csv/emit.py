"""CSV emission from TabularData."""
from __future__ import annotations
import asyncio
import csv
import io
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData


def emit_csv(data: TabularData, sink: BinaryIO) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    columns = [c.name for c in data.schema]
    writer.writerow(columns)

    async def _drain() -> list[dict]:
        return [r async for r in data.rows]

    rows = asyncio.get_event_loop().run_until_complete(_drain()) \
        if not asyncio.get_event_loop().is_running() else _collect_sync(data)
    for r in rows:
        writer.writerow([r.get(c, "") for c in columns])
    sink.write(buf.getvalue().encode("utf-8"))


def _collect_sync(data: TabularData) -> list[dict]:
    # When already in a running loop (FastAPI), use nest_asyncio-style fallback.
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_drain(data))
    finally:
        loop.close()


async def _drain(data: TabularData) -> list[dict]:
    return [r async for r in data.rows]


__all__ = ["emit_csv"]
