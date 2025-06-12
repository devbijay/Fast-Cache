from .integration import FastAPICache
from .backends.backend import CacheBackend

from .backends.redis import RedisBackend
from .backends.memory import InMemoryBackend

__all__ = ["FastAPICache", "RedisBackend", "CacheBackend", "InMemoryBackend", "cache"]


# Create global cache instance
cache = FastAPICache()
