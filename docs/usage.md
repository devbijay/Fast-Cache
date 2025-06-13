# 🧑‍💻 Usage Guide

FastAPI Cachekit makes it easy to cache results in your FastAPI app using decorators or dependency injection.  
Below are the most common usage patterns.

---

## 1️⃣ Decorator for Functions

You can use the `@cache.cached()` decorator to cache the result of any function (sync or async), not just FastAPI routes.

```python
from fast_cache import FastAPICache, InMemoryBackend

cache = FastAPICache()
backend = InMemoryBackend()
cache.init_app(app, backend)

@cache.cached(expire=60)
def expensive_computation(x: int):
    # This result will be cached for 60 seconds
    return x * 2

result = expensive_computation(10)  # Cached!
```

- Works for both sync and async functions.
- You can specify `expire` (in seconds or as a `timedelta`).

---

## 2️⃣ Decorator for FastAPI Routes

You can use the same decorator directly on your FastAPI endpoints to cache their responses.

```python
from fastapi import FastAPI
from fast_cache import FastAPICache, InMemoryBackend

app = FastAPI()
cache = FastAPICache()
backend = InMemoryBackend()
cache.init_app(app, backend)

@app.get("/expensive")
@cache.cached(expire=120)
async def expensive_route(x: int):
    # This endpoint's response will be cached for 2 minutes
    return {"result": x * 2}
```

- Works for both `@app.get`, `@app.post`, etc.
- Supports both sync and async endpoints.

---

## 3️⃣ Dependency Injection for Advanced Use

For more control, you can inject the backend and use its methods directly (e.g., for custom cache keys, manual cache control, or advanced logic).

```python
from fastapi import Depends
from fast_cache import cache, CacheBackend
 
## Add The cache init Here

@app.get("/profile/{user_id}")
async def get_profile(
    user_id: int,
    cache_backend: CacheBackend = Depends(cache.get_cache)
):
    key = f"profile:{user_id}"
    cached = await cache_backend.aget(key)
    if cached:
        return {"profile": cached, "cached": True}
    # Simulate expensive fetch
    profile = {"user_id": user_id, "bio": f"User {user_id} bio"}
    await cache_backend.aset(key, profile, expire=60)
    return {"profile": profile, "cached": False}
```

- Use `Depends(cache.get_cache)` to inject the backend.
- Use `aget`, `aset`, `adelete`, etc. for async; `get`, `set`, etc. for sync.

---

## 🔗 Next Steps

- [API Reference](api.md)
- [Backends](backends.md)

---

**FastAPI Cachekit makes caching easy, flexible, and production-ready!**