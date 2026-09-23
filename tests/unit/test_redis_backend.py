import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fastapi import FastAPI
from fast_cache import FastAPICache, RedisBackend


@pytest.fixture
def cache(redis_url):
    backend = RedisBackend(redis_url, namespace="test-ns")
    backend.clear()
    yield backend
    backend.clear()


@pytest.fixture
def fastapi_cache(cache):
    instance = FastAPICache()
    instance.init_app(FastAPI(), cache)
    return instance


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


def test_expire_timedelta(cache):
    cache.set("foo", "bar", expire=timedelta(seconds=1))
    assert cache.get("foo") == "bar"
    time.sleep(1.1)
    assert cache.get("foo") is None


def test_expire_sub_second_timedelta(cache):
    cache.set("foo", "bar", expire=timedelta(milliseconds=500))
    assert cache.get("foo") == "bar"
    time.sleep(0.6)
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


@pytest.mark.asyncio
async def test_async_expire_timedelta(cache):
    await cache.aset("foo", "bar", expire=timedelta(seconds=1))
    assert await cache.aget("foo") == "bar"
    await asyncio.sleep(1.1)
    assert await cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_expire_sub_second_timedelta(cache):
    await cache.aset("foo", "bar", expire=timedelta(milliseconds=500))
    assert await cache.aget("foo") == "bar"
    await asyncio.sleep(0.6)
    assert await cache.aget("foo") is None


# ---- DEFAULT PARAMETER TESTS ----
def test_get_default_parameter(cache):
    """get() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    # Missing key with default returns sentinel
    assert cache.get("nonexistent", default=sentinel) is sentinel
    # Missing key without default returns None (backward compat)
    assert cache.get("nonexistent") is None
    # Stored None is returned as None, not the default
    cache.set("null_key", None)
    assert cache.get("null_key", default=sentinel) is None


@pytest.mark.asyncio
async def test_aget_default_parameter(cache):
    """aget() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert await cache.aget("nonexistent", default=sentinel) is sentinel
    assert await cache.aget("nonexistent") is None
    await cache.aset("null_key", None)
    assert await cache.aget("null_key", default=sentinel) is None


# ---- LOCK TESTS (SYNC) ----
def test_acquire_and_release_lock(cache):
    """acquire_lock returns a token, release_lock returns True."""
    token = cache.acquire_lock("locktest", timeout=5, wait=0)
    assert token is not None
    assert cache.release_lock("locktest", token) is True


def test_lock_is_exclusive(cache):
    """Second acquire with wait=0 returns None while lock is held."""
    token = cache.acquire_lock("exclusive", timeout=5, wait=0)
    assert token is not None
    assert cache.acquire_lock("exclusive", timeout=5, wait=0) is None
    cache.release_lock("exclusive", token)


def test_release_with_wrong_token(cache):
    """Releasing with wrong token returns False and lock remains."""
    token = cache.acquire_lock("wrongtoken", timeout=5, wait=0)
    assert token is not None
    assert cache.release_lock("wrongtoken", "bad-token") is False
    # Lock still held — second acquire still fails
    assert cache.acquire_lock("wrongtoken", timeout=5, wait=0) is None
    cache.release_lock("wrongtoken", token)


def test_lock_auto_expires(cache):
    """Lock auto-expires after timeout, allowing re-acquisition."""
    token = cache.acquire_lock("expiry", timeout=1, wait=0)
    assert token is not None
    time.sleep(1.1)
    new_token = cache.acquire_lock("expiry", timeout=5, wait=0)
    assert new_token is not None
    cache.release_lock("expiry", new_token)


# ---- LOCK TESTS (ASYNC) ----
@pytest.mark.asyncio
async def test_async_acquire_and_release_lock(cache):
    """aacquire_lock returns a token, arelease_lock returns True."""
    token = await cache.aacquire_lock("alocktest", timeout=5, wait=0)
    assert token is not None
    assert await cache.arelease_lock("alocktest", token) is True


@pytest.mark.asyncio
async def test_async_lock_is_exclusive(cache):
    """Second aacquire_lock with wait=0 returns None while lock is held."""
    token = await cache.aacquire_lock("aexclusive", timeout=5, wait=0)
    assert token is not None
    assert await cache.aacquire_lock("aexclusive", timeout=5, wait=0) is None
    await cache.arelease_lock("aexclusive", token)


@pytest.mark.asyncio
async def test_async_release_with_wrong_token(cache):
    """Releasing with wrong token returns False and lock remains."""
    token = await cache.aacquire_lock("awrongtoken", timeout=5, wait=0)
    assert token is not None
    assert await cache.arelease_lock("awrongtoken", "bad-token") is False
    assert await cache.aacquire_lock("awrongtoken", timeout=5, wait=0) is None
    await cache.arelease_lock("awrongtoken", token)


@pytest.mark.asyncio
async def test_async_lock_auto_expires(cache):
    """Lock auto-expires after timeout, allowing re-acquisition."""
    token = await cache.aacquire_lock("aexpiry", timeout=1, wait=0)
    assert token is not None
    await asyncio.sleep(1.1)
    new_token = await cache.aacquire_lock("aexpiry", timeout=5, wait=0)
    assert new_token is not None
    await cache.arelease_lock("aexpiry", new_token)


# ---- STAMPEDE TESTS (SYNC) ----
def test_cached_sync_concurrent_misses_execute_once(fastapi_cache):
    """Concurrent misses on the same key run the wrapped function once."""
    calls = 0
    calls_guard = threading.Lock()

    @fastapi_cache.cached(expire=60)
    def compute(x):
        nonlocal calls
        with calls_guard:
            calls += 1
        time.sleep(0.2)
        return x * 2

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: compute(21), range(10)))
    elapsed = time.monotonic() - started

    assert results == [42] * 10
    assert calls == 1
    assert elapsed < 1.0


def test_cached_sync_falls_back_after_lock_wait(fastapi_cache, cache):
    """When the lock is held past lock_wait, the function runs uncached."""
    calls = 0

    @fastapi_cache.cached(expire=60, lock_wait=0.2)
    def compute():
        nonlocal calls
        calls += 1
        return "fresh"

    cache_key = f"{compute.__module__}:{compute.__name__}:():{{}}"
    token = cache.acquire_lock(cache_key, timeout=5, wait=0)
    try:
        assert compute() == "fresh"
    finally:
        cache.release_lock(cache_key, token)

    assert calls == 1
    assert cache.get(cache_key) is None


# ---- STAMPEDE TESTS (ASYNC) ----
@pytest.mark.asyncio
async def test_cached_async_concurrent_misses_execute_once(fastapi_cache):
    """Concurrent misses on the same key run the wrapped function once."""
    calls = 0

    @fastapi_cache.cached(expire=60)
    async def compute(x):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.2)
        return x * 2

    started = time.monotonic()
    results = await asyncio.gather(*(compute(21) for _ in range(10)))
    elapsed = time.monotonic() - started

    assert results == [42] * 10
    assert calls == 1
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_cached_async_waiter_takes_over_when_holder_fails(fastapi_cache):
    """A waiter recomputes as soon as a failed holder releases the lock."""
    calls = 0

    @fastapi_cache.cached(expire=60, lock_wait=5.0)
    async def compute():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.1)
        if calls == 1:
            raise RuntimeError("boom")
        return "ok"

    started = time.monotonic()
    results = await asyncio.gather(compute(), compute(), return_exceptions=True)
    elapsed = time.monotonic() - started

    assert isinstance(results[0], RuntimeError)
    assert results[1] == "ok"
    assert calls == 2
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_cached_async_falls_back_after_lock_wait(fastapi_cache, cache):
    """When the lock is held past lock_wait, the function runs uncached."""
    calls = 0

    @fastapi_cache.cached(expire=60, lock_wait=0.2)
    async def compute():
        nonlocal calls
        calls += 1
        return "fresh"

    cache_key = f"{compute.__module__}:{compute.__name__}:():{{}}"
    token = await cache.aacquire_lock(cache_key, timeout=5, wait=0)
    try:
        assert await compute() == "fresh"
    finally:
        await cache.arelease_lock(cache_key, token)

    assert calls == 1
    assert await cache.aget(cache_key) is None
