import pytest
import asyncio
from fast_cache import InMemoryBackend


@pytest.fixture
def cache():
    return InMemoryBackend(namespace="test-ns", max_size=3)


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
    import time

    time.sleep(1.1)
    assert cache.get("foo") is None


def test_lru_eviction(cache):
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)  # Should evict "a"
    assert cache.get("a") is None
    assert cache.get("b") == 2


@pytest.mark.asyncio
async def test_async_set_and_get():
    cache = InMemoryBackend(namespace="test-ns-async")
    await cache.aset("foo", "bar")
    assert await cache.aget("foo") == "bar"
    await cache.aclear()
    assert await cache.aget("foo") is None
