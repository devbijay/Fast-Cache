import pytest
import asyncio
import time
from fast_cache import RedisBackend


@pytest.fixture
def cache(redis_url):
    backend = RedisBackend(redis_url, namespace="test-ns")
    backend.clear()
    yield backend
    backend.clear()


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
