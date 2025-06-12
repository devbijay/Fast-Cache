import os

import uvicorn
from fastapi import FastAPI, Depends, Query
from fast_cache import cache, InMemoryBackend, CacheBackend, RedisBackend
from typing import Annotated
from pydantic import BaseModel


def get_backend():
    backend_type = os.getenv("CACHE_BACKEND")
    if backend_type == "memory":
        return InMemoryBackend(namespace="integration-demo")
    if backend_type == "redis":
        return RedisBackend(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            namespace="integration-demo"
        )

app = FastAPI()

# Initialize cache with InMemoryBackend for local/dev/testing
cache.init_app(
    app=app,
    backend=get_backend(),
    default_expire=120
)

# --- Decorator-based caching (async and sync) ---

@app.get("/decorator/async")
@cache.cached(expire=10)
async def cached_async(x: int = Query(...)):
    backend = cache.get_cache()
    print(f"[ENDPOINT] Backend in use: {type(backend).__name__}")
    # Simulate expensive work
    return {"result": x * 2}

@app.get("/decorator/sync")
@cache.cached(expire=10)
def cached_sync(x: int = Query(...)):
    # Simulate expensive work
    return {"result": x * 3}

# --- Decorator with custom namespace and key builder ---

@app.get("/decorator/custom")
@cache.cached(namespace="custom", key_builder=lambda x: f"custom:{x}", expire=15)
async def custom_key(x: int):
    return {"custom_key": x}

# --- Decorator: skip cache for specific call ---

@app.get("/decorator/skip")
@cache.cached(expire=10)
async def skip_cache(x: int, skip_cache: bool = False):
    # skip_cache param will bypass cache if True
    return {"result": x * 5}

# --- Pydantic model caching ---

class Item(BaseModel):
    name: str
    value: int

@app.get("/decorator/pydantic")
@cache.cached(expire=10)
async def cached_pydantic(name: str, value: int):
    return Item(name=name, value=value)

# --- Dependency Injection: direct backend access ---

@app.get("/di/set")
async def di_set(
    cache_backend: Annotated[CacheBackend, Depends(cache.get_cache)],
    key: str,
    value: str,
):
    await cache_backend.aset(key, value, expire=30)
    return {"set": True}

@app.get("/di/get")
async def di_get(
    cache_backend: Annotated[CacheBackend, Depends(cache.get_cache)],
    key: str,
):
    value = await cache_backend.aget(key)
    return {"value": value}

@app.get("/di/has")
async def di_has(
    cache_backend: Annotated[CacheBackend, Depends(cache.get_cache)],
    key: str,
):
    exists = await cache_backend.ahas(key)
    return {"exists": exists}

@app.delete("/di/delete")
async def di_delete(
    cache_backend: Annotated[CacheBackend, Depends(cache.get_cache)],
    key: str,
):
    await cache_backend.adelete(key)
    return {"deleted": True}

@app.post("/di/clear")
async def di_clear(
    cache_backend: Annotated[CacheBackend, Depends(cache.get_cache)],
    namespace: str = "integration-demo"
):
    await cache_backend.aclear()
    return {"cleared": True}

# --- Example: cache with dependency injection for business logic ---

@app.get("/profile/{user_id}")
async def get_profile(
    user_id: int,
    cache_backend: Annotated[CacheBackend, Depends(cache.get_cache)]
):
    key = f"profile:{user_id}"
    cached = await cache_backend.aget(key)
    if cached:
        return {"profile": cached, "cached": True}
    # Simulate expensive fetch
    profile = {"user_id": user_id, "bio": f"User {user_id} bio"}
    await cache_backend.aset(key, profile, expire=60)
    return {"profile": profile, "cached": False}

# --- Example: cache with skip_cache param ---

@app.get("/weather")
@cache.cached()
async def get_weather(city: str, skip_cache: bool = False):
    # Simulate slow API call
    return {"city": city, "weather": "sunny"}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)