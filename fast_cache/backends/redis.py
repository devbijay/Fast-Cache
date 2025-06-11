import asyncio
import inspect
from typing import Any, Optional, Union
from datetime import timedelta
import pickle
import redis.asyncio as aioredis
import redis
from .backend import CacheBackend


class RedisBackend(CacheBackend):
    """Redis cache backend implementation with namespace support"""

    def __init__(
        self,
        redis_url: str,
        namespace: str = "fastapi-cache",
        pool_size: int = 10,
        max_connections: int = 20,
    ) -> None:
        """
        Initialize Redis backend with connection URL and pool settings.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            namespace: Namespace prefix for all keys (default: "fastapi-cache")
            pool_size: Minimum number of connections in the pool
            max_connections: Maximum number of connections in the pool
        """
        self._namespace = namespace
        self._sync_pool = redis.ConnectionPool.from_url(
            redis_url, max_connections=max_connections, decode_responses=False
        )

        self._async_pool = aioredis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            decode_responses=False,
            encoding="utf-8",
        )

        self._sync_client = redis.Redis(connection_pool=self._sync_pool)
        self._async_client = aioredis.Redis(connection_pool=self._async_pool)

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self._namespace}:{key}"

    async def _scan_keys(self, pattern: str = "*") -> list[str]:
        """Scan all keys in the namespace."""
        keys = []
        cursor = 0
        namespace_pattern = self._make_key(pattern)

        while True:
            cursor, batch = await self._async_client.scan(
                cursor=cursor, match=namespace_pattern, count=100
            )
            keys.extend(batch)
            if cursor == 0:
                break
        return keys

    async def aget(self, key: str) -> Any:
        """Asynchronously retrieve a value from the cache."""
        try:
            result = await self._async_client.get(self._make_key(key))
            return pickle.loads(result) if result else None
        except Exception:
            return None

    def get(self, key: str) -> Any:
        """Synchronously retrieve a value from the cache."""
        try:
            result = self._sync_client.get(self._make_key(key))
            return pickle.loads(result) if result else None
        except Exception:
            return None

    async def aset(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """Asynchronously set a value in the cache."""
        try:
            ex = expire.total_seconds() if isinstance(expire, timedelta) else expire
            await self._async_client.set(
                self._make_key(key), pickle.dumps(value), ex=ex
            )
        except Exception:
            pass

    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """Synchronously set a value in the cache."""
        try:
            ex = expire.total_seconds() if isinstance(expire, timedelta) else expire
            self._sync_client.set(self._make_key(key), pickle.dumps(value), ex=ex)
        except Exception:
            pass

    async def adelete(self, key: str) -> None:
        """Asynchronously delete a value from the cache."""
        try:
            await self._async_client.delete(self._make_key(key))
        except Exception:
            pass

    def delete(self, key: str) -> None:
        """Synchronously delete a value from the cache."""
        try:
            self._sync_client.delete(self._make_key(key))
        except Exception:
            pass

    async def aclear(self) -> None:
        """Asynchronously clear all values from the namespace."""
        try:
            keys = await self._scan_keys()
            if keys:
                await self._async_client.delete(*keys)
        except Exception:
            pass

    def clear(self) -> None:
        """Synchronously clear all values from the namespace."""
        try:
            cursor = 0
            namespace_pattern = self._make_key("*")

            while True:
                cursor, keys = self._sync_client.scan(
                    cursor=cursor, match=namespace_pattern, count=100
                )
                if keys:
                    self._sync_client.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass

    async def ahas(self, key: str) -> bool:
        """Asynchronously check if a key exists in the cache."""
        try:
            return await self._async_client.exists(self._make_key(key)) > 0
        except Exception:
            return False

    def has(self, key: str) -> bool:
        """Synchronously check if a key exists in the cache."""
        try:
            return self._sync_client.exists(self._make_key(key)) > 0
        except Exception:
            return False

    async def close(self) -> None:
        """Close Redis connections and clean up pools."""
        await self._async_client.close()
        await self._async_pool.disconnect()
        self._sync_client.close()
        self._sync_pool.disconnect()
