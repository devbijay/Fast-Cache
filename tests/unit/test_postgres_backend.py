import pytest
import time
import asyncio
from fastapi import FastAPI

from fast_cache import FastAPICache, PostgresBackend


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


def test_cached_function_runs_when_backend_unavailable(postgres_dsn):
    """Backend errors inside @cached are logged and the function still runs."""
    backend = PostgresBackend(postgres_dsn, namespace="pytest_unavailable")
    backend.close()
    fastapi_cache = FastAPICache()
    fastapi_cache.init_app(FastAPI(), backend)
    calls = 0

    @fastapi_cache.cached(expire=60)
    def compute(x):
        nonlocal calls
        calls += 1
        return x * 2

    assert compute(21) == 42
    assert compute(21) == 42
    assert calls == 2


def test_cached_function_errors_propagate(postgres_cache):
    fastapi_cache = FastAPICache()
    fastapi_cache.init_app(FastAPI(), postgres_cache)

    @fastapi_cache.cached(expire=60)
    def compute():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        compute()


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


@pytest.mark.asyncio
async def test_async_cached_function_runs_when_backend_unavailable(postgres_dsn):
    """Backend errors inside @cached are logged and the function still runs."""
    backend = PostgresBackend(postgres_dsn, namespace="pytest_async_unavailable")
    # Open the async pool before closing it; an unopened pool can still be opened later.
    await backend.aget("warmup")
    await backend.aclose()
    fastapi_cache = FastAPICache()
    fastapi_cache.init_app(FastAPI(), backend)
    calls = 0

    @fastapi_cache.cached(expire=60)
    async def compute(x):
        nonlocal calls
        calls += 1
        return x * 2

    assert await compute(21) == 42
    assert await compute(21) == 42
    assert calls == 2


@pytest.mark.asyncio
async def test_async_cached_function_errors_propagate(async_postgres_cache):
    fastapi_cache = FastAPICache()
    fastapi_cache.init_app(FastAPI(), async_postgres_cache)

    @fastapi_cache.cached(expire=60)
    async def compute():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await compute()


# ---- DEFAULT PARAMETER TESTS ----
def test_get_default_parameter(postgres_cache):
    """get() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert postgres_cache.get("nonexistent", default=sentinel) is sentinel
    assert postgres_cache.get("nonexistent") is None
    postgres_cache.set("null_key", None)
    assert postgres_cache.get("null_key", default=sentinel) is None


@pytest.mark.asyncio
async def test_aget_default_parameter(async_postgres_cache):
    """aget() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert await async_postgres_cache.aget("nonexistent", default=sentinel) is sentinel
    assert await async_postgres_cache.aget("nonexistent") is None
    await async_postgres_cache.aset("null_key", None)
    assert await async_postgres_cache.aget("null_key", default=sentinel) is None


# ---- CONCURRENCY TESTS ----
@pytest.mark.asyncio
async def test_concurrent_async_init(postgres_dsn):
    """Concurrent aget() calls on a fresh backend must not race on _ensure_async_pool_open()."""
    from fast_cache import PostgresBackend

    backend = PostgresBackend(postgres_dsn, namespace="pytest_race")
    try:
        results = await asyncio.gather(
            *[backend.aget(f"key-{i}") for i in range(50)]
        )
        assert all(r is None for r in results)
    finally:
        await backend.aclose()
