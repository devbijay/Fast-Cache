import pickle
import time
from typing import Any, Optional, Union
from datetime import timedelta
from .backend import CacheBackend

class MongoDBBackend(CacheBackend):
    """
    MongoDB cache backend with both sync and async support.
    Uses a TTL index for automatic expiration of cache entries.

    Each cache entry is stored as a document with:
      - _id: the cache key (optionally namespaced)
      - value: the pickled cached value
      - expires_at: epoch time when the entry should expire

    Expired documents are deleted automatically by MongoDB's TTL monitor,
    but expiration is also checked in code to avoid returning stale data.
    """

    def __init__(
        self,
        uri: str,
        namespace: Optional[str] = "fastapi_cache"
    ) -> None:
        """
        Initialize the MongoDB backend.

        Args:
            uri (str): MongoDB connection URI (should include the database name).
            namespace (Optional[str]): Optional prefix for all cache keys and the collection name.
                                       Defaults to "fastapi_cache".
        Raises:
            ImportError: If pymongo is not installed.
        """
        try:
            import pymongo
        except ImportError:
            raise ImportError(
                "MongoDBBackend requires 'pymongo>=4.6.0'. "
                "Install with: pip install fastapi-cachekit[mongodb]"
            )
        self._namespace = namespace or "cache"

        self._sync_client = pymongo.MongoClient(uri)
        self._sync_db = self._sync_client.get_default_database()
        self._sync_collection = self._sync_db[self._namespace]
        self._sync_collection.create_index("expires_at", expireAfterSeconds=0)

        # Async client
        self._async_client = pymongo.AsyncMongoClient(uri)
        self._async_db = self._async_client.get_default_database()
        self._async_collection = self._async_db[self._namespace]

    def _make_key(self, key: str) -> str:
        """
        Create a namespaced cache key.

        Args:
            key (str): The original cache key.

        Returns:
            str: The namespaced cache key.
        """
        return f"{self._namespace}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieve a value from the cache.

        Args:
            key (str): The cache key.

        Returns:
            Optional[Any]: The cached value, or None if not found or expired.
        """
        doc = self._sync_collection.find_one({"_id": self._make_key(key)})
        if doc and (doc.get("expires_at", float("inf")) > time.time()):
            return pickle.loads(doc["value"])
        return None

    def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Synchronously set a value in the cache.

        Args:
            key (str): The cache key.
            value (Any): The value to cache.
            expire (Optional[Union[int, timedelta]]): Expiration time in seconds or as timedelta.
                                                     If None, the entry never expires.
        """
        update = {"value": pickle.dumps(value)}
        if expire is not None:
            if isinstance(expire, timedelta):
                exptime = int(time.time() + expire.total_seconds())
            else:
                exptime = int(time.time() + expire)
            update["expires_at"] = exptime

        self._sync_collection.update_one(
            {"_id": self._make_key(key)}, {"$set": update}, upsert=True
        )

    def delete(self, key: str) -> None:
        """
        Synchronously delete a value from the cache.

        Args:
            key (str): The cache key.
        """
        self._sync_collection.delete_one({"_id": self._make_key(key)})

    def clear(self) -> None:
        """
        Synchronously clear all values from the namespace.
        """
        self._sync_collection.delete_many({"_id": {"$regex": f"^{self._namespace}:"}})

    def has(self, key: str) -> bool:
        """
        Synchronously check if a key exists in the cache.

        Args:
            key (str): The cache key.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.
        """
        doc = self._sync_collection.find_one({"_id": self._make_key(key)})
        return bool(doc and (doc.get("expires_at", float("inf")) > time.time()))

    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieve a value from the cache.

        Args:
            key (str): The cache key.

        Returns:
            Optional[Any]: The cached value, or None if not found or expired.
        """
        doc = await self._async_collection.find_one({"_id": self._make_key(key)})
        if doc and (doc.get("expires_at", float("inf")) > time.time()):
            return pickle.loads(doc["value"])
        return None

    async def aset(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Asynchronously set a value in the cache.

        Args:
            key (str): The cache key.
            value (Any): The value to cache.
            expire (Optional[Union[int, timedelta]]): Expiration time in seconds or as timedelta.
                                                     If None, the entry never expires.
        """
        update = {"value": pickle.dumps(value)}
        if expire is not None:
            if isinstance(expire, timedelta):
                exptime = int(time.time() + expire.total_seconds())
            else:
                exptime = int(time.time() + expire)
            update["expires_at"] = exptime

        await self._async_collection.update_one(
            {"_id": self._make_key(key)},
            {"$set": update},
            upsert=True
        )

    async def adelete(self, key: str) -> None:
        """
        Asynchronously delete a value from the cache.

        Args:
            key (str): The cache key.
        """
        await self._async_collection.delete_one({"_id": self._make_key(key)})

    async def aclear(self) -> None:
        """
        Asynchronously clear all values from the namespace.
        """
        await self._async_collection.delete_many({"_id": {"$regex": f"^{self._namespace}:"}})

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously check if a key exists in the cache.

        Args:
            key (str): The cache key.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.
        """
        doc = await self._async_collection.find_one({"_id": self._make_key(key)})
        return bool(doc and (doc.get("expires_at", float("inf")) > time.time()))

    def close(self) -> None:
        """
        Close the synchronous MongoDB client.
        """
        self._sync_client.close()

    async def aclose(self) -> None:
        """
        Close the asynchronous MongoDB client.
        """
        self._sync_client.close()
        await self._async_client.close()