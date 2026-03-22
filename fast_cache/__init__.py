from importlib.metadata import version

from .integration import FastAPICache
from .backends.backend import CacheBackend

__version__ = version("fastapi-cachekit")

from .backends.redis import RedisBackend
from .backends.memory import InMemoryBackend
from .backends.postgres import PostgresBackend
from .backends.memcached import MemcachedBackend
from .backends.mongodb import MongoDBBackend
from .backends.google_firestore import FirestoreBackend
from .backends.dynamodb import DynamoDBBackend

__all__ = [
    "FastAPICache",
    "RedisBackend",
    "CacheBackend",
    "InMemoryBackend",
    "PostgresBackend",
    "cache",
    "MemcachedBackend",
    "MongoDBBackend",
    "FirestoreBackend",
    "DynamoDBBackend",
]


# Create global cache instance
cache = FastAPICache()
