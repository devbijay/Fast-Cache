import uuid

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
