import pytest
import time
import asyncio


try:
    from fast_cache import PostgresBackend

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not POSTGRES_AVAILABLE, reason="PostgresBackend not available"
)


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


@pytest.mark.asyncio
async def test_async_set_and_get(async_postgres_cache):
    await async_postgres_cache.aset("foo", "bar")
    assert await async_postgres_cache.aget("foo") == "bar"
    await async_postgres_cache.aclear()
    assert await async_postgres_cache.aget("foo") is None
