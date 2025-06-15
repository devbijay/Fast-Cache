import pytest
import asyncio

import pytest_asyncio

from fast_cache import MongoDBBackend


@pytest_asyncio.fixture
async def cache(mongo_url):
    backend = MongoDBBackend(mongo_url, namespace="my_cache")
    await backend.aclear()
    yield backend
    await backend.aclear()
    await backend.aclose()


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


@pytest.mark.asyncio
async def test_async_set_and_get(cache):
    await cache.aset("foo", "bar")
    assert await cache.aget("foo") == "bar"
    await cache.aclear()
    assert await cache.aget("foo") is None
