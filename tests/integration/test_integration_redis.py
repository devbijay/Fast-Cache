import os
import time
import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from examples.main import app
from fast_cache import RedisBackend, cache, InMemoryBackend, PostgresBackend


@pytest.fixture
def client():
    with RedisContainer() as redis:
        redis_url = (
            f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
        )
        backend = RedisBackend(redis_url, namespace="integration-demo")
        cache.init_app(app=app, backend=backend, default_expire=120)
        with TestClient(app) as c:
            yield c


def test_decorator_async_cache(client):
    # First call: not cached
    resp1 = client.get("/decorator/async", params={"x": 10})
    assert resp1.status_code == 200
    val1 = resp1.json()["result"]

    # Second call: should be cached
    resp2 = client.get("/decorator/async", params={"x": 10})
    assert resp2.status_code == 200
    assert resp2.json()["result"] == val1

    # Wait for cache to expire
    time.sleep(10.1)
    resp3 = client.get("/decorator/async", params={"x": 10})
    assert resp3.status_code == 200
    assert resp3.json()["result"] == val1  # Function is deterministic


def test_decorator_sync_cache(client):
    resp1 = client.get("/decorator/sync", params={"x": 7})
    assert resp1.status_code == 200
    val1 = resp1.json()["result"]

    resp2 = client.get("/decorator/sync", params={"x": 7})
    assert resp2.status_code == 200
    assert resp2.json()["result"] == val1


def test_decorator_custom_key(client):
    resp1 = client.get("/decorator/custom", params={"x": 42})
    assert resp1.status_code == 200
    val1 = resp1.json()["custom_key"]

    # Should be cached even if called again
    resp2 = client.get("/decorator/custom", params={"x": 42})
    assert resp2.status_code == 200
    assert resp2.json()["custom_key"] == val1


def test_decorator_skip_cache(client):
    resp1 = client.get("/decorator/skip", params={"x": 3})
    assert resp1.status_code == 200
    val1 = resp1.json()["result"]

    # Should be cached
    resp2 = client.get("/decorator/skip", params={"x": 3})
    assert resp2.status_code == 200
    assert resp2.json()["result"] == val1

    # Skip cache
    resp3 = client.get("/decorator/skip", params={"x": 3, "skip_cache": True})
    assert resp3.status_code == 200
    assert resp3.json()["result"] == val1


def test_decorator_pydantic(client):
    resp = client.get("/decorator/pydantic", params={"name": "foo", "value": 123})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "foo"
    assert data["value"] == 123


def test_di_set_get_has_delete_clear(client):
    # Set a value
    resp = client.get("/di/set", params={"key": "foo", "value": "bar"})
    assert resp.status_code == 200
    assert resp.json()["set"] is True

    # Get the value
    resp = client.get("/di/get", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["value"] == "bar"

    # Check existence
    resp = client.get("/di/has", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["exists"] is True

    # Delete the key
    resp = client.delete("/di/delete", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Should not exist now
    resp = client.get("/di/has", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["exists"] is False

    # Set again and clear all
    client.get("/di/set", params={"key": "foo", "value": "bar"})
    resp = client.post("/di/clear")
    assert resp.status_code == 200
    assert resp.json()["cleared"] is True

    # Should not exist after clear
    resp = client.get("/di/has", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["exists"] is False


def test_profile_cache(client):
    # First call: not cached
    resp1 = client.get("/profile/123")
    assert resp1.status_code == 200
    assert resp1.json()["cached"] is False

    # Second call: should be cached
    resp2 = client.get("/profile/123")
    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True


def test_weather_skip_cache(client):
    # First call: cached
    resp1 = client.get("/weather", params={"city": "London"})
    assert resp1.status_code == 200
    val1 = resp1.json()["weather"]

    # Second call: cached
    resp2 = client.get("/weather", params={"city": "London"})
    assert resp2.status_code == 200
    assert resp2.json()["weather"] == val1

    # Third call: skip cache
    resp3 = client.get("/weather", params={"city": "London", "skip_cache": True})
    assert resp3.status_code == 200
    assert resp3.json()["weather"] == val1
