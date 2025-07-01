import pickle
import threading
import time
from typing import Any, Optional, Union
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from .backend import CacheBackend


class FirestoreBackend(CacheBackend):
    """
    Initializes a new instance of the FirestoreBackend cache.

    This backend provides a cache using Google Cloud Firestore as the storage layer.
    It supports both synchronous and asynchronous operations, manual expiration
    management, and optional periodic cleanup of expired entries.

    Args:
        credential_path (Optional[str], optional): Path to the Firebase Admin SDK
            credentials file. If None, uses the GOOGLE_APPLICATION_CREDENTIALS
            environment variable. Defaults to None.
        namespace (Optional[str], optional): Optional prefix for all cache keys.
            Defaults to "fastapi_cache".
        collection_name (Optional[str], optional): Name of the Firestore collection
            to use for storing cache entries. Defaults to "cache_entries".
        cleanup_interval (int, optional): Interval in seconds for periodic cleanup
            of expired entries. Defaults to 30.
        auto_cleanup (bool, optional): Whether to automatically start the cleanup
            scheduler on initialization. Defaults to True.

    Raises:
        ImportError: If the required `google-cloud-firestore` package is not installed.

    Notes:
        - The backend uses a hashed, namespaced key for each Firestore document.
        - Expired entries are managed via a custom `expires_at` field.
        - Both synchronous and asynchronous Firestore clients are initialized.
        - The cleanup scheduler can be started or stopped manually.
    """

    def __init__(
        self,
        credential_path: Optional[str] = None,
        namespace: Optional[str] = "fastapi_cache",
        collection_name: Optional[str] = "cache_entries",
        cleanup_interval: int = 30,
        auto_cleanup: bool = True,
    ) -> None:
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

        self._scheduler = None
        self._scheduler_lock = threading.Lock()

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

        if self._auto_cleanup:
            self._start_cleanup_scheduler()

    @staticmethod
    def _compute_expire_at(expire: Optional[Union[int, timedelta]]) -> Optional[int]:
        """
        Computes the expiration timestamp for a cache entry.

        Args:
            expire (Optional[Union[int, timedelta]]): The expiration time, either as
                an integer (seconds) or a timedelta. If None, the entry does not expire.

        Returns:
            Optional[int]: The expiration time as a Unix epoch timestamp in seconds,
            or None if no expiration is set.

        Notes:
            - Used internally by set/aset methods.
            - Uses the current system time.
        """
        if expire is not None:
            if isinstance(expire, timedelta):
                return int(time.time() + expire.total_seconds())
            else:
                return int(time.time() + expire)
        return None

    def _make_key(self, key: str) -> str:
        """
        Creates a namespaced, hashed cache key suitable for Firestore document IDs.

        Firestore document IDs have character and length restrictions, so this method
        applies SHA-256 hashing to the namespaced key.

        Args:
            key (str): The original cache key.

        Returns:
            str: The hashed, namespaced cache key.

        Notes:
            - All cache operations use hashed, namespaced keys internally.
            - Prevents key collisions and ensures Firestore compatibility.
        """

        # Firestore document IDs have limitations, using safe encoding
        import hashlib

        hashed_key = hashlib.sha256(f"{self._namespace}:{key}".encode()).hexdigest()
        return hashed_key

    def _is_expired(self, expires_at: Optional[int]) -> bool:
        """
        Checks if a cache entry is expired.

        Args:
            expires_at (Optional[int]): The expiration time as a Unix epoch timestamp in seconds.

        Returns:
            bool: True if the entry is expired, False otherwise.

        Notes:
            - If expires_at is None, the entry does not expire.
            - Uses the current system time.
        """
        return expires_at is not None and expires_at < time.time()

    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieves a value from the cache by key.

        If the key does not exist or the entry has expired, returns None. If the
        entry is expired, it is not automatically deleted.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found or expired.

        Notes:
            - The value is deserialized using pickle.
            - Handles deserialization errors gracefully.
            - Thread-safe for Firestore client.
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
            - Thread-safe for Firestore client.
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
        Synchronously deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - Thread-safe for Firestore client.
            - The key is automatically namespaced and hashed.
        """
        doc_ref = self._sync_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        doc_ref.delete()

    def clear(self) -> None:
        """
        Synchronously removes all cache entries in the collection.

        This method deletes all documents in the configured Firestore collection.
        Note that Firestore does not support direct namespace-based clearing, so
        all entries in the collection are removed.

        Notes:
            - Thread-safe for Firestore client.
            - This operation can be expensive if the collection is large.
            - For more granular clearing, consider adding a namespace field to documents.
        """
        docs = self._sync_db.collection(self._collection_name).stream()
        for doc in docs:
            doc.reference.delete()

    def has(self, key: str) -> bool:
        """
        Synchronously checks if a cache key exists and is not expired.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.

        Notes:
            - Thread-safe for Firestore client.
            - Expired entries are not considered present.
        """
        doc_ref = self._sync_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return not self._is_expired(data.get("expires_at"))
        return False

    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieves a value from the cache by key.

        If the key does not exist or the entry has expired, returns None. If the
        entry is expired, it is not automatically deleted.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Optional[Any]: The cached Python object, or None if not found or expired.

        Notes:
            - The value is deserialized using pickle.
            - Handles deserialization errors gracefully.
            - Asyncio-safe for Firestore client.
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
            - Asyncio-safe for Firestore client.
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
        Asynchronously deletes a cache entry by key.

        If the key does not exist, this method does nothing.

        Args:
            key (str): The cache key to delete.

        Notes:
            - Asyncio-safe for Firestore client.
            - The key is automatically namespaced and hashed.
        """
        doc_ref = self._async_db.collection(self._collection_name).document(
            self._make_key(key)
        )
        await doc_ref.delete()

    async def aclear(self) -> None:
        """
        Asynchronously removes all cache entries in the collection.

        This method deletes all documents in the configured Firestore collection.
        Note that Firestore does not support direct namespace-based clearing, so
        all entries in the collection are removed.

        Notes:
            - Asyncio-safe for Firestore client.
            - This operation can be expensive if the collection is large.
            - For more granular clearing, consider adding a namespace field to documents.
        """
        docs = self._async_db.collection(self._collection_name).stream()
        async for doc in docs:
            await doc.reference.delete()

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously checks if a cache key exists and is not expired.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists and is not expired, False otherwise.

        Notes:
            - Asyncio-safe for Firestore client.
            - Expired entries are not considered present.
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
        Closes the synchronous Firestore client and stops the cleanup scheduler.

        This method should be called when the backend is no longer needed to ensure
        all resources are released and background jobs are stopped.

        Notes:
            - After calling this method, the synchronous client is closed and cannot be used.
            - The background cleanup scheduler is stopped.
        """
        self._stop_cleanup_scheduler()
        try:
            self._sync_db.close()
        except TypeError:
            return

    async def aclose(self) -> None:
        """
        Closes the asynchronous Firestore client and stops the cleanup scheduler.

        This method should be called when the backend is no longer needed to ensure
        all resources are released and background jobs are stopped.

        Notes:
            - After calling this method, the asynchronous client is closed and cannot be used.
            - The background cleanup scheduler is stopped.
        """
        self._stop_cleanup_scheduler()
        try:
            await self._async_db.close()
        except TypeError:
            return

    def _start_cleanup_scheduler(self):
        """
        Starts the background scheduler for periodic cleanup of expired cache entries.

        This method launches a background job that periodically deletes expired
        cache entries from the Firestore collection. If the scheduler is already running,
        this method does nothing.

        Thread-safe: uses a lock to prevent concurrent scheduler starts.

        Notes:
            - The cleanup interval is determined by the `cleanup_interval` parameter
              provided during initialization.
            - The scheduler runs in a background thread and does not block main
              application execution.
            - The scheduler is started automatically on initialization if `auto_cleanup` is True.
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
        Periodically deletes expired cache entries from the Firestore collection.

        This method is executed by the background scheduler at regular intervals.
        It queries for all documents with an `expires_at` field less than the current
        time and deletes them in batches.

        Notes:
            - This method is not intended to be called directly.
            - Uses batch deletes for efficiency (up to 500 per batch).
            - Only entries with a non-null `expires_at` field and an expiration
              time earlier than the current time are deleted.
            - Thread-safe for Firestore client.
        """
        now = int(time.time())
        expired_query = self._sync_db.collection(self._collection_name).where(
            "expires_at", "<", now
        )
        batch = self._sync_db.batch()
        count = 0
        for doc in expired_query.stream():
            batch.delete(doc.reference)
            count += 1
            if count == 500:
                batch.commit()
                batch = self._async_db.batch()
                count = 0
        if count > 0:
            batch.commit()
