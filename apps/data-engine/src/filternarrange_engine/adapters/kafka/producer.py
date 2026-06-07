"""Kafka producer with JSON-Schema-on-write (Plan D §3)."""
from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Mapping

from aiokafka import AIOKafkaProducer

from filternarrange_engine.adapters.kafka.schema_validator import (
    SchemaValidator,
    SchemaValidationError,
)

log = logging.getLogger(__name__)
CONTRACTS = pathlib.Path(__file__).resolve().parents[6] / "contracts" / "kafka"


class JobResultsProducer:
    """Produces ``topic.v1.job-results`` messages keyed by ``job_id`` (Plan D §5)."""

    def __init__(
        self,
        bootstrap_servers: str,
        validator: SchemaValidator | None = None,
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._validator = validator or SchemaValidator(CONTRACTS)
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            enable_idempotence=True,
            acks="all",
            request_timeout_ms=10_000,
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def send(self, topic: str, key: str, payload: Mapping[str, Any]) -> None:
        assert self._producer is not None, "Call start() first"
        try:
            self._validator.validate(topic, payload)
        except SchemaValidationError as e:
            log.error("Refusing to produce malformed message: %s", e)
            raise
        await self._producer.send_and_wait(
            topic,
            key=key.encode(),
            value=json.dumps(payload).encode("utf-8"),
        )
