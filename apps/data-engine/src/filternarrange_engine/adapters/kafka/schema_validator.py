"""JSON-Schema validation for Kafka messages (Plan D §3, §6).

Schemas declare ``$schema: draft/2019-09``; we pin the validator to the matching
draft so silent acceptance (the everit / draft-07 trap we hit on the Java side)
can't happen here.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Mapping

import jsonschema
from jsonschema import Draft201909Validator


class SchemaValidationError(ValueError):
    """Raised when a Kafka message does not conform to its v1 contract."""


class SchemaValidator:
    """Loads, caches, and validates against ``contracts/kafka/*.schema.json``.

    The validator is process-wide; load once and share across producers and
    consumers. ``validate`` raises :class:`SchemaValidationError` so consumer
    loops can ack-and-skip without crashing.
    """

    _FILE_FOR_TOPIC = {
        "topic.v1.jobs":            "topic.v1.jobs.schema.json",
        "topic.v1.job-results":     "topic.v1.job-results.schema.json",
        "topic.v1.audit-events":    "topic.v1.audit-events.schema.json",
        "topic.v1.format-requests": "topic.v1.format-requests.schema.json",
    }

    def __init__(self, contracts_dir: pathlib.Path) -> None:
        self._contracts_dir = contracts_dir
        self._cache: dict[str, Draft201909Validator] = {}

    def validate(self, topic: str, payload: Mapping[str, Any]) -> None:
        v = self._cache.get(topic)
        if v is None:
            fname = self._FILE_FOR_TOPIC.get(topic)
            if fname is None:
                raise SchemaValidationError(f"Unknown topic: {topic}")
            schema = json.loads((self._contracts_dir / fname).read_text())
            v = Draft201909Validator(schema)
            self._cache[topic] = v
        try:
            v.validate(payload)
        except jsonschema.ValidationError as e:
            raise SchemaValidationError(
                f"{topic}: {e.message} (at /{'/'.join(map(str, e.absolute_path))})"
            ) from e
