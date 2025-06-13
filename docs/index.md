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
- **Multiple backends:** Use in-memory, Redis, Postgres, or Memcached—swap backends with a single line of code.
- **Sync & Async support:** Works seamlessly with both synchronous and asynchronous FastAPI endpoints.
- **Performance:** Reduce database load, speed up API responses, and improve scalability.
- **Optional dependencies:** Only install the backend you need, keeping your project lightweight.
- **Production-ready:** Tested with Docker, testcontainers, and CI for reliability.
- **Easy integration:** Works with FastAPI’s dependency injection and lifespan events.

---

## 📦 Backends & Sync/Async Support

| Backend            | Sync API | Async API | Install Extra         |
|--------------------|:--------:|:---------:|----------------------|
| `InMemoryBackend`  |   ✅     |    ✅     | _built-in_           |
| `RedisBackend`     |   ✅     |    ✅     | `redis`              |
| `PostgresBackend`  |   ✅     |    ✅     | `postgres`           |
| `MemcachedBackend` |   ✅     |    ✅     | `memcached`          |

---

## 🧑‍💻 Example Usage

```python
from fast_cache import FastAPICache, InMemoryBackend

cache = FastAPICache()
backend = InMemoryBackend()
cache.init_app(app, backend)

@app.get("/expensive")
@cache.cached(expire=60)
async def expensive_operation(x: int):
    # Simulate expensive work
    return {"result": x * 2}
```

---




FastAPI Cachekit makes caching in FastAPI **simple, powerful, and flexible** so you can focus on building fast, reliable APIs.

**Next:** [Installation →](installation.md)
