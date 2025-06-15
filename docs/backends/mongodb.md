# MongoDB Backend

The **MongoDBBackend** allows you to use a MongoDB database as a cache store for FastAPI Cachekit.
This backend is ideal when you want persistent, document-based caching, or when you already have a MongoDB database in your stack.
It supports automatic cache expiration using MongoDB’s TTL (Time-To-Live) indexes, making it easy to manage cache lifetimes efficiently.
---

## 🚀 Installation

Install FastAPI Cachekit with MongoDB support:

```
pip install fastapi-cachekit[mongodb]
```

Or with other tools:

- **uv**
```
uv add fastapi-cachekit[mongodb]
```
- **poetry**
```
poetry add fastapi-cachekit -E mongodb
```

---

## ⚙️ Setup with FastAPI

```python
from fast_cache import cache, MongoDBBackend

backend = MongoDBBackend(
    uri="mongodb://user:password@localhost:27017/mydb",
    namespace="myapp_cache"
)
cache.init_app(app, backend)
```

- `uri`: MongoDB connection string With All necessary Auth and Db in URL (required)
- `namespace`: Prefix for all cache keys (default: `"fastapi_cache"`)

---

## 🧑‍💻 Example Usage

```python
@app.get("/expensive")
@cache.cached(expire=120)
async def expensive_operation(x: int):
    # This result will be cached in Postgres for 2 minutes
    return {"result": x * 2}
```

---


# ⚡️ About MongoDB TTL Cache

> **This backend uses a MongoDB collection with a TTL (Time-To-Live) index for storing cache entries.**

- **TTL Indexes** in MongoDB automatically remove expired cache entries, so you don’t need to manage expiration manually.
- **Benefit:** Cache data is persistent across app and database restarts, and expired data is cleaned up automatically by MongoDB’s background process.
- **Drawback:** Expired documents may not be deleted immediately (MongoDB’s TTL monitor runs every 60 seconds by default), so there may be a short delay before expired cache entries are removed.

**In summary:**  
- Cache data is persistent and automatically expired, but there may be a short delay before expired entries are deleted.
- If you need instant removal of expired data, you should check expiration in your code (this backend does so).

---

## ⚠️ Tips & Limitations

- **Requires a running MongoDB server**.
- **Data is persistent across app and database restarts**.
- **Slightly slower than in-memory or Redis** for high-throughput caching, but great for persistence and document-based setups.
- **Best for apps already using MongoDB** or needing persistent, auto-expiring cache.
- **TTL index expiration is not instantaneous**; expired documents are removed in the background.

---
## 📝 How It Works

- Each cache entry is stored as a document with:
  - `_id`: the cache key (optionally namespaced)
  - `value`: the pickled cached value
  - `expires_at`: epoch time when the entry should expire
- A TTL index is created on the `expires_at` field.
- Expired documents are deleted automatically by MongoDB’s TTL monitor.
- Expiration is also checked in code to avoid returning stale data.

---
## 🚦 When to Use
- You want persistent, document-based caching.
- You already have a MongoDB database in your stack.
- You want automatic cache expiration without manual cleanup.
---

## 🔗 See Also

- [Backends Overview](../backends.md)
- [API Reference](../api.md)
- [Usage Guide](../usage.md)