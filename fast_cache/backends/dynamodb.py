import hashlib
from typing import Any, Optional, Union
from datetime import timedelta
import pickle
import time

from .backend import CacheBackend


class DynamoDBBackend(CacheBackend):
    """
    DynamoDB cache backend implementation with namespace support.

    Attributes:
        _namespace (str): Namespace prefix for all keys.
        _table_name (str): DynamoDB table name.
        _sync_client (boto3.client): Synchronous DynamoDB client.
        _async_client (aioboto3.client): Asynchronous DynamoDB client.
        _sync_resource (boto3.resource): Synchronous DynamoDB resource.
        _async_resource (aioboto3.resource): Asynchronous DynamoDB resource.
    """

    def __init__(
        self,
        table_name: str,
        region_name: str,
        namespace: str = "cache",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        create_table: bool = True,
    ) -> None:
        """
        Initialize DynamoDB backend with table and connection settings.

        Args:
            table_name (str): DynamoDB table name for cache storage.
            namespace (str): Namespace prefix for all keys (default: "fastapi-cache").
            region_name (str): AWS region name (default: "us-east-1").
            aws_access_key_id (Optional[str]): AWS access key ID.
            aws_secret_access_key (Optional[str]): AWS secret access key.
            endpoint_url (Optional[str]): Custom endpoint URL (for local DynamoDB).
            create_table (bool): Whether to create table if it doesn't exist.
        """
        try:
            import boto3
            import aioboto3
        except ImportError:
            raise ImportError(
                "DynamoDBBackend requires the 'boto3' and 'aioboto3' packages. "
                "Install them with: pip install fast-cache[dynamodb]"
            )

        self._namespace = namespace
        self._table_name = table_name

        # Connection parameters
        self._connection_params = {
            "region_name": region_name,
            "endpoint_url": endpoint_url,
        }

        if aws_access_key_id and aws_secret_access_key:
            self._connection_params.update(
                {
                    "aws_access_key_id": aws_access_key_id,
                    "aws_secret_access_key": aws_secret_access_key,
                }
            )

        # Sync client for table management only
        self._sync_client = boto3.client("dynamodb", **self._connection_params)

        # Sync resource/table for sync cache operations
        self._sync_resource = boto3.resource("dynamodb", **self._connection_params)
        self._sync_table = self._sync_resource.Table(table_name)

        # Initialize async session
        self._async_resource = None
        self._async_table = None
        self._async_session = aioboto3.Session()

        # Create table if requested
        if create_table:
            self._ensure_table_exists()

    async def _get_async_table(self):
        if self._async_table is None:
            # Create the resource context
            self._async_resource = self._async_session.resource(
                "dynamodb", **self._connection_params
            )

            # Enter the context and get the actual resource
            actual_resource = await self._async_resource.__aenter__()

            # Create the table from the actual resource
            self._async_table = await actual_resource.Table(self._table_name)


        return self._async_table

    def _ensure_table_exists(self) -> None:
        """
        Ensure the DynamoDB table exists, create if it doesn't.
        """

        try:
            self._sync_client.describe_table(TableName=self._table_name)
        except self._sync_client.exceptions.ResourceNotFoundException:
            # Table doesn't exist, create it
            self._sync_client.create_table(
                TableName=self._table_name,
                KeySchema=[{"AttributeName": "cache_key", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "cache_key", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Wait for table to be created
            waiter = self._sync_client.get_waiter("table_exists")
            waiter.wait(TableName=self._table_name)

        try:
            self._sync_client.update_time_to_live(
                TableName=self._table_name,
                TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
            )
        except Exception:
            pass

    def _make_key(self, key: str) -> str:
        """
        Create a namespaced key with optional hashing for long keys.

        Args:
            key (str): The original key.

        Returns:
            str: The namespaced key, hashed if too long.
        """
        namespaced_key = f"{self._namespace}:{key}"

        # DynamoDB has a 2KB limit for partition keys
        if len(namespaced_key.encode("utf-8")) > 1024:
            key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
            namespaced_key = f"{self._namespace}:hash:{key_hash}"

        return namespaced_key

    def _get_ttl(self, expire: Optional[Union[int, timedelta]]) -> Optional[int]:
        """
        Calculate TTL timestamp for DynamoDB.

        Args:
            expire (Optional[Union[int, timedelta]]): Expiration time.

        Returns:
            Optional[int]: TTL timestamp or None if no expiration.
        """
        if expire is None:
            return None

        if isinstance(expire, timedelta):
            expire = int(expire.total_seconds())

        if expire <= 0:
            return None

        return int(time.time()) + expire

    def _is_expired(self, item: dict) -> bool:
        """
        Check if an item has expired based on TTL.

        Args:
            item (dict): DynamoDB item.

        Returns:
            bool: True if expired, False otherwise.
        """
        if "ttl" not in item:
            return False

        return time.time() > item["ttl"]

    def _serialize_value(self, value: Any) -> bytes:
        """
        Serialize value for storage in DynamoDB.

        Args:
            value (Any): Value to serialize.

        Returns:
            bytes: Serialized value.
        """
        return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize_value(self, data: bytes) -> Any:
        """
        Deserialize value from DynamoDB storage.

        Args:
            data (bytes): Serialized data.

        Returns:
            Any: Deserialized value.
        """
        return pickle.loads(bytes(data))

    def _build_item(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> dict:
        """
        Build a DynamoDB item for storage.

        Args:
            key (str): Cache key.
            value (Any): Value to store.
            expire (Optional[Union[int, timedelta]]): Expiration time.

        Returns:
            dict: DynamoDB item.
        """
        item = {
            "cache_key": self._make_key(key),
            "value": self._serialize_value(value),
        }

        ttl = self._get_ttl(expire)
        if ttl is not None:
            item["ttl"] = ttl

        return item

    def get(self, key: str) -> Optional[Any]:
        """
        Synchronously retrieve a value from the cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[Any]: The cached value, or None if not found.
        """
        try:
            response = self._sync_table.get_item(Key={"cache_key": self._make_key(key)})

            if "Item" not in response:
                return None

            item = response["Item"]

            # Check if item has expired and delete if so
            if self._is_expired(item):
                self.delete(key)
                return None
            value = self._deserialize_value(item["value"])
            return value
        except Exception:
            return None

    async def aget(self, key: str) -> Optional[Any]:
        """
        Asynchronously retrieve a value from the cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[Any]: The cached value, or None if not found.
        """
        try:
            table = await self._get_async_table()
            response = await table.get_item(Key={"cache_key": self._make_key(key)})

            if "Item" not in response:
                return None

            item = response["Item"]

            # Check if item has expired and delete if so
            if self._is_expired(item):
                await self.adelete(key)
                return None

            return self._deserialize_value(item["value"])
        except Exception:
            return None

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
        try:
            item = self._build_item(key, value, expire)
            self._sync_table.put_item(Item=item)
        except Exception:
            pass

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
        try:
            table = await self._get_async_table()
            item = self._build_item(key, value, expire)
            await table.put_item(Item=item)
        except Exception:
            pass

    def delete(self, key: str) -> None:
        """
        Synchronously delete a value from the cache.

        Args:
            key (str): The key to delete.
        """
        try:
            self._sync_table.delete_item(Key={"cache_key": self._make_key(key)})
        except Exception:
            pass

    async def adelete(self, key: str) -> None:
        """
        Asynchronously delete a value from the cache.

        Args:
            key (str): The key to delete.
        """
        try:
            table = await self._get_async_table()
            await table.delete_item(Key={"cache_key": self._make_key(key)})
        except Exception:
            pass

    def has(self, key: str) -> bool:
        """
        Synchronously check if a key exists in the cache.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        try:
            response = self._sync_table.get_item(
                Key={"cache_key": self._make_key(key)},
                ProjectionExpression="cache_key, #ttl",
                ExpressionAttributeNames={"#ttl": "ttl"},
            )


            if "Item" not in response:
                return False

            item = response["Item"]

            # Check if item has expired and delete if so
            if self._is_expired(item):
                self.delete(key)
                return False

            return True
        except Exception:
            return False

    async def ahas(self, key: str) -> bool:
        """
        Asynchronously check if a key exists in the cache.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        try:
            table = await self._get_async_table()
            response = await table.get_item(
                Key={"cache_key": self._make_key(key)},
                ProjectionExpression="cache_key, #ttl",
                ExpressionAttributeNames={"#ttl": "ttl"},
            )

            if "Item" not in response:
                return False

            item = response["Item"]

            # Check if item has expired and delete if so
            if self._is_expired(item):
                await self.adelete(key)
                return False

            return True
        except Exception:
            return False

    def clear(self) -> None:
        """
        Synchronously clear all values from the namespace.
        """
        try:
            # Scan for all items with the namespace prefix
            response = self._sync_table.scan(
                FilterExpression="begins_with(cache_key, :prefix)",
                ExpressionAttributeValues={":prefix": f"{self._namespace}:"},
                ProjectionExpression="cache_key",
            )

            # Delete items in batches
            if response.get("Items"):
                with self._sync_table.batch_writer() as batch:
                    for item in response["Items"]:
                        batch.delete_item(Key={"cache_key": item["cache_key"]})

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self._sync_table.scan(
                    FilterExpression="begins_with(cache_key, :prefix)",
                    ExpressionAttributeValues={":prefix": f"{self._namespace}:"},
                    ProjectionExpression="cache_key",
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )

                if response.get("Items"):
                    with self._sync_table.batch_writer() as batch:
                        for item in response["Items"]:
                            batch.delete_item(Key={"cache_key": item["cache_key"]})

        except Exception:
            pass

    async def aclear(self) -> None:
        """
        Asynchronously clear all values from the namespace.
        """
        try:
            table = await self._get_async_table()

            # Scan for all items with the namespace prefix
            response = await table.scan(
                FilterExpression="begins_with(cache_key, :prefix)",
                ExpressionAttributeValues={":prefix": f"{self._namespace}:"},
                ProjectionExpression="cache_key",
            )

            # Delete items in batches
            if response.get("Items"):
                async with table.batch_writer() as batch:
                    for item in response["Items"]:
                        await batch.delete_item(Key={"cache_key": item["cache_key"]})

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = await table.scan(
                    FilterExpression="begins_with(cache_key, :prefix)",
                    ExpressionAttributeValues={":prefix": f"{self._namespace}:"},
                    ProjectionExpression="cache_key",
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )

                if response.get("Items"):
                    async with table.batch_writer() as batch:
                        for item in response["Items"]:
                            await batch.delete_item(Key={"cache_key": item["cache_key"]})

        except Exception:
            pass

    async def close(self) -> None:
        """
        Close DynamoDB connections and clean up resources.
        """
        if self._async_resource:
            await self._async_resource.__aexit__(None, None, None)
            self._async_resource = None
            self._async_table = None
