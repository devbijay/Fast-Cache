import pytest
import asyncio
import time


# ---- SYNC TESTS ----
def test_set_and_get(memcached_cache):
    memcached_cache.set("foo", "bar")
    assert memcached_cache.get("foo") == "bar"


def test_delete(memcached_cache):
    memcached_cache.set("foo", "bar")
    memcached_cache.delete("foo")
    assert memcached_cache.get("foo") is None


def test_clear(memcached_cache):
    memcached_cache.set("foo", "bar")
    memcached_cache.set("baz", "qux")
    memcached_cache.clear()
    assert memcached_cache.get("foo") is None
    assert memcached_cache.get("baz") is None


def test_has(memcached_cache):
    memcached_cache.set("foo", "bar")
    assert memcached_cache.has("foo")
    memcached_cache.delete("foo")
    assert not memcached_cache.has("foo")


def test_expire(memcached_cache):
    memcached_cache.set("foo", "bar", expire=1)
    assert memcached_cache.get("foo") == "bar"
    time.sleep(1.1)
    assert memcached_cache.get("foo") is None


# ---- ASYNC TESTS ----
@pytest.mark.asyncio
async def test_async_set_and_get(memcached_cache):
    await memcached_cache.aset("foo", "bar")
    assert await memcached_cache.aget("foo") == "bar"


@pytest.mark.asyncio
async def test_async_delete(memcached_cache):
    await memcached_cache.aset("foo", "bar")
    await memcached_cache.adelete("foo")
    assert await memcached_cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_clear(memcached_cache):
    await memcached_cache.aset("foo", "bar")
    await memcached_cache.aset("baz", "qux")
    await memcached_cache.aclear()
    assert await memcached_cache.aget("foo") is None
    assert await memcached_cache.aget("baz") is None


@pytest.mark.asyncio
async def test_async_has(memcached_cache):
    await memcached_cache.aset("foo", "bar")
    assert await memcached_cache.ahas("foo")
    await memcached_cache.adelete("foo")
    assert not await memcached_cache.ahas("foo")


@pytest.mark.asyncio
async def test_async_expire(memcached_cache):
    await memcached_cache.aset("foo", "bar", expire=1)
    assert await memcached_cache.aget("foo") == "bar"
    await asyncio.sleep(1.1)
    assert await memcached_cache.aget("foo") is None


# ---- DEFAULT PARAMETER TESTS ----
def test_get_default_parameter(memcached_cache):
    """get() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert memcached_cache.get("nonexistent", default=sentinel) is sentinel
    assert memcached_cache.get("nonexistent") is None
    memcached_cache.set("null_key", None)
    assert memcached_cache.get("null_key", default=sentinel) is None


@pytest.mark.asyncio
async def test_aget_default_parameter(memcached_cache):
    """aget() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert await memcached_cache.aget("nonexistent", default=sentinel) is sentinel
    assert await memcached_cache.aget("nonexistent") is None
    await memcached_cache.aset("null_key", None)
    assert await memcached_cache.aget("null_key", default=sentinel) is None
