"""Per-job heartbeat producing ``running`` messages every interval seconds (Plan D §3)."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable


class Heartbeat:
    """Background ticker that calls ``emit`` every ``interval_s`` seconds.

    The worker constructs one Heartbeat per active job and cancels it on
    terminal status. The first tick fires immediately so the WebSocket client
    sees a ``running`` envelope before the first parsing phase finishes.
    """

    def __init__(self, interval_s: float, emit: Callable[[], Awaitable[None]]) -> None:
        self._interval = interval_s
        self._emit = emit
        self._stop = asyncio.Event()

    async def run(self) -> None:
        try:
            await self._emit()
            while not self._stop.is_set():
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
                except asyncio.TimeoutError:
                    await self._emit()
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        self._stop.set()
