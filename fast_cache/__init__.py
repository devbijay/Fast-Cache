from .integration import FastAPICache
from .backends.backend import CacheBackend

from .backends.redis import RedisBackend

__all__ = ["FastAPICache", "RedisBackend", "CacheBackend", "cache"]


# Create global cache instance
cache = FastAPICache()
