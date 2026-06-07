"""Async Kafka consumer with JSON-Schema-on-read (Plan D §3).

Plan D creates two consumer groups — ``python-worker-paid`` and
``python-worker-free`` — both consuming ``topic.v1.jobs``. Tier-aware routing
lands in Plan F; for now the groups behave identically and the free group is
the default in dev compose.
"""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from typing import Any, Awaitable, Callable, Mapping

from aiokafka import AIOKafkaConsumer

from filternarrange_engine.adapters.kafka.schema_validator import (
    SchemaValidator,
    SchemaValidationError,
)
from filternarrange_engine.adapters.kafka.topics import JOBS

log = logging.getLogger(__name__)
CONTRACTS = pathlib.Path(__file__).resolve().parents[6] / "contracts" / "kafka"

Handler = Callable[[Mapping[str, Any]], Awaitable[None]]


class JobConsumer:
    """Consumes ``topic.v1.jobs`` for one consumer group."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        handler: Handler,
        validator: SchemaValidator | None = None,
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._group_id = group_id
        self._handler = handler
        self._validator = validator or SchemaValidator(CONTRACTS)
        self._consumer: AIOKafkaConsumer | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            JOBS,
            bootstrap_servers=self._bootstrap,
            group_id=self._group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            request_timeout_ms=10_000,
        )
        await self._consumer.start()

    async def stop(self) -> None:
        self._stop.set()
        if self._consumer:
            await self._consumer.stop()

    async def run(self) -> None:
        assert self._consumer is not None, "Call start() first"
        try:
            async for record in self._consumer:
                if self._stop.is_set():
                    break
                try:
                    await self._dispatch(record.value.decode("utf-8"))
                except Exception as e:
                    log.error(
                        "Handler crashed on offset %s: %s — ack & continue",
                        record.offset, e,
                    )
                # Always commit. The producer is idempotent and the handler
                # checks job-status (queued|cancelled) to dedupe on its side.
                await self._consumer.commit()
        finally:
            await self._consumer.stop()

    async def _dispatch(self, raw_value: str) -> None:
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError as e:
            log.warning("Dropping non-JSON message: %s", e)
            return
        try:
            self._validator.validate(JOBS, payload)
        except SchemaValidationError as e:
            log.warning("Dropping schema-invalid message: %s", e)
            return
        await self._handler(payload)
