from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Optional, Callable, Union, AsyncIterator, Any
from datetime import timedelta
import inspect
from functools import wraps
from .backends.backend import CacheBackend

_CACHE_MISS = object()


class FastAPICache:
    """
    FastAPI Cache Extension.

    This class provides caching utilities for FastAPI applications, including
    decorator-based caching and dependency-injection-based backend access.
    """

    def __init__(self) -> None:
        """
        Initialize the FastAPICache instance.
        """
        self._backend: Optional[CacheBackend] = None
        self._app: Optional[FastAPI] = None
        self._default_expire: Optional[Union[int, timedelta]] = None

    def get_cache(self) -> CacheBackend:
        """
        Get the configured cache backend for dependency injection.

        Returns:
            CacheBackend: The configured cache backend instance.

        Raises:
            RuntimeError: If the cache is not initialized.
        """
        if self._backend is None:
            raise RuntimeError("Cache not initialized. Call init_app first.")
        return self._backend

    def cached(
        self,
        expire: Optional[Union[int, timedelta]] = None,
        key_builder: Optional[Callable[..., str]] = None,
        namespace: Optional[str] = None,
        stampede_protection: bool = True,
        lock_timeout: int = 30,
        lock_wait: float = 5.0,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for caching function results.

        Args:
            expire (Optional[Union[int, timedelta]]): Expiration time in seconds or as a timedelta.
            key_builder (Optional[Callable[..., str]]): Custom function to build the cache key.
            namespace (Optional[str]): Optional namespace for the cache key.
            stampede_protection (bool): Enable distributed lock to prevent thundering herd
                on cache miss. Requires a backend that supports locking (e.g., Redis).
                Silently skipped for backends without lock support. Defaults to True.
            lock_timeout (int): Lock auto-expiry in seconds (deadlock protection). Defaults to 30.
            lock_wait (float): Max seconds to wait for the lock before falling back
                to a direct function call. Defaults to 5.0.

        Returns:
            Callable: A decorator that caches the function result.
        """

        def decorator(func: Callable) -> Callable[..., Any]:
            """
            The actual decorator that wraps the function.

            Args:
                func (Callable): The function to be cached.

            Returns:
                Callable: The wrapped function with caching.
            """
            is_async = inspect.iscoroutinefunction(func)

            def build_cache_key(*args, **kwargs) -> str:
                """
                Build the cache key for the function call.

                Args:
                    *args: Positional arguments for the function.
                    **kwargs: Keyword arguments for the function.

                Returns:
                    str: The generated cache key.
                """
                if key_builder is not None:
                    key = key_builder(*args, **kwargs)
                else:
                    # Default key building logic
                    key = f"{func.__module__}:{func.__name__}:{str(args)}:{str(kwargs)}"

                if namespace:
                    key = f"{namespace}:{key}"

                return key

            def _backend_supports_locking() -> bool:
                return self._backend is not None and hasattr(
                    self._backend, "acquire_lock"
                )

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                """
                Async wrapper for caching.

                Args:
                    *args: Positional arguments.
                    **kwargs: Keyword arguments.

                Returns:
                    Any: The cached or computed result.
                """
                if not self._backend:
                    return await func(*args, **kwargs)

                # Skip cache if explicitly requested
                if kwargs.pop("skip_cache", False):
                    return await func(*args, **kwargs)

                cache_key = build_cache_key(*args, **kwargs)
                effective_expire = expire or self._default_expire

                # Fast path: cache hit
                cached_value = await self._backend.aget(
                    cache_key, default=_CACHE_MISS
                )
                if cached_value is not _CACHE_MISS:
                    return cached_value

                # Stampede protection: distributed lock
                if stampede_protection and _backend_supports_locking():
                    token = await self._backend.aacquire_lock(
                        cache_key, timeout=lock_timeout, wait=lock_wait
                    )

                    if token is not None:
                        # We are the lock holder — rebuild the value
                        try:
                            result = await func(*args, **kwargs)
                            await self._backend.aset(
                                cache_key, result, expire=effective_expire
                            )
                            return result
                        finally:
                            await self._backend.arelease_lock(cache_key, token)
                    else:
                        # Another process is rebuilding — check if it finished
                        cached_value = await self._backend.aget(
                            cache_key, default=_CACHE_MISS
                        )
                        if cached_value is not _CACHE_MISS:
                            return cached_value

                        # Still no value — fallback: call function directly
                        return await func(*args, **kwargs)

                # No stampede protection — original behavior
                result = await func(*args, **kwargs)
                await self._backend.aset(
                    cache_key, result, expire=effective_expire
                )
                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """
                Sync wrapper for caching.

                Args:
                    *args: Positional arguments.
                    **kwargs: Keyword arguments.

                Returns:
                    Any: The cached or computed result.
                """
                if not self._backend:
                    return func(*args, **kwargs)

                # Skip cache if explicitly requested
                if kwargs.pop("skip_cache", False):
                    return func(*args, **kwargs)

                cache_key = build_cache_key(*args, **kwargs)
                effective_expire = expire or self._default_expire

                # Fast path: cache hit
                cached_value = self._backend.get(
                    cache_key, default=_CACHE_MISS
                )
                if cached_value is not _CACHE_MISS:
                    return cached_value

                # Stampede protection: distributed lock
                if stampede_protection and _backend_supports_locking():
                    token = self._backend.acquire_lock(
                        cache_key, timeout=lock_timeout, wait=lock_wait
                    )

                    if token is not None:
                        # We are the lock holder — rebuild the value
                        try:
                            result = func(*args, **kwargs)
                            self._backend.set(
                                cache_key, result, expire=effective_expire
                            )
                            return result
                        finally:
                            self._backend.release_lock(cache_key, token)
                    else:
                        # Another process is rebuilding — check if it finished
                        cached_value = self._backend.get(
                            cache_key, default=_CACHE_MISS
                        )
                        if cached_value is not _CACHE_MISS:
                            return cached_value

                        # Still no value — fallback: call function directly
                        return func(*args, **kwargs)

                # No stampede protection — original behavior
                result = func(*args, **kwargs)
                self._backend.set(
                    cache_key, result, expire=effective_expire
                )
                return result

            return async_wrapper if is_async else sync_wrapper

        return decorator

    @asynccontextmanager
    async def lifespan_handler(self, app: FastAPI) -> AsyncIterator[None]:
        """
        Lifespan context manager for FastAPI.

        This can be used as the `lifespan` argument to FastAPI to manage
        cache lifecycle.

        Args:
            app (FastAPI): The FastAPI application instance.

        Yields:
            None
        """
        if not hasattr(app, "state"):
            app.state = {}
        app.state["cache"] = self

        try:
            yield
        finally:
            if self._backend:
                close = getattr(self._backend, "aclose", None)
                if close:
                    await close()
                else:
                    close = getattr(self._backend, "close", None)
                    if close:
                        close()

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
            app (FastAPI): FastAPI application instance.
            backend (CacheBackend): Cache backend instance.
            default_expire (Optional[Union[int, timedelta]]): Default expiration time for cached items.
        """
        self._backend = backend
        self._app = app
        self._default_expire = default_expire
