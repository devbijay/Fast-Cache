import asyncio
import threading
import time
from collections import OrderedDict
from datetime import timedelta
from typing import Any, Optional, Union, Tuple

from apscheduler.schedulers.background import BackgroundScheduler

from .backend import CacheBackend


class InMemoryBackend(CacheBackend):
    """
    Initializes a new instance of the InMemoryBackend cache.

    This backend provides an in-memory cache with optional LRU (Least Recently Used)
    eviction, namespace support, thread and async safety, and automatic periodic
    cleanup of expired items. It is suitable for single-process, multi-threaded, or
    asyncio-based applications.

    Args:
        namespace (str, optional): A namespace prefix for all cache keys. This allows
            multiple independent caches to share the same process. Defaults to "fastapi-cache".
        max_size (Optional[int], optional): The maximum number of items to store in the
            cache. If set, the cache will evict the least recently used items when the
            limit is exceeded. If None, the cache size is unlimited. Defaults to None.
        cleanup_interval (int, optional): The interval, in seconds, at which the
            background cleanup job runs to remove expired cache entries. Defaults to 30.

    Notes:
        - The backend uses an OrderedDict to maintain LRU order.
        - Both synchronous (thread-safe) and asynchronous (asyncio-safe) operations are supported.
        - Expired items are removed automatically by a background scheduler.
        - This backend is not suitable for multi-process or distributed environments.
    """

    def __init__(
        self,
        namespace: str = "fastapi-cache",
        max_size: Optional[int] = None,
        cleanup_interval: int = 30,
    ) -> None:
        """
        Initialize the in-memory cache backend.

        Args:
            namespace: Namespace prefix for all keys.
            max_size: Optional maximum number of items (LRU eviction if set).
            cleanup_interval: Interval in seconds for background cleanup.
        """
        self._namespace = namespace
        self._cache: OrderedDict[str, Tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval

        self._scheduler = None
        self._scheduler_lock = threading.Lock()
        self._start_cleanup_scheduler()

    def _start_cleanup_scheduler(self):
        """
        Starts the background scheduler for periodic cleanup of expired cache items.

        This method launches a background job that periodically deletes expired
        cache entries from the in-memory store. If the scheduler is already running,
        this method does nothing.

        Thread-safe: uses a lock to prevent concurrent scheduler starts.

        Notes:
            - The cleanup interval is determined by the `cleanup_interval` parameter
              provided during initialization.
            - The scheduler runs in a background thread and does not block main
              application execution.
            - The scheduler is started automatically on initialization.
        """
        with self._scheduler_lock:
            if self._scheduler is not None:
                return
            self._scheduler = BackgroundScheduler()
            self._scheduler.add_job(
                self._run_cleanup_job,
                "interval",
                seconds=self._cleanup_interval,
                id="cache_cleanup",
                max_instances=1,
            )
            self._scheduler.start()

    def _stop_cleanup_scheduler(self):
        """
        Stops the background cleanup scheduler if it is running.

        This method shuts down the background scheduler responsible for removing
        expired cache entries. If the scheduler is not running, this method does
        nothing.

        Thread-safe: uses a lock to prevent concurrent shutdowns.

        Notes:
            - This method is called automatically when closing the backend.
            - The scheduler is stopped without waiting for currently running jobs to finish.
        """
        with self._scheduler_lock:
            if self._scheduler:
                self._scheduler.shutdown(wait=False)
                self._scheduler = None

    def _run_cleanup_job(self):
        """
        Removes all expired items from the cache.

        This method is executed by the background scheduler at regular intervals.
        It iterates through all cache entries and deletes those whose expiration
        time has passed.

        Notes:
            - This method is not intended to be called directly.
            - Uses a monotonic clock for expiration checks.
            - Only entries with a non-null expiration time and an expiration
              time earlier than the current time are deleted.
        """
        while True:
            now = time.monotonic()
            keys_to_delete = [
                k
                for k, (_, exp) in list(self._cache.items())
                if exp is not None and now > exp
            ]
            for k in keys_to_delete:
                self._cache.pop(k, None)

    def _make_key(self, key: str) -> str:
        """
        Creates a namespaced cache key.

        This method prepends the namespace to the provided key to avoid key collisions
        between different cache namespaces.

        Args:
            key (str): The original cache key.

        Returns:
            str: The namespaced cache key.

        Notes:
            - All cache operations use namespaced keys internally.
        """
        return f"{self._namespace}:{key}"

    def _is_expired(self, expire_time: Optional[float]) -> bool:
        """
        Checks if a cache entry is expired.

        Args:
            expire_time (Optional[float]): The expiration timestamp (monotonic time).

        Returns:
            bool: True if the entry is expired, False otherwise.

        Notes:
            - If expire_time is None, the entry does not expire.
            - Uses a monotonic clock for reliable expiration checks.
        """
        if expire_time is None:
            return False
        return time.monotonic() > expire_time

    def _get_expire_time(
        self, expire: Optional[Union[int, timedelta]]
    ) -> Optional[float]:
        """
        Calculates the expiration timestamp for a cache entry.

        Args:
            expire (Optional[Union[int, timedelta]]): The expiration time, either as
                an integer (seconds) or a timedelta. If None, the entry does not expire.

        Returns:
            Optional[float]: The expiration timestamp (monotonic time), or None if no expiration.

        Notes:
            - Used internally by set/aset methods.
            - Ensures consistent expiration regardless of system clock changes.
        """
        if expire is None:
            return None
        seconds = expire.total_seconds() if isinstance(expire, timedelta) else expire
        return time.monotonic() + seconds

    def _evict_if_needed(self):
        """
        Evicts the least recently used items if the cache exceeds max_size.

        If the cache size exceeds the configured maximum, this method removes
        the oldest (least recently used) items until the size constraint is met.

        Notes:
            - Only applies if max_size is set.
            - Called automatically after each set/aset operation.
        """
        if self._max_size is not None:
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)  # Remove oldest (LRU)

    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieves a value from the cache by key.

        If the key does not exist or the entry has expired, returns None. If the
        entry is expired, it is deleted from the cache (lazy deletion). Accessing
        an item moves it to the end of the LRU order.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found or expired.

        Notes:
            - Thread-safe.
            - Expired entries are removed on access.
            - Updates LRU order on access.
        """
        k = self._make_key(key)
        with self._lock:
            item = self._cache.get(k)
            if item:
                value, expire_time = item
                if not self._is_expired(expire_time):
                    self._cache.move_to_end(k)
                    return value
                self._cache.pop(k, None)
            return None

    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Synchronously stores a value in the cache under the specified key.

        If the key already exists, its value and expiration time are updated.
        Optionally, an expiration time can be set, after which the entry will be
        considered expired and eligible for deletion. Setting an item moves it to
        the end of the LRU order.

        Args:
            key (str): The cache key to store the value under.
            value (Any): The Python object to cache.
            expire (Optional[Union[int, timedelta]], optional): The expiration time
                for the cache entry. Can be specified as an integer (seconds) or a
                timedelta. If None, the entry does not expire.

        Notes:
            - Thread-safe.
            - Triggers LRU eviction if max_size is set.
            - Updates LRU order on set.
        """
        k = self._make_key(key)
        expire_time = self._get_expire_time(expire)
        with self._lock:
            self._cache[k] = (value, expire_time)
            self._cache.move_to_end(k)
            self._evict_if_needed()

    def delete(self, key: str) -> None:
        """
        Synchronously deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - Thread-safe.
            - The key is automatically namespaced.
        """
        k = self._make_key(key)
        with self._lock:
            self._cache.pop(k, None)

    def clear(self) -> None:
        """
        Synchronously removes all cache entries in the current namespace.

        This method deletes all entries whose keys match the current namespace prefix.

        Notes:
            - Thread-safe.
            - Only entries in the current namespace are affected.
            - This operation can be expensive if the cache is large.
        """
        prefix = f"{self._namespace}:"
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                self._cache.pop(k, None)

    def has(self, key: str) -> bool:
        """
        Synchronously checks if a cache key exists and is not expired.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.

        Notes:
            - Thread-safe.
            - Expired entries are not considered present and are removed on check.
            - Updates LRU order on access.
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
        Asynchronously retrieves a value from the cache by key.

        If the key does not exist or the entry has expired, returns None. If the
        entry is expired, it is deleted from the cache (lazy deletion). Accessing
        an item moves it to the end of the LRU order.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found or expired.

        Notes:
            - Asyncio-safe.
            - Expired entries are removed on access.
            - Updates LRU order on access.
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
        Asynchronously stores a value in the cache under the specified key.

        If the key already exists, its value and expiration time are updated.
        Optionally, an expiration time can be set, after which the entry will be
        considered expired and eligible for deletion. Setting an item moves it to
        the end of the LRU order.

        Args:
            key (str): The cache key to store the value under.
            value (Any): The Python object to cache.
            expire (Optional[Union[int, timedelta]], optional): The expiration time
                for the cache entry. Can be specified as an integer (seconds) or a
                timedelta. If None, the entry does not expire.

        Notes:
            - Asyncio-safe.
            - Triggers LRU eviction if max_size is set.
            - Updates LRU order on set.
        """
        k = self._make_key(key)
        expire_time = self._get_expire_time(expire)
        async with self._async_lock:
            self._cache[k] = (value, expire_time)
            self._cache.move_to_end(k)
            self._evict_if_needed()

    async def adelete(self, key: str) -> None:
        """
        Asynchronously deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - Asyncio-safe.
            - The key is automatically namespaced.
        """
        k = self._make_key(key)
        async with self._async_lock:
            self._cache.pop(k, None)

    async def aclear(self) -> None:
        """
        Asynchronously removes all cache entries in the current namespace.

        This method deletes all entries whose keys match the current namespace prefix.

        Notes:
            - Asyncio-safe.
            - Only entries in the current namespace are affected.
            - This operation can be expensive if the cache is large.
        """
        prefix = f"{self._namespace}:"
        async with self._async_lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                self._cache.pop(k, None)

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously checks if a cache key exists and is not expired.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.

        Notes:
            - Asyncio-safe.
            - Expired entries are not considered present and are removed on check.
            - Updates LRU order on access.
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

    def close(self) -> None:
        """
        Closes the backend and stops the background cleanup scheduler.

        This method should be called when the backend is no longer needed to ensure
        all resources are released and background jobs are stopped.

        Notes:
            - After calling this method, the cache is cleared and cannot be used.
            - The background cleanup scheduler is stopped.
        """
        self._stop_cleanup_scheduler()
        self._cache = None
