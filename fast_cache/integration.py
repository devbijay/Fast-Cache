from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Optional, Callable, Union
from datetime import timedelta
import inspect
from functools import wraps
from .backends.backend import CacheBackend


class FastAPICache:
    """FastAPI Cache Extension"""

    def __init__(self) -> None:
        self._backend: Optional[CacheBackend] = None
        self._app: Optional[FastAPI] = None
        self._default_expire: Optional[Union[int, timedelta]] = None

    def get_cache(self) -> CacheBackend:
        """
        Dependency injection method that returns the cache backend.

        Returns:
            CacheBackend: The configured cache backend instance

        Raises:
            RuntimeError: If cache is not initialized
        """
        if self._backend is None:
            raise RuntimeError("Cache not initialized. Call init_app first.")
        return self._backend

    def cached(
        self,
        expire: Optional[Union[int, timedelta]] = None,
        key_builder: Optional[Callable[..., str]] = None,
        namespace: Optional[str] = None,
    ):
        """
        Decorator for caching function results.

        Args:
            expire: Expiration time in seconds or timedelta
            key_builder: Custom function to build cache key
            namespace: Optional namespace for the cache key
        """

        def decorator(func: Callable) -> Callable:
            is_async = inspect.iscoroutinefunction(func)

            def build_cache_key(*args, **kwargs) -> str:
                if key_builder is not None:
                    key = key_builder(*args, **kwargs)
                else:
                    # Default key building logic
                    key = f"{func.__module__}:{func.__name__}:{str(args)}:{str(kwargs)}"

                if namespace:
                    key = f"{namespace}:{key}"

                return key

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self._backend:
                    return await func(*args, **kwargs)

                # Skip cache if explicitly requested
                if kwargs.pop("skip_cache", False):
                    return await func(*args, **kwargs)

                cache_key = build_cache_key(*args, **kwargs)

                # Try to get from cache
                cached_value = await self._backend.aget(cache_key)
                if cached_value is not None:
                    return cached_value

                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self._backend.aset(
                    cache_key, result, expire=expire or self._default_expire
                )
                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self._backend:
                    return func(*args, **kwargs)

                # Skip cache if explicitly requested
                if kwargs.pop("skip_cache", False):
                    return func(*args, **kwargs)

                cache_key = build_cache_key(*args, **kwargs)

                # Try to get from cache
                cached_value = self._backend.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Execute function and cache result
                result = func(*args, **kwargs)
                self._backend.set(
                    cache_key, result, expire=expire or self._default_expire
                )
                return result

            return async_wrapper if is_async else sync_wrapper

        return decorator

    @asynccontextmanager
    async def lifespan_handler(self, app: FastAPI):
        """Lifespan context manager for FastAPI"""
        if not hasattr(app, "state"):
            app.state = {}
        app.state["cache"] = self
        yield
        self._backend = None
        self._app = None

    def init_app(
        self,
        app: FastAPI,
        backend: CacheBackend,
        default_expire: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the cache extension.

        Args:
            app: FastAPI application instance
            backend: Cache backend instance
            default_expire: Default expiration time for cached items
        """
        self._backend = backend
        self._app = app
        self._default_expire = default_expire
