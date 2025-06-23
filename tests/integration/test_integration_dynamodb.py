import time
import pytest
from fastapi.testclient import TestClient
from testcontainers.core.container import DockerContainer

from examples.main import app
from fast_cache import cache, DynamoDBBackend

@pytest.fixture(scope="session")
def dynamodb_container():
    """DynamoDB Local container for testing."""
    container = DockerContainer("amazon/dynamodb-local:latest")
    container.with_exposed_ports(8000)
    container.with_command(["-jar", "DynamoDBLocal.jar", "-sharedDb", "-inMemory"])
    with container:
        time.sleep(2)
        yield container

@pytest.fixture(scope="session")
def dynamodb_endpoint(dynamodb_container):
    """Get DynamoDB Local endpoint URL."""
    host = dynamodb_container.get_container_host_ip()
    port = dynamodb_container.get_exposed_port(8000)
    return f"http://{host}:{port}"

@pytest.fixture
def client(dynamodb_endpoint):
    backend = DynamoDBBackend(
        table_name="test_cache_table",
        region_name="us-east-1",
        namespace="integration-demo",
        aws_access_key_id="fake",
        aws_secret_access_key="fake",
        endpoint_url=dynamodb_endpoint,
        create_table=True,
    )
    cache.init_app(app=app, backend=backend, default_expire=120)
    with TestClient(app) as c:
        yield c

def test_decorator_async_cache(client):
    resp1 = client.get("/decorator/async", params={"x": 10})
    assert resp1.status_code == 200
    val1 = resp1.json()["result"]

    resp2 = client.get("/decorator/async", params={"x": 10})
    assert resp2.status_code == 200
    assert resp2.json()["result"] == val1

    time.sleep(10.1)
    resp3 = client.get("/decorator/async", params={"x": 10})
    assert resp3.status_code == 200
    assert resp3.json()["result"] == val1

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

    resp2 = client.get("/decorator/custom", params={"x": 42})
    assert resp2.status_code == 200
    assert resp2.json()["custom_key"] == val1

def test_decorator_skip_cache(client):
    resp1 = client.get("/decorator/skip", params={"x": 3})
    assert resp1.status_code == 200
    val1 = resp1.json()["result"]

    resp2 = client.get("/decorator/skip", params={"x": 3})
    assert resp2.status_code == 200
    assert resp2.json()["result"] == val1

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
    resp = client.get("/di/set", params={"key": "foo", "value": "bar"})
    assert resp.status_code == 200
    assert resp.json()["set"] is True

    resp = client.get("/di/get", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["value"] == "bar"

    resp = client.get("/di/has", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["exists"] is True

    resp = client.delete("/di/delete", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    resp = client.get("/di/has", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["exists"] is False

    client.get("/di/set", params={"key": "foo", "value": "bar"})
    resp = client.post("/di/clear")
    assert resp.status_code == 200
    assert resp.json()["cleared"] is True

    resp = client.get("/di/has", params={"key": "foo"})
    assert resp.status_code == 200
    assert resp.json()["exists"] is False

def test_profile_cache(client):
    resp1 = client.get("/profile/123")
    assert resp1.status_code == 200
    assert resp1.json()["cached"] is False

    resp2 = client.get("/profile/123")
    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True

def test_weather_skip_cache(client):
    resp1 = client.get("/weather", params={"city": "London"})
    assert resp1.status_code == 200
    val1 = resp1.json()["weather"]

    resp2 = client.get("/weather", params={"city": "London"})
    assert resp2.status_code == 200
    assert resp2.json()["weather"] == val1

    resp3 = client.get("/weather", params={"city": "London", "skip_cache": True})
    assert resp3.status_code == 200
    assert resp3.json()["weather"] == val1