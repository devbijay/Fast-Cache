import asyncio
import inspect
import pickle
import time
from functools import wraps
from typing import Any, Optional, Union
from datetime import timedelta

from .backend import CacheBackend


def ensure_cleanup_task(method):
    @wraps(method)
    def sync_wrapper(self, *args, **kwargs):
        self._ensure_cleanup_task()
        return method(self, *args, **kwargs)

    @wraps(method)
    async def async_wrapper(self, *args, **kwargs):
        self._ensure_cleanup_task()
        return await method(self, *args, **kwargs)

    if inspect.iscoroutinefunction(method):
        return async_wrapper
    else:
        return sync_wrapper

class FirestoreBackend(CacheBackend):
    """
    Firebase Firestore cache backend with both sync and async support.
    Uses a 'expires_at' field for manual expiration checks.
    """

    def __init__(
        self,
        credential_path: Optional[str] = None,
        namespace: Optional[str] = "fastapi_cache",
        collection_name: Optional[str] = "cache_entries",
        cleanup_interval: int = 30,
        auto_cleanup: bool = True,
    ) -> None:
        """
        Initialize the Firestore backend.

        Args:
            credential_path (Optional[str]): Path to the Firebase Admin SDK credentials file.
                                            If None, uses GOOGLE_APPLICATION_CREDENTIALS from env variable.
            namespace (Optional[str]): Optional prefix for all cache keys. Defaults to "fastapi_cache".
            collection_name (Optional[str]): Name of the Firestore collection to use. Defaults to "cache_entries".
        """

        try:
            from google.oauth2 import service_account
            from google.cloud import firestore
            from google.cloud.firestore_v1.async_client import AsyncClient
            from google.cloud.firestore_v1.client import Client
        except ImportError:
            raise ImportError(
                "FirestoreBackend requires 'google-cloud-firestore'. "
                "Install with: pip install fastapi-cachekit[firestore]"
            )

        self._namespace = namespace or "cache"
        self._collection_name = collection_name or "cache_entries"

        self._cleanup_task = None
        self._cleanup_interval = cleanup_interval
        self._auto_cleanup = auto_cleanup

        if credential_path:
            # Explicitly load credentials from the provided path
            credentials = service_account.Credentials.from_service_account_file(
                credential_path
            )
            self._sync_db: Client = firestore.Client(credentials=credentials)
            self._async_db: AsyncClient = firestore.AsyncClient(credentials=credentials)
        else:
            # Rely on GOOGLE_APPLICATION_CREDENTIALS
            self._sync_db: Client = firestore.Client()
            self._async_db: AsyncClient = firestore.AsyncClient()

    @staticmethod
    def _compute_expire_at(expire: Optional[Union[int, timedelta]]) -> Optional[int]:
        if expire is not None:
            if isinstance(expire, timedelta):
                return int(time.time() + expire.total_seconds())
            else:
                return int(time.time() + expire)
        return None

    def _make_key(self, key: str) -> str:
        """
        Create a namespaced cache key.

        Args:
            key (str): The original cache key.

        Returns:
            str: The namespaced cache key.
        """
        # Firestore document IDs have limitations, using safe encoding
        import hashlib

        hashed_key = hashlib.sha256(f"{self._namespace}:{key}".encode()).hexdigest()
        return hashed_key

    def _is_expired(self, expires_at: Optional[int]) -> bool:
        """
        Check if an entry has expired.

        Args:
            expires_at (Optional[int]): The expiration time in epoch seconds.

        Returns:
            bool: True if the entry is expired, False otherwise.
        """
        return expires_at is not None and expires_at < time.time()

    @ensure_cleanup_task
    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieve a value from the cache.

        Args:
            key (str): The cache key.

        Returns:
            Optional[Any]: The cached value, or None if not found or expired.
        """
        doc_ref = self._sync_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if not self._is_expired(data.get("expires_at")):
                try:
                    return pickle.loads(data["value"])
                except (pickle.UnpicklingError, KeyError):
                    return None
        return None

    @ensure_cleanup_task
    def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Synchronously set a value in the cache.

        Args:
            key (str): The cache key.
            value (Any): The value to cache.
            expire (Optional[Union[int, timedelta]]): Expiration time in seconds or as timedelta.
                                                     If None, the entry never expires (or relies on Firestore's max TTL).
        """
        doc_ref = self._sync_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        data = {"value": pickle.dumps(value)}
        exptime = self._compute_expire_at(expire)
        if exptime is not None:
            data["expires_at"] = exptime

        doc_ref.set(data)

    def delete(self, key: str) -> None:
        """
        Synchronously delete a value from the cache.

        Args:
            key (str): The cache key.
        """
        doc_ref = self._sync_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        doc_ref.delete()

    def clear(self) -> None:
        """
        Synchronously clear all values from the namespace.
        Note: Firestore doesn't have direct namespace-based clearing.
        This implementation will delete all documents in the collection.
        Consider adding a query based on a namespaced field if needed.
        """
        docs = self._sync_db.collection(self._collection_name).stream()
        for doc in docs:
            doc.reference.delete()

    def has(self, key: str) -> bool:
        """
        Synchronously check if a key exists in the cache and is not expired.

        Args:
            key (str): The cache key.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.
        """
        doc_ref = self._sync_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return not self._is_expired(data.get("expires_at"))
        return False

    @ensure_cleanup_task
    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieve a value from the cache.

        Args:
            key (str): The cache key.

        Returns:
            Optional[Any]: The cached value, or None if not found or expired.
        """
        doc_ref = self._async_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if not self._is_expired(data.get("expires_at")):
                try:
                    return pickle.loads(data["value"])
                except (pickle.UnpicklingError, KeyError):
                    # Handle potential deserialization errors or missing value field
                    return None
        return None

    @ensure_cleanup_task
    async def aset(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """
        Asynchronously set a value in the cache.

        Args:
            key (str): The cache key.
            value (Any): The value to cache.
            expire (Optional[Union[int, timedelta]]): Expiration time in seconds or as timedelta.
                                                     If None, the entry never expires (or relies on Firestore's max TTL).
        """
        doc_ref = self._async_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        data = {"value": pickle.dumps(value)}
        exptime = self._compute_expire_at(expire)

        if expire is not None:
            data["expires_at"] = exptime

        await doc_ref.set(data)

    async def adelete(self, key: str) -> None:
        """
        Asynchronously delete a value from the cache.

        Args:
            key (str): The cache key.
        """
        doc_ref = self._async_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        await doc_ref.delete()

    async def aclear(self) -> None:
        """
        Asynchronously clear all values from the namespace.
        Note: Firestore doesn't have direct namespace-based clearing.
        This implementation will delete all documents in the collection.
        Consider adding a query based on a namespaced field if needed.
        """
        docs = self._async_db.collection(self._collection_name).stream()
        async for doc in docs:
            await doc.reference.delete()

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously check if a key exists in the cache and is not expired.

        Args:
            key (str): The cache key.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.
        """
        doc_ref = self._async_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return not self._is_expired(data.get("expires_at"))
        return False

    def close(self) -> None:
        """
        Close the synchronous Firestore client.
        """
        try:
            self._sync_db.close()
        except TypeError as e:
            return

    async def aclose(self) -> None:
        """
        Close the asynchronous Firestore client.
        """
        try:
            await self._async_db.close()
        except TypeError as e:
            return

    def _ensure_cleanup_task(self):
        if (
            getattr(self, "_auto_cleanup", True)
            and getattr(self, "_cleanup_task", None) is None
        ):
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self.cleanup_expired(self._cleanup_interval))
            except RuntimeError:
                pass

    async def cleanup_expired(self, interval_seconds: int = 30):
        """
        Periodically delete expired cache entries.
        Should be run as a background task.
        Args:
            interval_seconds (int): How often to run cleanup (default: 1 hour)
        """
        while True:
            now = int(time.time())
            expired_query = self._async_db.collection(self._collection_name).where(
                "expires_at", "<", now
            )
            batch = self._async_db.batch()
            count = 0
            async for doc in expired_query.stream():
                batch.delete(doc.reference)
                count += 1
                if count == 500:
                    await batch.commit()
                    batch = self._async_db.batch()
                    count = 0
            if count > 0:
                await batch.commit()
            await asyncio.sleep(interval_seconds)
