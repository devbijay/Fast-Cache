# FastAPI Cachekit

**FastAPI Cachekit** is a high-performance, pluggable caching extension for [FastAPI](https://fastapi.tiangolo.com/).  
It provides a unified, developer-friendly interface for adding caching to your FastAPI applications, supporting multiple backends and both synchronous and asynchronous APIs.

---

## 🚀 What is FastAPI Cachekit?

FastAPI Cachekit is a library designed to make caching in FastAPI apps **easy, flexible, and production-ready**.  
It allows you to cache expensive computations, database queries, or API responses using a simple decorator or dependency injection, with support for:

- In-memory caching (for local development and testing)
- Redis (for distributed, production-grade caching)
- PostgreSQL (for persistent, SQL-based caching)
- Memcached (for high-speed, distributed caching)

You can choose the backend that fits your needs, and switch between them with minimal code changes.

---

## 🌟 Benefits

- **Plug-and-play:** Add caching to any FastAPI endpoint with a simple decorator.
- **Multiple backends:** Use in-memory, Redis, Postgres, or Memcache etc. Swap backends with a single line of code.
- **Sync & Async support:** Works seamlessly with both synchronous and asynchronous FastAPI endpoints.
- **Performance:** Reduce database load, speed up API responses, and improve scalability.
- **Optional dependencies:** Only install the backend you need, keeping your project lightweight.
- **Production-ready:** Tested with Docker, testcontainers, and CI for reliability.
- **Easy integration:** Works with FastAPI’s dependency injection and lifespan events.

---

## 📦 Backends & Sync/Async Support

| Backend            | Sync API | Async API | Install Extra | Setup Guide                                   |
|--------------------|:--------:|:---------:|---------------|-----------------------------------------------|
| `InMemoryBackend`  |   ✅     |    ✅     | _built-in_    | [Guide](backends/in_memory.md)                |
| `RedisBackend`     |   ✅     |    ✅     | `redis`       | [Guide](backends/redis.md)                    |
| `PostgresBackend`  |   ✅     |    ✅     | `postgres`    | [Guide](backends/postgres.md)                 |
| `MemcachedBackend` |   ✅     |    ✅     | `memcached`   | [Guide](backends/memcached.md)                |
| `MongoDBBackend`   |   ✅     |    ✅     | `mongodb`     | [Guide](backends/mongodb.md)                  |
| `FirestoreBackend` |   ✅     |    ✅     | `firestore`   | [Guide](backends/firestore.md)                |
| `DynamoDBBackend`  |   ✅     |    ✅     | `dynamodb`    | [Guide](backends/dynamodb.md)                 |
---
## 🧑‍💻 Example Usage

### 1. **Decorator-Based Caching**

Cache the result of a function or endpoint automatically using the `@cache.cached` decorator:

```python
from fast_cache import cache, InMemoryBackend

backend = InMemoryBackend()
cache.init_app(app, backend)

@app.get("/expensive")
@cache.cached(expire=60)
async def expensive_operation(x: int):
    # Simulate expensive work
    return {"result": x * 2}
```

---

### 2. **Dependency Injection: Direct Backend Access**

You can inject the cache backend into your endpoint for full control:

```python
from fastapi import Depends
from typing import Annotated

@app.get("/expensive-direct")
async def expensive_operation_direct(
    x: int,
    cache_backend: Annotated[InMemoryBackend, Depends(cache.get_cache)],
):
    cache_key = f"expensive:{x}"
    # Try to get from cache
    cached = await cache_backend.aget(cache_key)
    if cached is not None:
        return {"result": cached, "cached": True}
    # Simulate expensive work
    result = x * 2
    await cache_backend.aset(cache_key, result, expire=60)
    return {"result": result, "cached": False}
```

---

### 3. **Sync Function Caching (Decorator)**

You can also cache sync functions:

```python
@app.get("/expensive-sync")
@cache.cached(expire=60)
def expensive_operation_sync(x: int):
    # Simulate expensive work
    return {"result": x * 3}
```

---

**Tip:**  
- Use the decorator for simple, automatic caching.
- Use dependency injection for advanced or custom cache logic.


FastAPI Cachekit makes caching in FastAPI **simple, powerful, and flexible** so you can focus on building fast, reliable APIs.

**Next:** [Installation →](installation.md)
