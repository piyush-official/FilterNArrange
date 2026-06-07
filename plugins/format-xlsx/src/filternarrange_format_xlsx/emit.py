"""XLSX emit — single-sheet workbook from TabularData."""
from __future__ import annotations
import asyncio
from typing import BinaryIO

from openpyxl import Workbook

from filternarrange_engine.core.canonical import TabularData


def emit(data: TabularData, sink: BinaryIO) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    columns = [c.name for c in data.schema]
    ws.append(columns)

    async def collect() -> list[dict]:
        return [r async for r in data.rows]

    rows = asyncio.new_event_loop().run_until_complete(collect())
    for r in rows:
        ws.append([r.get(c) for c in columns])
    wb.save(sink)


__all__ = ["emit"]
