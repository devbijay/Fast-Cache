# Postgres Backend

The **PostgresBackend** allows you to use a PostgreSQL database as a cache store for FastAPI Cachekit.  
This backend is ideal when you want persistent, SQL-based caching, or when you already have a PostgreSQL database in your stack.

---

## 🚀 Installation

Install FastAPI Cachekit with Postgres support:

```
pip install fastapi-cachekit[postgres]
```

Or with other tools:

- **uv**
```
uv add fastapi-cachekit[postgres]
```
- **poetry**
```
poetry add fastapi-cachekit -E postgres
```

---

## ⚙️ Setup with FastAPI

```python
from fast_cache import cache, PostgresBackend

backend = PostgresBackend(
    dsn="postgresql://user:password@localhost:5432/mydb",
    namespace="myapp_cache"
)
cache.init_app(app, backend)
```

- `dsn`: PostgreSQL connection string (required)
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

## 📝 Options

- **dsn**:  
  PostgreSQL connection string, e.g. `postgresql://user:password@localhost:5432/mydb`
- **namespace**:  
  String prefix for all cache keys (default: `"fastapi-cache"`)
- **min_size**:  
  Minimum number of connections in the pool (default: 1)
- **max_size**:  
  Maximum number of connections in the pool (default: 10)

```python
backend = PostgresBackend(
    dsn="postgresql://user:password@localhost:5432/mydb",
    namespace="myapp-cache",
    min_size=2,
    max_size=20
)
```

---

## ⚡️ About UNLOGGED TABLES

> **This backend uses a PostgreSQL UNLOGGED TABLE for storing cache entries.**

- **UNLOGGED TABLES** are much faster than regular tables because they do not write to the PostgreSQL write-ahead log (WAL).
- **Drawback:** Data in an unlogged table is **not crash-safe**—if the database server crashes, all cached data in the table is lost.
- **Benefit:** For cache data, this is usually acceptable and gives a significant performance boost.

**In summary:**  
- Cache data is fast and persistent across app restarts, but not across database crashes.
- If you need crash-safe persistence, consider using a regular table (open an issue or PR for support).

---

## ⚠️ Tips & Limitations

- **Requires a running PostgreSQL server**.
- **Data is persistent across app restarts, but not across database crashes** (due to UNLOGGED TABLE).
- **Slightly slower than in-memory or Redis** for high-throughput caching, but great for persistence and SQL-based setups.
- **Best for apps already using PostgreSQL** or needing persistent cache.

---

## 🔗 See Also

- [Backends Overview](../backends.md)
- [API Reference](../api.md)
- [Usage Guide](../usage.md)