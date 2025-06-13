from .integration import FastAPICache
from .backends.backend import CacheBackend

from .backends.redis import RedisBackend
from .backends.memory import InMemoryBackend
from .backends.postgres import PostgresBackend

__all__ = ["FastAPICache", "RedisBackend", "CacheBackend", "InMemoryBackend","PostgresBackend", "cache"]


# Create global cache instance
cache = FastAPICache()
