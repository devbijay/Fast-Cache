import pytest
import asyncio
from fast_cache import InMemoryBackend


def test_set_and_get(in_memory_cache):
    in_memory_cache.set("foo", "bar")
    assert in_memory_cache.get("foo") == "bar"


def test_delete(in_memory_cache):
    in_memory_cache.set("foo", "bar")
    in_memory_cache.delete("foo")
    assert in_memory_cache.get("foo") is None


def test_clear(in_memory_cache):
    in_memory_cache.set("foo", "bar")
    in_memory_cache.set("baz", "qux")
    in_memory_cache.clear()
    assert in_memory_cache.get("foo") is None
    assert in_memory_cache.get("baz") is None


def test_has(in_memory_cache):
    in_memory_cache.set("foo", "bar")
    assert in_memory_cache.has("foo")
    in_memory_cache.delete("foo")
    assert not in_memory_cache.has("foo")


def test_expire(in_memory_cache):
    in_memory_cache.set("foo", "bar", expire=1)
    assert in_memory_cache.get("foo") == "bar"
    import time

    time.sleep(1.1)
    assert in_memory_cache.get("foo") is None


def test_lru_eviction(in_memory_cache):
    in_memory_cache.set("a", 1)
    in_memory_cache.set("b", 2)
    in_memory_cache.set("c", 3)
    in_memory_cache.set("d", 4)  # Should evict "a"
    assert in_memory_cache.get("a") is None
    assert in_memory_cache.get("b") == 2


@pytest.mark.asyncio
async def test_async_set_and_get(in_memory_cache):
    await in_memory_cache.aset("foo", "bar")
    assert await in_memory_cache.aget("foo") == "bar"
    await in_memory_cache.aclear()
    assert await in_memory_cache.aget("foo") is None
