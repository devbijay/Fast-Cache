import pickle
import re
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Union

from apscheduler.schedulers.background import BackgroundScheduler

from .backend import CacheBackend


def _validate_namespace(namespace: str) -> str:
    if not re.match(r"^[A-Za-z0-9_]+$", namespace):
        raise ValueError("Invalid namespace: only alphanumeric and underscore allowed")
    return namespace


class PostgresBackend(CacheBackend):
    """
    PostgreSQL cache backend implementation.

    Uses an UNLOGGED TABLE for performance and lazy expiration.
    """

    def __init__(
        self,
        dsn: str,
        namespace: str = "fastapi",
        min_size: int = 1,
        max_size: int = 10,
        cleanup_interval: int = 30,
        auto_cleanup: bool = True,
    ) -> None:
        """
        Initializes a new instance of the PostgresBackend cache.

        This backend uses a PostgreSQL database to store cache entries in an
        UNLOGGED TABLE for improved performance. It supports both synchronous and
        asynchronous operations, lazy expiration, and periodic cleanup of expired
        entries.

        Args:
            dsn (str): The PostgreSQL DSN (Data Source Name) string used to connect
                to the database.
            namespace (str, optional): A namespace prefix for all cache keys. This
                allows multiple independent caches to share the same database table.
                Only alphanumeric characters and underscores are allowed. Defaults to "fastapi".
            min_size (int, optional): The minimum number of connections to maintain
                in the connection pool. Defaults to 1.
            max_size (int, optional): The maximum number of connections allowed in
                the connection pool. Defaults to 10.
            cleanup_interval (int, optional): The interval, in seconds, at which the
                background cleanup job runs to remove expired cache entries.
                Defaults to 30 seconds.
            auto_cleanup (bool, optional): If True, automatically starts the
                background cleanup scheduler on initialization. Defaults to True.

        Raises:
            ImportError: If the required `psycopg[pool]` package is not installed.
            ValueError: If the provided namespace contains invalid characters.

        Notes:
            - The backend creates the cache table and an index on the expiration
              column if they do not already exist.
            - The cleanup scheduler can be started or stopped manually.
            - Both synchronous and asynchronous connection pools are managed.
        """
        try:
            from psycopg_pool import AsyncConnectionPool, ConnectionPool
        except ImportError:
            raise ImportError(
                "PostgresBackend requires the 'psycopg[pool]' package. "
                "Install it with: pip install fast-cache[postgres]"
            )

        self._namespace = _validate_namespace(namespace)
        self._table_name = f"{namespace}_cache_store"

        # The pools are opened on creation and will auto-reopen if needed
        # when using the context manager (`with/async with`).
        self._sync_pool = ConnectionPool(
            conninfo=dsn, min_size=min_size, max_size=max_size, open=True
        )
        self._async_pool = AsyncConnectionPool(
            conninfo=dsn, min_size=min_size, max_size=max_size, open=False
        )
        self._create_unlogged_table_if_not_exists()

        self._cleanup_interval = cleanup_interval
        self._auto_cleanup = auto_cleanup

        self._scheduler = None
        self._scheduler_lock = threading.Lock()

        if self._auto_cleanup:
            self._start_cleanup_scheduler()

    def _start_cleanup_scheduler(self):
        """
        Starts the background scheduler for periodic cache cleanup.

        This method launches a background job that periodically deletes expired
        cache entries from the database table. If the scheduler is already running,
        this method does nothing.

        Thread-safe: uses a lock to prevent concurrent scheduler starts.

        Notes:
            - The cleanup interval is determined by the `cleanup_interval` parameter
              provided during initialization.
            - The scheduler runs in a background thread and does not block main
              application execution.
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
        Internal method that performs periodic cleanup of expired cache entries.

        This method is executed by the background scheduler at regular intervals.
        It deletes all rows from the cache table where the expiration time has
        passed.

        Notes:
            - This method is not intended to be called directly.
            - Uses a synchronous database connection.
            - Only entries with a non-null `expire_at` column and an expiration
              time earlier than the current time are deleted.
        """
        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._table_name} WHERE expire_at IS NOT NULL AND expire_at < NOW();"
                )
                conn.commit()

    def _create_unlogged_table_if_not_exists(self):
        """
        Creates the cache table and index in the PostgreSQL database if they do not exist.

        The table is created as UNLOGGED for better performance, as cache data can
        be regenerated if lost. An index is created on the `expire_at` column to
        speed up cleanup operations.

        Notes:
            - The table name is derived from the namespace.
            - This method is called automatically during initialization.
            - The table schema includes:
                - key (TEXT, primary key)
                - value (BYTEA, pickled Python object)
                - expire_at (TIMESTAMPTZ, nullable)
        """
        create_sql = f"""
        CREATE UNLOGGED TABLE IF NOT EXISTS {self._table_name} (
            key TEXT PRIMARY KEY,
            value BYTEA NOT NULL,
            expire_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_{self._table_name}_expire_at
        ON {self._table_name} (expire_at);
        """
        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_sql)
                conn.commit()

    def _make_key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    def _is_expired(self, expire_at: Optional[datetime]) -> bool:
        return expire_at is not None and expire_at < datetime.now(timezone.utc)

    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Stores a value in the cache under the specified key.

        If the key already exists, its value and expiration time are updated.
        Optionally, an expiration time can be set, after which the entry will be
        considered expired and eligible for deletion.

        Args:
            key (str): The cache key to store the value under.
            value (Any): The Python object/values to cache. It will be serialized using pickle.
            expire (Optional[Union[int, timedelta]], optional): The expiration time
                for the cache entry. Can be specified as an integer (seconds) or a
                timedelta. If None, the entry does not expire.

        Notes:
            - The key is automatically namespaced.
            - Expired entries are lazily deleted on access or by the cleanup job.
        """
        expire_at = self._compute_expire_at(expire)
        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._table_name} (key, value, expire_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value,
                                  expire_at = EXCLUDED.expire_at;
                    """,
                    (self._make_key(key), pickle.dumps(value), expire_at),
                )
                conn.commit()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache by key.

        If the key does not exist or the entry has expired, returns None. If the
        entry is expired, it is deleted from the cache (lazy deletion).

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found or expired.

        Notes:
            - The value is deserialized using pickle.
            - Expired entries are removed on access.
        """
        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT value, expire_at FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                value, expire_at = row
                if self._is_expired(expire_at):
                    self.delete(key)  # Lazy delete
                    return None
                return pickle.loads(value)

    def delete(self, key: str) -> None:
        """
        Deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - The key is automatically namespaced.
        """
        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                conn.commit()

    def has(self, key: str) -> bool:
        """
        Checks if a cache key exists and is not expired.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.

        Notes:
            - Expired entries are not considered present.
            - Does not remove expired entries; use `get` for lazy deletion.
        """
        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT expire_at FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                row = cur.fetchone()
                if not row:
                    return False
                return not self._is_expired(row[0])

    def clear(self) -> None:
        """
        Removes all cache entries in the current namespace.

        This method deletes all rows from the cache table whose keys match the
        current namespace prefix.

        Notes:
            - Only entries in the current namespace are affected.
            - This operation can be expensive if the cache is large.
        """

        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                # FIX: Use the dynamic table name
                cur.execute(
                    f"DELETE FROM {self._table_name} WHERE key LIKE %s;",
                    (self._make_key("%"),),
                )
                conn.commit()

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
            value (Any): The Python object/values to cache. It will be serialized using pickle.
            expire (Optional[Union[int, timedelta]], optional): The expiration time
                for the cache entry. Can be specified as an integer (seconds) or a
                timedelta. If None, the entry does not expire.

        Notes:
            - Uses the asynchronous connection pool.
            - The key is automatically namespaced.
        """
        await self._ensure_async_pool_open()
        expire_at = self._compute_expire_at(expire)
        async with self._async_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    INSERT INTO {self._table_name} (key, value, expire_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value,
                                  expire_at = EXCLUDED.expire_at;
                    """,
                    (self._make_key(key), pickle.dumps(value), expire_at),
                )
                await conn.commit()

    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieves a value from the cache by key.

        If the key does not exist or the entry has expired, returns None. If the
        entry is expired, it is deleted from the cache (lazy deletion).

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found or expired.

        Notes:
            - Uses the asynchronous connection pool.
            - The value is deserialized using pickle.
            - Expired entries are removed on access.
        """
        await self._ensure_async_pool_open()
        async with self._async_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT value, expire_at FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                value, expire_at = row
                if self._is_expired(expire_at):
                    await self.adelete(key)  # Lazy delete
                    return None
                return pickle.loads(value)

    async def adelete(self, key: str) -> None:
        """
        Asynchronously deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - Uses the asynchronous connection pool.
            - The key is automatically namespaced.
        """
        await self._ensure_async_pool_open()
        async with self._async_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"DELETE FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                await conn.commit()

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously checks if a cache key exists and is not expired.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.

        Notes:
            - Uses the asynchronous connection pool.
            - Expired entries are not considered present.
            - Does not remove expired entries; use `aget` for lazy deletion.
        """
        await self._ensure_async_pool_open()
        async with self._async_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT expire_at FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                row = await cur.fetchone()
                if not row:
                    return False
                return not self._is_expired(row[0])

    async def aclear(self) -> None:
        """
        Asynchronously removes all cache entries in the current namespace.

        This method deletes all rows from the cache table whose keys match the
        current namespace prefix.

        Notes:
            - Uses the asynchronous connection pool.
            - Only entries in the current namespace are affected.
            - This operation can be expensive if the cache is large.
        """
        await self._ensure_async_pool_open()
        async with self._async_pool.connection() as conn:
            async with conn.cursor() as cur:
                # FIX: Use the dynamic table name
                await cur.execute(
                    f"DELETE FROM {self._table_name} WHERE key LIKE %s;",
                    (self._make_key("%"),),
                )
                await conn.commit()

    async def aclose(self) -> None:
        """
        Asynchronously closes the connection pools and stops the cleanup scheduler.

        This method should be called when the backend is no longer needed to ensure
        all resources are released and background jobs are stopped.

        Notes:
            - Closes both synchronous and asynchronous connection pools.
            - Stops the background cleanup scheduler.
        """
        self._stop_cleanup_scheduler()
        if self._sync_pool:
            self._sync_pool.close()

        if self._async_pool:
            await self._async_pool.close()

    def close(self) -> None:
        """
        Closes the synchronous connection pool and stops the cleanup scheduler.

        This method should be called when the backend is no longer needed to ensure
        all resources are released and background jobs are stopped.

        Notes:
            - Only closes the synchronous connection pool.
            - Stops the background cleanup scheduler.
        """
        self._stop_cleanup_scheduler()
        if self._sync_pool:
            self._sync_pool.close()

    @staticmethod
    def _compute_expire_at(
        expire: Optional[Union[int, timedelta]],
    ) -> Optional[datetime]:
        """
        Computes the expiration datetime for a cache entry.

        Args:
            expire (Optional[Union[int, timedelta]]): The expiration time, either as
                an integer (seconds) or a timedelta. If None, the entry does not expire.

        Returns:
            Optional[datetime]: The UTC datetime when the entry should expire, or
            None if no expiration is set.

        Notes:
            - Used internally by set/aset methods.
        """
        if expire:
            delta = timedelta(seconds=expire) if isinstance(expire, int) else expire
            return datetime.now(timezone.utc) + delta
        return None

    async def _ensure_async_pool_open(self):
        """
        Ensures that the asynchronous connection pool is open before use.

        If the pool is not already open, it is opened asynchronously.

        Notes:
            - Used internally by all asynchronous methods.
            - Prevents errors from using a closed or uninitialized pool.
        """
        if not self._async_pool._opened:
            await self._async_pool.open()
