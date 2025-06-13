# Memcached Backend

The **MemcachedBackend** allows you to use a Memcached server as a cache store for FastAPI Cachekit.  
This backend is ideal for high-speed, distributed caching in stateless applications.

---

## 🚀 Installation

Install FastAPI Cachekit with Memcached support:

```bash
pip install fastapi-cachekit[memcached]
```

Or with other tools:

- **uv**
```bash
uv add fastapi-cachekit[memcached]
```
- **poetry**
```bash
poetry add fastapi-cachekit -E memcached
```

---

## ⚙️ Setup with FastAPI

```python
from fast_cache import cache, MemcachedBackend

backend = MemcachedBackend(
    host="localhost",
    port=11211,
    namespace="myapp-cache"
)
cache.init_app(app, backend)
```

- `host`: Memcached server host (default: `"localhost"`)
- `port`: Memcached server port (default: `11211`)
- `namespace`: Prefix for all cache keys (default: `"fastapi-cache"`)

---

## 🧑‍💻 Example Usage

```python
@app.get("/expensive")
@cache.cached(expire=60)
async def expensive_operation(x: int):
    # This result will be cached in Memcached for 60 seconds
    return {"result": x * 2}
```

---

## 📝 Options

- **host**:  
  Memcached server host (default: `"localhost"`)

- **port**:  
  Memcached server port (default: `11211`)

- **namespace**:  
  String prefix for all cache keys (default: `"fastapi-cache"`)


- **pool_size**:  
  Maximum number of connections in the sync pool (default: `2`)

---

## ⚡️ Notes

- **Memcached is a high-speed, in-memory, distributed cache.**
- **No persistence:** Data is lost if the server restarts.
- **No built-in authentication by default:**  
  SASL authentication is available if enabled on the server and configured in the backend.
- **Best for stateless, high-throughput caching.**

---

## 🛠️ Example: Using SASL Authentication

If your Memcached server is configured with SASL:

```python
backend = MemcachedBackend(
    host="localhost",
    port=11211,
    username="myuser",
    password="mypassword"
)
```

---

## 🔗 See Also

- [Backends Overview](../backends.md)
- [API Reference](../api.md)
- [Usage Guide](../usage.md)