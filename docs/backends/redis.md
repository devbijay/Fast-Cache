# Redis Backend

## Installation

```bash
pip install fastapi-cachekit[redis]
```

## Setup with FastAPI

```python
from fast_cache import FastAPICache, RedisBackend

cache = FastAPICache()
backend = RedisBackend(redis_url="redis://localhost:6379/0")
cache.init_app(app, backend)
```

## Options

- `redis_url`: Redis connection string
- `namespace`: Key prefix for all cache entries

## Example Usage

```python
@app.get("/expensive")
@cache.cached(expire=60)
async def expensive_operation(x: int):
    return {"result": x * 2}
```

## Tips

- Use Redis for distributed, production-grade caching.
- Make sure your Redis server is running and accessible.