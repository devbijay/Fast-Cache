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
