import pytest
import asyncio
from fast_cache import MemcachedBackend


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
    import time

    time.sleep(1.1)
    assert memcached_cache.get("foo") is None


@pytest.mark.asyncio
async def test_async_set_and_get(memcached_cache):
    await memcached_cache.aset("foo", "bar")
    assert await memcached_cache.aget("foo") == "bar"
    await memcached_cache.aclear()
    assert await memcached_cache.aget("foo") is None
