import pytest
import asyncio
import time
from fast_cache import InMemoryBackend


# ---- SYNC TESTS ----
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
    time.sleep(1.1)
    assert in_memory_cache.get("foo") is None


def test_lru_eviction(in_memory_cache):
    in_memory_cache.set("a", 1)
    in_memory_cache.set("b", 2)
    in_memory_cache.set("c", 3)
    in_memory_cache.set("d", 4)  # Should evict "a"
    assert in_memory_cache.get("a") is None
    assert in_memory_cache.get("b") == 2


# ---- ASYNC TESTS ----
@pytest.mark.asyncio
async def test_async_set_and_get(in_memory_cache):
    await in_memory_cache.aset("foo", "bar")
    assert await in_memory_cache.aget("foo") == "bar"


@pytest.mark.asyncio
async def test_async_delete(in_memory_cache):
    await in_memory_cache.aset("foo", "bar")
    await in_memory_cache.adelete("foo")
    assert await in_memory_cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_clear(in_memory_cache):
    await in_memory_cache.aset("foo", "bar")
    await in_memory_cache.aset("baz", "qux")
    await in_memory_cache.aclear()
    assert await in_memory_cache.aget("foo") is None
    assert await in_memory_cache.aget("baz") is None


@pytest.mark.asyncio
async def test_async_has(in_memory_cache):
    await in_memory_cache.aset("foo", "bar")
    assert await in_memory_cache.ahas("foo")
    await in_memory_cache.adelete("foo")
    assert not await in_memory_cache.ahas("foo")


@pytest.mark.asyncio
async def test_async_expire(in_memory_cache):
    await in_memory_cache.aset("foo", "bar", expire=1)
    assert await in_memory_cache.aget("foo") == "bar"
    await asyncio.sleep(1.1)
    assert await in_memory_cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_lru_eviction(in_memory_cache):
    await in_memory_cache.aset("a", 1)
    await in_memory_cache.aset("b", 2)
    await in_memory_cache.aset("c", 3)
    await in_memory_cache.aset("d", 4)  # Should evict "a"
    assert await in_memory_cache.aget("a") is None
    assert await in_memory_cache.aget("b") == 2