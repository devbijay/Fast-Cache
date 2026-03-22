import logging
import uuid

import pytest
import pytest_asyncio
import time
import asyncio
from fast_cache import DynamoDBBackend

logging.getLogger("testcontainers").setLevel(logging.CRITICAL)


# ---- SYNC FIXTURE ----
@pytest.fixture(scope="function")
def cache(dynamodb_endpoint):
    unique_table_name = f"test-cache-table-{uuid.uuid4().hex[:8]}"
    unique_namespace = f"my_cache_{uuid.uuid4().hex[:8]}"
    backend = DynamoDBBackend(
        table_name=unique_table_name,
        region_name="us-east-1",
        namespace=unique_namespace,
        endpoint_url=dynamodb_endpoint,
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
        create_table=True,
    )
    backend.clear()
    yield backend
    backend.clear()


# ---- ASYNC FIXTURE ----
@pytest_asyncio.fixture(scope="function")
async def async_cache(dynamodb_endpoint):
    unique_table_name = f"test-async-cache-table-{uuid.uuid4().hex[:8]}"
    unique_namespace = f"my_async_cache_{uuid.uuid4().hex[:8]}"

    backend = DynamoDBBackend(
        table_name=unique_table_name,
        region_name="us-east-1",
        namespace=unique_namespace,
        endpoint_url=dynamodb_endpoint,
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
        create_table=True,
    )

    # Wait for table creation to complete
    await asyncio.sleep(0.5)
    await backend.aclear()

    yield backend

    await backend.aclear()
    await backend.close()


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
    cache.set("foo", "bar", expire=2)
    assert cache.get("foo") == "bar"
    time.sleep(2)
    assert cache.get("foo") is None


# ---- ASYNC TESTS ----
@pytest.mark.asyncio
async def test_async_set_and_get(async_cache):
    await async_cache.aset("foo", "bar")
    assert await async_cache.aget("foo") == "bar"
    await async_cache.aclear()
    assert await async_cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_delete(async_cache):
    await async_cache.aset("foo", "bar")
    await async_cache.adelete("foo")
    assert await async_cache.aget("foo") is None


@pytest.mark.asyncio
async def test_async_clear(async_cache):
    await async_cache.aset("foo", "bar")
    await async_cache.aset("baz", "qux")
    await async_cache.aclear()
    assert await async_cache.aget("foo") is None
    assert await async_cache.aget("baz") is None


@pytest.mark.asyncio
async def test_async_has(async_cache):
    await async_cache.aset("foo", "bar")
    assert await async_cache.ahas("foo")
    await async_cache.adelete("foo")
    assert not await async_cache.ahas("foo")


@pytest.mark.asyncio
async def test_async_expire(async_cache):
    await async_cache.aset("foo", "bar", expire=1)
    assert await async_cache.aget("foo") == "bar"
    await asyncio.sleep(1.1)
    assert await async_cache.aget("foo") is None


# ---- DEFAULT PARAMETER TESTS ----
def test_get_default_parameter(cache):
    """get() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert cache.get("nonexistent", default=sentinel) is sentinel
    assert cache.get("nonexistent") is None
    cache.set("null_key", None)
    assert cache.get("null_key", default=sentinel) is None


@pytest.mark.asyncio
async def test_aget_default_parameter(async_cache):
    """aget() returns default on miss, None by default for backward compat, and distinguishes stored None from a miss."""
    sentinel = object()
    assert await async_cache.aget("nonexistent", default=sentinel) is sentinel
    assert await async_cache.aget("nonexistent") is None
    await async_cache.aset("null_key", None)
    assert await async_cache.aget("null_key", default=sentinel) is None
