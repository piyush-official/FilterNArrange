"""Audit-event publisher for the Python side."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from filternarrange_engine.adapters.kafka.producer import JobResultsProducer
from filternarrange_engine.adapters.kafka.topics import AUDIT_EVENTS


async def audit_event_publish(
    producer: JobResultsProducer,
    *,
    user_id: str | None,
    action: str,
    target: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    trace_id: str,
) -> None:
    payload: dict[str, Any] = {
        "event_id":    str(uuid.uuid4()),
        "action":      action,
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "trace_id":    trace_id,
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if target is not None:
        payload["target"] = target
    if metadata is not None:
        payload["metadata"] = dict(metadata)
    key = user_id or "system"
    await producer.send(AUDIT_EVENTS, key=key, payload=payload)
