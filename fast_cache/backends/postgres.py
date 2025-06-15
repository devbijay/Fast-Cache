import pickle
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Union
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
    ) -> None:
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

    def _validate_namespace(namespace: str) -> str:
        if not re.match(r"^[A-Za-z0-9_]+$", namespace):
            raise ValueError(
                "Invalid namespace: only alphanumeric and underscore allowed"
            )
        return namespace

    def _create_unlogged_table_if_not_exists(self):
        """Create the cache table if it doesn't exist."""
        # The index on expire_at is for efficient periodic cleanup jobs,
        # though not used in the lazy-delete implementation.
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
        return expire_at is not None and expire_at < datetime.now(
            timezone.utc
        )

    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        expire_at = None
        if expire:
            delta = (
                timedelta(seconds=expire)
                if isinstance(expire, int)
                else expire
            )
            expire_at = datetime.now(timezone.utc) + delta

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
        with self._sync_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                conn.commit()

    def has(self, key: str) -> bool:
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
        """Clear all keys in the current namespace from the cache."""
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

        if not self._async_pool._opened:
            await self._async_pool.open()

        expire_at = None
        if expire:
            delta = (
                timedelta(seconds=expire)
                if isinstance(expire, int)
                else expire
            )
            expire_at = datetime.now(timezone.utc) + delta

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
        if not self._async_pool._opened:
            await self._async_pool.open()
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
        if not self._async_pool._opened:
            await self._async_pool.open()
        async with self._async_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"DELETE FROM {self._table_name} WHERE key = %s;",
                    (self._make_key(key),),
                )
                await conn.commit()

    async def ahas(self, key: str) -> bool:
        if not self._async_pool._opened:
            await self._async_pool.open()
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
        """Asynchronously clear all keys in the current namespace."""
        if not self._async_pool._opened:
            await self._async_pool.open()
        async with self._async_pool.connection() as conn:
            async with conn.cursor() as cur:
                # FIX: Use the dynamic table name
                await cur.execute(
                    f"DELETE FROM {self._table_name} WHERE key LIKE %s;",
                    (self._make_key("%"),),
                )
                await conn.commit()

    async def close(self) -> None:
        self._sync_pool.close()
        await self._async_pool.close()
