# In-Memory Backend

The **InMemoryBackend** is the simplest backend for FastAPI Cachekit.  
It stores all cached data in the application's memory, making it ideal for local development, testing, or small-scale deployments.

---

## 🚀 Installation

No extra dependencies are required!  
The in-memory backend is **built-in** and works out of the box.

```bash
pip install fastapi-cachekit
```

---

## ⚙️ Setup with FastAPI

```python
from fast_cache import FastAPICache, InMemoryBackend

cache = FastAPICache()
backend = InMemoryBackend(namespace="myapp-cache")
cache.init_app(app, backend)
```

- `namespace` (optional): Prefix for all cache keys (default: `"fastapi-cache"`).

---

## 🧑‍💻 Example Usage

```python
@app.get("/expensive")
@cache.cached(expire=60)
async def expensive_operation(x: int):
    # This result will be cached in memory for 60 seconds
    return {"result": x * 2}
```

---

## 📝 Options

- **namespace**:  
  A string prefix for all cache keys. Useful if you run multiple apps in the same process.

- **max_size** (optional):  
  Maximum number of items to store in the cache.  
  If set, the cache will evict the least recently used (LRU) items when full.

```python
backend = InMemoryBackend(namespace="myapp-cache", max_size=1000)
```

---

## ⚠️ Limitations

- **Not shared between processes or servers**:  
  Each process has its own cache. Not suitable for distributed or multi-worker deployments.
- **Data is lost on restart**:  
  The cache is cleared when the app restarts.
- **Best for development, testing, or single-process apps**.

---
## 🔗 See Also

- [Backends Overview](../backends.md)
- [API Reference](../api.md)
- [Usage Guide](../usage.md)