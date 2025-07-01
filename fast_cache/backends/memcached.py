import pickle
from typing import Any, Optional, Union
from datetime import timedelta
from .backend import CacheBackend


class MemcachedBackend(CacheBackend):
    """
    Initializes a new instance of the MemcachedBackend cache.

    This backend provides a cache using Memcached as the storage layer. It supports
    both synchronous and asynchronous operations, and uses a namespace prefix for
    all keys to avoid collisions.

    Args:
        host (str): The hostname or IP address of the Memcached server.
        port (int): The port number of the Memcached server.
        pool_size (int, optional): The maximum number of connections in the async pool.
            Defaults to 10.
        pool_minsize (int, optional): The minimum number of connections in the async pool.
            Defaults to 1.
        namespace (str, optional): Prefix for all cache keys. Defaults to "fastapi_cache".

    Raises:
        ImportError: If the required `aiomcache` or `pymemcache` packages are not installed.

    Notes:
        - Both synchronous and asynchronous Memcached clients are initialized.
        - The async client is created per event loop.
        - All cache keys are automatically namespaced.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        pool_size: int = 10,
        pool_minsize: int = 1,
        namespace: str = "fastapi_cache",
    ) -> None:
        try:
            import aiomcache
            from pymemcache.client.base import PooledClient
        except ImportError:
            raise ImportError(
                "MemcachedBackend requires 'aiomcache' and 'pymemcache'. "
                "Install with: pip install fast-cache[memcached]"
            )
        self._namespace = namespace
        self._host = host
        self._port = port

        # Sync client
        self._sync_client = PooledClient(
            (host, port),
            max_pool_size=10,
        )
        self._async_client = aiomcache.Client(
            host,
            port,
            pool_size=pool_size,
            pool_minsize=pool_minsize,
        )
        # Async client will be created per event loop

    def _make_key(self, key: str) -> bytes:
        """
        Creates a namespaced cache key as bytes for Memcached.

        Args:
            key (str): The original cache key.

        Returns:
            bytes: The namespaced cache key, encoded as bytes.

        Notes:
            - All cache operations use namespaced keys internally.
            - Ensures key separation between different namespaces.
        """
        return f"{self._namespace}:{key}".encode()

    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieves a value from the cache by key.

        If the key does not exist, returns None.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found.

        Notes:
            - The value is deserialized using pickle.
            - Handles deserialization errors gracefully.
            - Thread-safe for Memcached client.
        """
        try:
            value = self._sync_client.get(self._make_key(key))
            return pickle.loads(value) if value else None
        except Exception:
            return None

    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Synchronously stores a value in the cache under the specified key.

        If the key already exists, its value and expiration time are updated.
        Optionally, an expiration time can be set, after which the entry will be
        considered expired and eligible for deletion.

        Args:
            key (str): The cache key to store the value under.
            value (Any): The Python object to cache.
            expire (Optional[Union[int, timedelta]], optional): The expiration time
                for the cache entry. Can be specified as an integer (seconds) or a
                timedelta. If None, the entry does not expire.

        Notes:
            - The value is serialized using pickle.
            - Thread-safe for Memcached client.
            - Expiration is handled by Memcached.
        """
        try:
            exptime = (
                int(expire.total_seconds())
                if isinstance(expire, timedelta)
                else (expire or 0)
            )
            self._sync_client.set(
                self._make_key(key), pickle.dumps(value), expire=exptime
            )
        except Exception:
            pass

    def delete(self, key: str) -> None:
        """
        Synchronously deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - Thread-safe for Memcached client.
            - The key is automatically namespaced.
        """
        try:
            self._sync_client.delete(self._make_key(key))
        except Exception:
            pass

    def clear(self) -> None:
        """
        Synchronously removes all cache entries from Memcached.

        Memcached does not support namespace-based clearing, so this operation flushes
        the entire cache, removing all entries regardless of namespace.

        Notes:
            - Thread-safe for Memcached client.
            - This operation affects all keys in the Memcached instance.
            - Use with caution in shared environments.
        """

        try:
            self._sync_client.flush_all()
        except Exception:
            pass

    def has(self, key: str) -> bool:
        """
        Synchronously checks if a cache key exists.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists, False otherwise.

        Notes:
            - Thread-safe for Memcached client.
            - Expired entries are not considered present.
        """
        try:
            return self._sync_client.get(self._make_key(key)) is not None
        except Exception:
            return False

    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieves a value from the cache by key.

        If the key does not exist, returns None.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found.

        Notes:
            - The value is deserialized using pickle.
            - Handles deserialization errors gracefully.
            - Asyncio-safe for Memcached client.
        """
        try:
            value = await self._async_client.get(self._make_key(key))
            return pickle.loads(value) if value else None
        except Exception:
            return None

    async def aset(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Asynchronously stores a value in the cache under the specified key.

        If the key already exists, its value and expiration time are updated.
        Optionally, an expiration time can be set, after which the entry will be
        considered expired and eligible for deletion.

        Args:
            key (str): The cache key to store the value under.
            value (Any): The Python object to cache.
            expire (Optional[Union[int, timedelta]], optional): The expiration time
                for the cache entry. Can be specified as an integer (seconds) or a
                timedelta. If None, the entry does not expire.

        Notes:
            - The value is serialized using pickle.
            - Asyncio-safe for Memcached client.
            - Expiration is handled by Memcached.
        """
        try:
            exptime = (
                int(expire.total_seconds())
                if isinstance(expire, timedelta)
                else (expire or 0)
            )
            await self._async_client.set(
                self._make_key(key), pickle.dumps(value), exptime=exptime
            )
        except Exception:
            pass

    async def adelete(self, key: str) -> None:
        """
        Asynchronously deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - Asyncio-safe for Memcached client.
            - The key is automatically namespaced.
        """
        try:
            await self._async_client.delete(self._make_key(key))
        except Exception:
            pass

    async def aclear(self) -> None:
        """
        Asynchronously removes all cache entries from Memcached.

        Memcached does not support namespace-based clearing, so this operation flushes
        the entire cache, removing all entries regardless of namespace.

        Notes:
            - Asyncio-safe for Memcached client.
            - This operation affects all keys in the Memcached instance.
            - Use with caution in shared environments.
        """
        try:
            await self._async_client.flush_all()
        except Exception:
            pass

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously checks if a cache key exists.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists, False otherwise.

        Notes:
            - Asyncio-safe for Memcached client.
            - Expired entries are not considered present.
        """
        try:
            value = await self._async_client.get(self._make_key(key))
            return value is not None
        except Exception:
            return False

    async def close(self) -> None:
        """
        Asynchronously closes both the async and sync Memcached clients.

        This method should be called when the backend is no longer needed to ensure
        all resources are released.

        Notes:
            - After calling this method, the backend cannot be used.
            - Closes both the async and sync clients.
        """
        try:
            await self._async_client.close()
            self._sync_client.close()
        except Exception:
            pass
