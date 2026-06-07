"""Bulkheaded execution primitives (Plan D §6).

- ``data_cpu_pool`` — ProcessPoolExecutor for CPU-heavy parsing.
- ``plugin_async`` — Semaphore for in-process plugin dispatch fan-out.
"""
from __future__ import annotations

import asyncio
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

data_cpu_pool: ProcessPoolExecutor | None = None
plugin_async: asyncio.Semaphore | None = None


def init() -> None:
    global data_cpu_pool, plugin_async
    if data_cpu_pool is None:
        ctx = multiprocessing.get_context("spawn")
        data_cpu_pool = ProcessPoolExecutor(
            max_workers=os.cpu_count() or 2,
            mp_context=ctx,
        )
    if plugin_async is None:
        plugin_async = asyncio.Semaphore(8)


def shutdown() -> None:
    global data_cpu_pool
    if data_cpu_pool is not None:
        data_cpu_pool.shutdown(wait=False, cancel_futures=True)
        data_cpu_pool = None
