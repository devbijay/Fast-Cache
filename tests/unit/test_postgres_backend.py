import pytest
import time
import asyncio


# ---- SYNC TESTS ----
def test_set_and_get(postgres_cache):
    postgres_cache.set("foo", "bar")
    assert postgres_cache.get("foo") == "bar"


def test_delete(postgres_cache):
    postgres_cache.set("foo", "bar")
    postgres_cache.delete("foo")
    assert postgres_cache.get("foo") is None


def test_clear(postgres_cache):
    postgres_cache.set("foo", "bar")
    postgres_cache.set("baz", "qux")
    postgres_cache.clear()
    assert postgres_cache.get("foo") is None
    assert postgres_cache.get("baz") is None


def test_has(postgres_cache):
    postgres_cache.set("foo", "bar")
    assert postgres_cache.has("foo")
    postgres_cache.delete("foo")
    assert not postgres_cache.has("foo")


def test_expire(postgres_cache):
    postgres_cache.set("foo", "bar", expire=1)
    assert postgres_cache.get("foo") == "bar"
    time.sleep(1.1)
    assert postgres_cache.get("foo") is None


# ---- ASYNC TESTS ----
@pytest.mark.asyncio
async def test_async_set_and_get(async_postgres_cache):
    await async_postgres_cache.aset("foo", "bar")
    assert await async_postgres_cache.aget("foo") == "bar"


@pytest.mark.asyncio
async def test_async_delete(async_postgres_cache):
    await async_postgres_cache.aset("foo", "bar")
    await async_postgres_cache.adelete("foo")
    assert await async_postgres_cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_clear(async_postgres_cache):
    await async_postgres_cache.aset("foo", "bar")
    await async_postgres_cache.aset("baz", "qux")
    await async_postgres_cache.aclear()
    assert await async_postgres_cache.aget("foo") is None
    assert await async_postgres_cache.aget("baz") is None


@pytest.mark.asyncio
async def test_async_has(async_postgres_cache):
    await async_postgres_cache.aset("foo", "bar")
    assert await async_postgres_cache.ahas("foo")
    await async_postgres_cache.adelete("foo")
    assert not await async_postgres_cache.ahas("foo")


@pytest.mark.asyncio
async def test_async_expire(async_postgres_cache):
    await async_postgres_cache.aset("foo", "bar", expire=1)
    assert await async_postgres_cache.aget("foo") == "bar"
    await asyncio.sleep(1.1)
    assert await async_postgres_cache.aget("foo") is None
