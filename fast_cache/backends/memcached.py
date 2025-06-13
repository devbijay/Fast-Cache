import pickle
from typing import Any, Optional, Union, Mapping
from datetime import timedelta
from .backend import CacheBackend

class MemcachedBackend(CacheBackend):
    """
    Memcached cache backend with both sync and async support.
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
        return f"{self._namespace}:{key}".encode()

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self._sync_client.get(self._make_key(key))
            return pickle.loads(value) if value else None
        except Exception:
            return None

    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        try:
            exptime = int(expire.total_seconds()) if isinstance(expire, timedelta) else (expire or 0)
            self._sync_client.set(self._make_key(key), pickle.dumps(value), expire=exptime)
        except Exception:
            pass

    def delete(self, key: str) -> None:
        try:
            self._sync_client.delete(self._make_key(key))
        except Exception:
            pass

    def clear(self) -> None:
        # Memcached does not support namespace flush, so flush all
        try:
            self._sync_client.flush_all()
        except Exception:
            pass

    def has(self, key: str) -> bool:
        try:
            return self._sync_client.get(self._make_key(key)) is not None
        except Exception:
            return False


    async def aget(self, key: str) -> Optional[Any]:
        try:
            value = await self._async_client.get(self._make_key(key))
            return pickle.loads(value) if value else None
        except Exception:
            return None

    async def aset(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        try:
            exptime = int(expire.total_seconds()) if isinstance(expire, timedelta) else (expire or 0)
            await self._async_client.set(self._make_key(key), pickle.dumps(value), exptime=exptime)
        except Exception:
            pass

    async def adelete(self, key: str) -> None:
        try:
            await self._async_client.delete(self._make_key(key))
        except Exception:
            pass


    async def aclear(self) -> None:
        try:
            await self._async_client.flush_all()
        except Exception:
            pass


    async def ahas(self, key: str) -> bool:
        try:
            value = await self._async_client.get(self._make_key(key))
            return value is not None
        except Exception:
            return False

    async def close(self) -> None:
        try:
            await self._async_client.close()
            self._sync_client.close()
        except Exception:
            pass