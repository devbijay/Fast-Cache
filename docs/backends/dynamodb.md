# DynamoDB Backend

## Installation

```bash
pip install fastapi-cachekit[dynamodb]
```

## Setup with FastAPI

```python
from fast_cache import FastAPICache
from fast_cache.dynamodb import DynamoDBBackend

cache = FastAPICache()
backend = DynamoDBBackend(
    table_name="my_cache_table",
    region_name="us-east-1",
    namespace="my-namespace",  # Optional, default: "cache"
    aws_access_key_id="YOUR_AWS_ACCESS_KEY_ID",         # Optional for local
    aws_secret_access_key="YOUR_AWS_SECRET_ACCESS_KEY", # Optional for local
    endpoint_url="http://localhost:8000",               # For DynamoDB Local
    create_table=True,                                  # Auto-create table if needed
)
cache.init_app(app, backend)
```

## Options

- `table_name`: Name of the DynamoDB table to use for caching (**required**)
- `region_name`: AWS region (e.g., `"us-east-1"`)
- `namespace`: Key prefix for all cache entries (default: `"cache"`)
- `aws_access_key_id`: AWS access key (optional for local)
- `aws_secret_access_key`: AWS secret key (optional for local)
- `endpoint_url`: Custom endpoint (use `"http://localhost:8000"` for DynamoDB Local)
- `create_table`: If `True`, creates the table if it does not exist (default: `True`)


## Example Usage

You can use the DynamoDB cache backend in three main ways:

---

### 1. **Function Caching via Decorator**

Cache the result of any function or endpoint using the `@cache.cached` decorator.  
This works for both async and sync functions.

```python
from fastapi import FastAPI
from fast_cache import cache, DynamoDBBackend

app = FastAPI()
backend = DynamoDBBackend(
    table_name="my_cache_table",
    region_name="us-east-1",
    endpoint_url="http://localhost:8000",
    aws_access_key_id="fake",
    aws_secret_access_key="fake",
    create_table=True,
)
cache.init_app(app, backend)

@app.get("/expensive")
@cache.cached(expire=60)
async def expensive_operation(x: int):
    # This result will be cached for 60 seconds
    return {"result": x * 2}
```

You can also use custom cache keys and namespaces:

```python
@app.get("/custom")
@cache.cached(
    expire=120,
    key_builder=lambda x: f"custom:{x}",
    namespace="special"
)
async def custom_cache(x: int):
    return {"value": x}
```

To **skip cache** for a specific call, pass `skip_cache=True` as a query parameter or function argument.

---

### 2. **Direct Backend Access**

You can use the backend instance directly for advanced cache operations:

```python
# Set a value
await backend.aset("mykey", {"foo": "bar"}, expire=30)

# Get a value
value = await backend.aget("mykey")

# Check if a key exists
exists = await backend.ahas("mykey")

# Delete a key
await backend.adelete("mykey")

# Clear all cache in the namespace
await backend.aclear()
```

---

### 3. **Dependency Injection in FastAPI Endpoints**

You can inject the cache backend into your endpoints using FastAPI's dependency system:

```python
from fastapi import Depends
from typing import Annotated

@app.get("/di/set")
async def set_cache(
    cache_backend: Annotated[DynamoDBBackend, Depends(cache.get_cache)],
    key: str,
    value: str,
):
    await cache_backend.aset(key, value, expire=60)
    return {"set": True}

@app.get("/di/get")
async def get_cache(
    cache_backend: Annotated[DynamoDBBackend, Depends(cache.get_cache)],
    key: str,
):
    value = await cache_backend.aget(key)
    return {"value": value}
```

---

### **Note**

- Use the decorator for simple, automatic caching of endpoint results.
- Use direct backend access for custom or batch cache operations.
- Use dependency injection for full control and testability in your endpoints.
- You can always pass `skip_cache=True` (For Decorator based) to bypass the cache for a specific call. 

---

## Tips

- Use DynamoDB for serverless, persistent, and scalable caching on AWS.
- For local development and testing, use [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) and set `endpoint_url` to `"http://localhost:8000"`.
- The backend will automatically create the table and enable TTL if `create_table=True`.
- Make sure your AWS credentials and permissions are set up if connecting to AWS.
- Use a unique `namespace` to avoid key collisions if sharing the table with other apps.

## Example: Local DynamoDB Setup

Start DynamoDB Local with Docker:

```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

Then use:

```python
backend = DynamoDBBackend(
    table_name="my_cache_table",
    region_name="us-east-1",
    endpoint_url="http://localhost:8000",
    aws_access_key_id="fake",         # Use dummy values for local
    aws_secret_access_key="fake",     # Use dummy values for local
    create_table=True,
)
```