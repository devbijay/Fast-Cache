import asyncio
import threading
import time
from collections import OrderedDict
from datetime import timedelta
from typing import Any, Dict, Optional, Union, Tuple
from .backend import CacheBackend


class InMemoryBackend(CacheBackend):
    """
    In-memory cache backend implementation with namespace support,
    thread/async safety, and efficient expiration cleanup.

    Attributes:
        _namespace (str): Namespace prefix for all keys.
        _cache (OrderedDict[str, Tuple[Any, Optional[float]]]): The in-memory cache store.
        _lock (threading.Lock): Lock for thread safety.
        _async_lock (asyncio.Lock): Lock for async safety.
        _cleanup_task (Optional[asyncio.Task]): Background cleanup task.
        _max_size (Optional[int]): Maximum number of items (for LRU eviction).
    """

    def __init__(
        self, namespace: str = "fastapi-cache", max_size: Optional[int] = None
    ) -> None:
        """
        Initialize the in-memory cache backend.

        Args:
            namespace (str): Namespace prefix for all keys (default: "fastapi-cache").
            max_size (Optional[int]): Optional maximum number of items (LRU eviction if set).
        """
        self._namespace = namespace
        self._cache: "OrderedDict[str, Tuple[Any, Optional[float]]]" = OrderedDict()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._max_size = max_size

    def _make_key(self, key: str) -> str:
        """
        Create a namespaced cache key.

        Args:
            key (str): The original key.

        Returns:
            str: The namespaced key.
        """
        return f"{self._namespace}:{key}"

    def _is_expired(self, expire_time: Optional[float]) -> bool:
        """
        Check if a cache entry is expired.

        Args:
            expire_time (Optional[float]): The expiration timestamp.

        Returns:
            bool: True if expired, False otherwise.
        """
        if expire_time is None:
            return False
        return time.monotonic() > expire_time

    def _get_expire_time(
        self, expire: Optional[Union[int, timedelta]]
    ) -> Optional[float]:
        """
        Calculate the expiration timestamp.

        Args:
            expire (Optional[Union[int, timedelta]]): Expiration in seconds or timedelta.

        Returns:
            Optional[float]: The expiration timestamp, or None if no expiration.
        """
        if expire is None:
            return None
        seconds = expire.total_seconds() if isinstance(expire, timedelta) else expire
        return time.monotonic() + seconds

    def _evict_if_needed(self):
        """
        Evict the least recently used items if the cache exceeds max_size.
        """
        if self._max_size is not None:
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)  # Remove oldest (LRU)

    def _cleanup(self) -> None:
        """
        Remove expired items from the cache.
        """
        now = time.monotonic()
        keys_to_delete = [
            k
            for k, (_, exp) in list(self._cache.items())
            if exp is not None and now > exp
        ]
        for k in keys_to_delete:
            self._cache.pop(k, None)

    async def _cleanup_expired(self) -> None:
        """
        Periodically clean up expired items in the background.
        """
        while True:
            await asyncio.sleep(60)
            async with self._async_lock:
                self._cleanup()

    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieve a value from the cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[Any]: The cached value, or None if not found or expired.
        """
        k = self._make_key(key)
        with self._lock:
            item = self._cache.get(k)
            if item:
                value, expire_time = item
                if not self._is_expired(expire_time):
                    # Move to end for LRU
                    self._cache.move_to_end(k)
                    return value
                self._cache.pop(k, None)
            return None

    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Synchronously set a value in the cache.

        Args:
            key (str): The key under which to store the value.
            value (Any): The value to store.
            expire (Optional[Union[int, timedelta]]): Expiration time in seconds or as timedelta.
        """
        k = self._make_key(key)
        expire_time = self._get_expire_time(expire)
        with self._lock:
            self._cache[k] = (value, expire_time)
            self._cache.move_to_end(k)
            self._evict_if_needed()
            self._cleanup()

    def delete(self, key: str) -> None:
        """
        Synchronously delete a value from the cache.

        Args:
            key (str): The key to delete.
        """
        k = self._make_key(key)
        with self._lock:
            self._cache.pop(k, None)

    def clear(self) -> None:
        """
        Synchronously clear all values from the cache.
        """
        prefix = f"{self._namespace}:"
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                self._cache.pop(k, None)

    def has(self, key: str) -> bool:
        """
        Synchronously check if a key exists in the cache.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.
        """
        k = self._make_key(key)
        with self._lock:
            item = self._cache.get(k)
            if item:
                _, expire_time = item
                if not self._is_expired(expire_time):
                    self._cache.move_to_end(k)
                    return True
                self._cache.pop(k, None)
            return False

    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieve a value from the cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[Any]: The cached value, or None if not found or expired.
        """
        k = self._make_key(key)
        async with self._async_lock:
            item = self._cache.get(k)
            if item:
                value, expire_time = item
                if not self._is_expired(expire_time):
                    self._cache.move_to_end(k)
                    return value
                self._cache.pop(k, None)
            return None

    async def aset(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Asynchronously set a value in the cache.

        Args:
            key (str): The key under which to store the value.
            value (Any): The value to store.
            expire (Optional[Union[int, timedelta]]): Expiration time in seconds or as timedelta.
        """
        k = self._make_key(key)
        expire_time = self._get_expire_time(expire)
        async with self._async_lock:
            self._cache[k] = (value, expire_time)
            self._cache.move_to_end(k)
            self._evict_if_needed()
            self._cleanup()
            # Start cleanup task if not already running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_expired())

    async def adelete(self, key: str) -> None:
        """
        Asynchronously delete a value from the cache.

        Args:
            key (str): The key to delete.
        """
        k = self._make_key(key)
        async with self._async_lock:
            self._cache.pop(k, None)

    async def aclear(self) -> None:
        """
        Asynchronously clear all values from the cache.
        """
        prefix = f"{self._namespace}:"
        async with self._async_lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                self._cache.pop(k, None)

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously check if a key exists in the cache.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.
        """
        k = self._make_key(key)
        async with self._async_lock:
            item = self._cache.get(k)
            if item:
                _, expire_time = item
                if not self._is_expired(expire_time):
                    self._cache.move_to_end(k)
                    return True
                self._cache.pop(k, None)
            return False

    async def close(self) -> None:
        """
        Asynchronously close the backend and cancel the cleanup task if running.
        """
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
