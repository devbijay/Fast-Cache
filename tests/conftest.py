import pytest
import os

from examples.main import app
from fast_cache import InMemoryBackend

# Only import RedisBackend and set up Redis if redis is available
try:
    from fast_cache import RedisBackend
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

@pytest.fixture
def in_memory_cache():
    """Fixture for a fresh InMemoryBackend instance."""
    cache = InMemoryBackend(namespace="test-ns", max_size=10)
    cache.clear()
    yield cache
    cache.clear()

@pytest.fixture(scope="session")
def redis_url():
    """Fixture for Redis URL, can be overridden by environment variable."""
    return os.getenv("TEST_REDIS_URL", "redis://localhost:6379/0")

@pytest.fixture
def redis_cache(redis_url):
    """Fixture for a fresh RedisBackend instance (if available)."""
    if not REDIS_AVAILABLE:
        pytest.skip("RedisBackend not available")
    cache = RedisBackend(redis_url, namespace="test-ns")
    cache.clear()
    yield cache
    cache.clear()


