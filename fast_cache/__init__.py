from .integration import FastAPICache
from .backends.backend import CacheBackend

from .backends.redis import RedisBackend
from .backends.memory import InMemoryBackend
from .backends.postgres import PostgresBackend
from .backends.memcached import MemcachedBackend
from .backends.mongodb import MongoDBBackend

__all__ = ["FastAPICache", "RedisBackend", "CacheBackend", "InMemoryBackend","PostgresBackend", "cache","MemcachedBackend", "MongoDBBackend" ]


# Create global cache instance
cache = FastAPICache()
