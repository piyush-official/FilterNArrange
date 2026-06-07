import json

import pytest
from unittest.mock import AsyncMock

from filternarrange_engine.adapters.llm.cache import AiCache, canonical_hash


def test_canonical_hash_stable_across_key_order():
    a = {"x": 1, "y": [3, 2], "z": {"b": 2, "a": 1}}
    b = {"z": {"a": 1, "b": 2}, "y": [3, 2], "x": 1}
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_differs_on_value_change():
    assert canonical_hash({"x": 1}) != canonical_hash({"x": 2})


@pytest.mark.asyncio
async def test_get_returns_parsed_value():
    redis = AsyncMock()
    redis.get.return_value = json.dumps({"foo": "bar"})
    c = AiCache(redis=redis, ttl_seconds=3600)
    out = await c.get("auto_summary", {"k": 1})
    assert out == {"foo": "bar"}
    expected_key = f"py:cache:ai:auto_summary:{canonical_hash({'k': 1})}"
    redis.get.assert_awaited_with(expected_key)


@pytest.mark.asyncio
async def test_get_returns_none_when_missing():
    redis = AsyncMock()
    redis.get.return_value = None
    c = AiCache(redis=redis, ttl_seconds=3600)
    assert await c.get("x", {"k": 1}) is None


@pytest.mark.asyncio
async def test_set_writes_with_ttl():
    redis = AsyncMock()
    c = AiCache(redis=redis, ttl_seconds=3600)
    await c.set("auto_summary", {"k": 1}, {"v": 2})
    expected_key = f"py:cache:ai:auto_summary:{canonical_hash({'k': 1})}"
    redis.set.assert_awaited_with(expected_key, json.dumps({"v": 2}), ex=3600)


@pytest.mark.asyncio
async def test_redis_failure_is_swallowed_get():
    redis = AsyncMock()
    redis.get.side_effect = RuntimeError("redis down")
    c = AiCache(redis=redis, ttl_seconds=3600)
    assert await c.get("x", {"k": 1}) is None


@pytest.mark.asyncio
async def test_redis_failure_is_swallowed_set():
    redis = AsyncMock()
    redis.set.side_effect = RuntimeError("redis down")
    c = AiCache(redis=redis, ttl_seconds=3600)
    await c.set("x", {"k": 1}, {"v": 2})
