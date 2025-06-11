# Fast-Cache

A high-performance, flexible caching solution for FastAPI applications. Fast-Cache supports both synchronous and asynchronous operations with a clean API and multiple backend options.

[![PyPI version](https://badge.fury.io/py/fast-cache.svg)](https://badge.fury.io/py/fast-cache)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![Downloads](https://pepy.tech/badge/fastapi-cache)](https://pepy.tech/project/fast-cache)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- ✅ Full async/sync support for all operations
- ✅ Redis backend with connection pooling
- ✅ Function result caching with decorator syntax
- ✅ FastAPI dependency injection support
- ✅ Namespace support for isolating cache entries
- ✅ Customizable key generation
- ✅ Type hinting throughout the codebase
- ✅ Expiration time support (seconds or timedelta)

## Installation

```bash
pip install fast-cache
```

or with uv:

```bash
uv add fast-cache
```

## Quick Start

```python
from fastapi import FastAPI, Depends
from fast_cache import cache, RedisBackend
from typing import Annotated

app = FastAPI()

# Initialize cache with Redis backend
cache.init_app(
    app=app,
    backend=RedisBackend(redis_url="redis://localhost:6379/0", namespace="myapp"),
    default_expire=300  # 5 minutes default expiration
)

# Register FastAPI lifespan event to manage cache connections
app.add_event_handler("startup", lambda: app.state.cache_handler(app))

# Use function caching decorator
@app.get("/items/{item_id}")
@cache.cached(expire=60)  # Cache for 60 seconds
async def read_item(item_id: int):
    # Expensive operation simulation
    return {"item_id": item_id, "name": f"Item {item_id}"}

# Use cache backend directly with dependency injection
@app.get("/manual-cache")
async def manual_cache_example(cache_backend: Annotated[RedisBackend, Depends(cache.get_cache)]):
    # Check if key exists
    has_key = await cache_backend.ahas("my-key")

    if not has_key:
        # Set a value in the cache
        await cache_backend.aset("my-key", {"data": "cached value"}, expire=30)
        return {"cache_set": True}

    # Get the value from cache
    value = await cache_backend.aget("my-key")
    return {"cached_value": value}
```

## Detailed Usage

### Initializing the Cache

Before using the cache, you need to initialize it with a backend:

```python
from fastapi import FastAPI
from fast_cache import cache, RedisBackend
from datetime import timedelta

app = FastAPI()

cache.init_app(
    app=app,
    backend=RedisBackend(
        redis_url="redis://localhost:6379/0",
        namespace="myapp",
        max_connections=20
    ),
    default_expire=timedelta(minutes=5)
)
```

### Cache Decorator

The `@cache.cached()` decorator is the simplest way to cache function results:

```python
from fast_cache import cache

# Cache with default expiration time
@cache.cached()
def get_user_data(user_id: int):
    # Expensive database query
    return {"user_id": user_id, "name": "John Doe"}

# Cache with custom namespace and expiration
@cache.cached(namespace="users", expire=300)
async def get_user_profile(user_id: int):
    # Async expensive operation
    return {"user_id": user_id, "profile": "..."}

# Cache with custom key builder
@cache.cached(key_builder=lambda user_id, **kwargs: f"user:{user_id}")
def get_user_permissions(user_id: int):
    # Complex permission calculation
    return ["read", "write"]
```

### Manual Cache Operations

You can access the cache backend directly for more control:

```python
from fastapi import Depends
from fast_cache import cache, CacheBackend
from typing import Annotated

@app.get("/api/data")
async def get_data(cache_backend: Annotated[CacheBackend, Depends(cache.get_cache)]):
    # Try to get from cache
    cached_data = await cache_backend.aget("api:data")
    if cached_data:
        return cached_data

    # Generate new data
    data = await fetch_expensive_api_data()

    # Store in cache for 1 hour
    await cache_backend.aset("api:data", data, expire=3600)

    return data
```

### Skip Cache for Specific Calls

Sometimes you need to bypass the cache for certain requests:

```python
@cache.cached()
async def get_weather(city: str, skip_cache: bool = False):
    # Function will be called directly if skip_cache is True
    return await fetch_weather_data(city)

# Usage:
weather = await get_weather("New York", skip_cache=True)  # Bypasses cache
```

### Advanced: Implementing Custom Backends

You can create your own cache backend by implementing the `CacheBackend` abstract class:

```python
from fast_cache.backends.backend import CacheBackend
from typing import Any, Optional, Union
from datetime import timedelta

class MyCustomBackend(CacheBackend):
    # Implement all required methods
    async def aget(self, key: str) -> Any:
        # Your implementation here
        ...

    def get(self, key: str) -> Any:
        # Your implementation here
        ...

    # ... implement all other required methods
```

## API Reference

### Cache Instance

- `cache.init_app(app, backend, default_expire=None)` - Initialize cache with FastAPI app
- `cache.get_cache()` - Get cache backend instance (for dependency injection)
- `cache.cached(expire=None, key_builder=None, namespace=None)` - Caching decorator

### CacheBackend Interface

All backends implement these methods in both sync and async versions:

- `get(key)` / `aget(key)` - Retrieve a value
- `set(key, value, expire)` / `aset(key, value, expire)` - Store a value
- `delete(key)` / `adelete(key)` - Delete a value
- `clear()` / `aclear()` - Clear all values
- `has(key)` / `ahas(key)` - Check if key exists

### RedisBackend Configuration

- `redis_url` - Redis connection string (required)
- `namespace` - Key prefix (default: "fastapi-cache")
- `pool_size` - Minimum pool connections (default: 10)
- `max_connections` - Maximum pool connections (default: 20)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.