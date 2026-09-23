import math
import uuid
from datetime import timezone
from unittest.mock import patch

import pytest
import asyncio
import time

import pytest_asyncio

from fast_cache import MongoDBBackend


@pytest_asyncio.fixture
async def cache(mongo_url):
    unique_namespace = f"my_cache_{uuid.uuid4().hex[:8]}"
    backend = MongoDBBackend(mongo_url, namespace=unique_namespace)
    await backend.aclear()
    yield backend
    await backend.aclear()
    await backend.aclose()


# ---- SYNC TESTS ----
def test_set_and_get(cache):
    cache.set("foo", "bar")
    assert cache.get("foo") == "bar"


def test_delete(cache):
    cache.set("foo", "bar")
    cache.delete("foo")
    assert cache.get("foo") is None


def test_clear(cache):
    cache.set("foo", "bar")
    cache.set("baz", "qux")
    cache.clear()
    assert cache.get("foo") is None
    assert cache.get("baz") is None


def test_has(cache):
    cache.set("foo", "bar")
    assert cache.has("foo")
    cache.delete("foo")
    assert not cache.has("foo")


def test_expire(cache):
    cache.set("foo", "bar", expire=1)
    assert cache.get("foo") == "bar"
    time.sleep(1.1)
    assert cache.get("foo") is None


def test_expire_keeps_sub_second_precision(cache):
    """An entry set late in a second stays valid for its full expire duration."""
    now = math.floor(time.time()) + 0.9
    with patch("fast_cache.backends.mongodb.time") as mock_time:
        mock_time.time.return_value = now
        cache.set("foo", "bar", expire=1)

        mock_time.time.return_value = now + 0.5
        assert cache.has("foo")
        assert cache.get("foo") == "bar"

        mock_time.time.return_value = now + 1.01
        assert cache.get("foo") is None


def test_expire_stores_ttl_date(cache):
    cache.set("foo", "bar", expire=60)
    doc = cache._sync_collection.find_one({"_id": cache._make_key("foo")})
    expires_at_date = doc["expires_at_date"].replace(tzinfo=timezone.utc)
    assert expires_at_date.timestamp() == pytest.approx(doc["expires_at"], abs=0.001)


def test_ttl_monitor_removes_expired_documents(cache):
    """MongoDB's TTL monitor deletes expired entries from the collection."""
    admin = cache._sync_client.admin
    admin.command("setParameter", 1, ttlMonitorSleepSecs=1)
    try:
        cache.set("foo", "bar", expire=1)
        key = cache._make_key("foo")
        deadline = time.monotonic() + 10
        while cache._sync_collection.find_one({"_id": key}) is not None:
            assert time.monotonic() < deadline, "expired document was not removed"
            time.sleep(0.5)
    finally:
        admin.command("setParameter", 1, ttlMonitorSleepSecs=60)


def test_set_without_expire_clears_previous_expiration(cache):
    cache.set("foo", "bar", expire=1)
    cache.set("foo", "baz")
    doc = cache._sync_collection.find_one({"_id": cache._make_key("foo")})
    assert "expires_at" not in doc
    assert "expires_at_date" not in doc
    time.sleep(1.1)
    assert cache.get("foo") == "baz"


# ---- ASYNC TESTS ----
@pytest.mark.asyncio
async def test_async_set_and_get(cache):
    await cache.aset("foo", "bar")
    assert await cache.aget("foo") == "bar"


@pytest.mark.asyncio
async def test_async_delete(cache):
    await cache.aset("foo", "bar")
    await cache.adelete("foo")
    assert await cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_clear(cache):
    await cache.aset("foo", "bar")
    await cache.aset("baz", "qux")
    await cache.aclear()
    assert await cache.aget("foo") is None
    assert await cache.aget("baz") is None


@pytest.mark.asyncio
async def test_async_has(cache):
    await cache.aset("foo", "bar")
    assert await cache.ahas("foo")
    await cache.adelete("foo")
    assert not await cache.ahas("foo")


@pytest.mark.asyncio
async def test_async_expire(cache):
    await cache.aset("foo", "bar", expire=1)
    assert await cache.aget("foo") == "bar"
    await asyncio.sleep(1.1)
    assert await cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_expire_keeps_sub_second_precision(cache):
    """An entry set late in a second stays valid for its full expire duration."""
    now = math.floor(time.time()) + 0.9
    with patch("fast_cache.backends.mongodb.time") as mock_time:
        mock_time.time.return_value = now
        await cache.aset("foo", "bar", expire=1)

        mock_time.time.return_value = now + 0.5
        assert await cache.ahas("foo")
        assert await cache.aget("foo") == "bar"

        mock_time.time.return_value = now + 1.01
        assert await cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_expire_stores_ttl_date(cache):
    await cache.aset("foo", "bar", expire=60)
    doc = await cache._async_collection.find_one({"_id": cache._make_key("foo")})
    expires_at_date = doc["expires_at_date"].replace(tzinfo=timezone.utc)
    assert expires_at_date.timestamp() == pytest.approx(doc["expires_at"], abs=0.001)


@pytest.mark.asyncio
async def test_async_set_without_expire_clears_previous_expiration(cache):
    await cache.aset("foo", "bar", expire=1)
    await cache.aset("foo", "baz")
    doc = await cache._async_collection.find_one({"_id": cache._make_key("foo")})
    assert "expires_at" not in doc
    assert "expires_at_date" not in doc
    await asyncio.sleep(1.1)
    assert await cache.aget("foo") == "baz"


# ---- DEFAULT PARAMETER TESTS ----
def test_get_default_parameter(cache):
    """get() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert cache.get("nonexistent", default=sentinel) is sentinel
    assert cache.get("nonexistent") is None
    cache.set("null_key", None)
    assert cache.get("null_key", default=sentinel) is None


@pytest.mark.asyncio
async def test_aget_default_parameter(cache):
    """aget() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert await cache.aget("nonexistent", default=sentinel) is sentinel
    assert await cache.aget("nonexistent") is None
    await cache.aset("null_key", None)
    assert await cache.aget("null_key", default=sentinel) is None
