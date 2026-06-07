"""TSV emission from TabularData (rows are dicts keyed by column name)."""
from __future__ import annotations
import asyncio
import csv
import io
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData


def emit(data: TabularData, sink: BinaryIO) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    columns = [c.name for c in data.schema]
    writer.writerow(columns)

    async def collect() -> list[dict]:
        return [r async for r in data.rows]

    rows = asyncio.new_event_loop().run_until_complete(collect())
    for r in rows:
        writer.writerow([r.get(c, "") for c in columns])
    sink.write(buf.getvalue().encode("utf-8"))


__all__ = ["emit"]
