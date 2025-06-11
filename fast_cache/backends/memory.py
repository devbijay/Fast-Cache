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
    """

    def __init__(self, namespace: str = "fastapi-cache", max_size: Optional[int] = None) -> None:
        """
        Args:
            namespace: Namespace prefix for all keys (default: "fastapi-cache")
            max_size: Optional maximum number of items (LRU eviction if set)
        """
        self._namespace = namespace
        self._cache: "OrderedDict[str, Tuple[Any, Optional[float]]]" = OrderedDict()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._max_size = max_size

    def _make_key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    def _is_expired(self, expire_time: Optional[float]) -> bool:
        if expire_time is None:
            return False
        return time.monotonic() > expire_time

    def _get_expire_time(self, expire: Optional[Union[int, timedelta]]) -> Optional[float]:
        if expire is None:
            return None
        seconds = expire.total_seconds() if isinstance(expire, timedelta) else expire
        return time.monotonic() + seconds

    def _evict_if_needed(self):
        if self._max_size is not None:
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)  # Remove oldest (LRU)

    def _cleanup(self) -> None:
        now = time.monotonic()
        keys_to_delete = [k for k, (_, exp) in list(self._cache.items()) if exp is not None and now > exp]
        for k in keys_to_delete:
            self._cache.pop(k, None)

    async def _cleanup_expired(self) -> None:
        while True:
            await asyncio.sleep(60)
            async with self._async_lock:
                self._cleanup()


    def get(self, key: str) -> Any:
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

    def set(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> None:
        k = self._make_key(key)
        expire_time = self._get_expire_time(expire)
        with self._lock:
            self._cache[k] = (value, expire_time)
            self._cache.move_to_end(k)
            self._evict_if_needed()
            self._cleanup()

    def delete(self, key: str) -> None:
        k = self._make_key(key)
        with self._lock:
            self._cache.pop(k, None)

    def clear(self) -> None:
        prefix = f"{self._namespace}:"
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                self._cache.pop(k, None)

    def has(self, key: str) -> bool:
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


    async def aget(self, key: str) -> Any:
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

    async def aset(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> None:
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
        k = self._make_key(key)
        async with self._async_lock:
            self._cache.pop(k, None)

    async def aclear(self) -> None:
        prefix = f"{self._namespace}:"
        async with self._async_lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                self._cache.pop(k, None)

    async def ahas(self, key: str) -> bool:
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
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass