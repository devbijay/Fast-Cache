from abc import ABC, abstractmethod
from typing import Any, Optional, Union
from datetime import timedelta


class CacheBackend(ABC):
    """
    Abstract base class for cache backends.

    All cache backend implementations must inherit from this class and implement
    both synchronous and asynchronous methods for cache operations.
    """

    @abstractmethod
    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieve a value from the cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[Any]: The cached value, or None if not found.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieve a value from the cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[Any]: The cached value, or None if not found.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def adelete(self, key: str) -> None:
        """
        Asynchronously delete a value from the cache.

        Args:
            key (str): The key to delete.
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Synchronously delete a value from the cache.

        Args:
            key (str): The key to delete.
        """
        pass

    @abstractmethod
    async def aclear(self) -> None:
        """
        Asynchronously clear all values from the cache.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Synchronously clear all values from the cache.
        """
        pass

    @abstractmethod
    async def ahas(self, key: str) -> bool:
        """
        Asynchronously check if a key exists in the cache.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Synchronously check if a key exists in the cache.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        pass
