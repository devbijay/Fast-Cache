import asyncio
import sys

import pytest
import os

import pytest_asyncio
from testcontainers.core.container import DockerContainer
from testcontainers.memcached import MemcachedContainer
from testcontainers.mongodb import MongoDbContainer
from testcontainers.redis import RedisContainer

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from fast_cache import InMemoryBackend
from testcontainers.postgres import PostgresContainer

# Only import RedisBackend and set up Redis if redis is available
try:
    from fast_cache import RedisBackend

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from fast_cache import PostgresBackend

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    from fast_cache import MemcachedBackend

    MEMCACHED_AVAILABLE = True
except ImportError:
    MEMCACHED_AVAILABLE = False


@pytest.fixture
def in_memory_cache():
    """Fixture for a fresh InMemoryBackend instance."""
    cache = InMemoryBackend(namespace="test-ns", max_size=3)
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer() as container:
        yield container


@pytest.fixture(scope="session")
def redis_url(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture
def redis_cache(redis_url):
    """Fixture for a fresh RedisBackend instance (if available)."""
    if not REDIS_AVAILABLE:
        pytest.skip("RedisBackend not available")
    cache = RedisBackend(redis_url, namespace="test-ns")
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer() as container:
        yield container


@pytest.fixture(scope="session")
def postgres_dsn(postgres_container) -> str:
    # Use the same container for all tests
    return postgres_container.get_connection_url(driver=None)


@pytest.fixture
def postgres_cache(postgres_dsn: str) -> PostgresBackend:
    backend = PostgresBackend(postgres_dsn, namespace="pytest_sync")
    try:
        backend.clear()  # Ensure a clean slate before the test
        yield backend
    finally:
        # Teardown: guaranteed to run even if the test fails
        backend.clear()


@pytest_asyncio.fixture
async def async_postgres_cache(postgres_dsn: str) -> PostgresBackend:
    backend = PostgresBackend(postgres_dsn, namespace="pytest_async")
    try:
        await backend.aclear()
        yield backend
    finally:
        # Teardown: guaranteed to run even if the test fails
        await backend.aclear()
        await backend.close()


@pytest.fixture(scope="session")
def memcached_container():
    with MemcachedContainer() as container:
        yield container


@pytest.fixture(scope="session")
def memcached_url(memcached_container):
    host = memcached_container.get_container_host_ip()
    port = int(memcached_container.get_exposed_port(11211))
    return host, port


@pytest.fixture
def memcached_cache(memcached_url):
    if not MEMCACHED_AVAILABLE:
        pytest.skip("MemcachedBackend not available")
    host, port = memcached_url
    backend = MemcachedBackend(host=host, port=port, namespace="test-ns")
    yield backend
    backend.clear()


@pytest.fixture(scope="session")
def mongo_url():
    with MongoDbContainer(
        username="test", password="test", dbname="testdb"
    ) as container:
        db_url = container.get_connection_url()
        # Always add authSource to be explicit
        if not db_url.endswith("/testdb"):
            db_url = f"{db_url}/testdb"
        if "authSource" not in db_url:
            db_url = f"{db_url}?authSource=admin"
        print(f"\n[TEST] MongoDB URL: {db_url}")
        yield db_url


@pytest.fixture(scope="session")
def dynamodb_container():
    """DynamoDB Local container for testing."""
    container = DockerContainer("amazon/dynamodb-local:latest")
    container.with_exposed_ports(8000)
    container.with_command(["-jar", "DynamoDBLocal.jar", "-sharedDb", "-inMemory"])

    with container:
        # Simple sleep - DynamoDB Local starts quickly
        import time

        time.sleep(2)
        yield container


@pytest.fixture(scope="session")
def dynamodb_endpoint(dynamodb_container):
    """Get DynamoDB Local endpoint URL."""
    host = dynamodb_container.get_container_host_ip()
    port = dynamodb_container.get_exposed_port(8000)
    return f"http://{host}:{port}"