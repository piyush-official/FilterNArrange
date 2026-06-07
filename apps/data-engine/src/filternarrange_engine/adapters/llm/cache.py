"""Redis-backed cache for AI capability outputs (Plan E §5).

Cache hits make subsequent identical capability requests skip the LLM call
entirely. Key derivation is canonical (sorted keys + compact separators) so
semantically-equal payloads collide; values are JSON-serialized dicts.

Redis failures never break the request path — both ``get`` and ``set``
swallow exceptions and log a warning. The cache is best-effort by design.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Mapping, Protocol


_log = logging.getLogger(__name__)


class _AsyncRedis(Protocol):
    async def get(self, key: str) -> str | bytes | None: ...
    async def set(self, key: str, value: str, *, ex: int | None = None) -> Any: ...


def canonical_hash(payload: Mapping[str, Any]) -> str:
    """Canonical, key-sorted JSON serialization hashed with SHA-256."""
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AiCache:
    def __init__(self, *, redis: _AsyncRedis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _key(self, capability: str, payload: Mapping[str, Any]) -> str:
        return f"py:cache:ai:{capability}:{canonical_hash(payload)}"

    async def get(
        self, capability: str, payload: Mapping[str, Any]
    ) -> dict | None:
        try:
            raw = await self._redis.get(self._key(capability, payload))
        except Exception as exc:
            _log.warning("redis get failed: %s", exc)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(
        self,
        capability: str,
        payload: Mapping[str, Any],
        value: Mapping[str, Any],
    ) -> None:
        try:
            await self._redis.set(
                self._key(capability, payload),
                json.dumps(value),
                ex=self._ttl,
            )
        except Exception as exc:
            _log.warning("redis set failed: %s", exc)


__all__ = ["AiCache", "canonical_hash"]
