# 🚀 Installation

FastAPI Cachekit is designed to be easy to install and flexible for any workflow.  
You can use **pip**, **uv**, or **poetry** and only install the backends you need.

---

## 📦 Basic Installation (In-Memory Only)

Install the core package (in-memory backend only):

### **pip**
```
pip install fastapi-cachekit
```

### **uv**
```
uv add fastapi-cachekit
```

### **poetry**
```
poetry add fastapi-cachekit
```

---

## 🔌 Optional Backends

You can install support for Redis, Postgres, or Memcached by specifying the appropriate "extra".

### **Redis Backend**

- **pip**
  ```
  pip install fastapi-cachekit[redis]
  ```
- **uv**
  ```
  uv add fastapi-cachekit[redis]
  ```
- **poetry**
  ```
  poetry add fastapi-cachekit -E redis
  ```

### **Postgres Backend**

- **pip**
  ```
  pip install fastapi-cachekit[postgres]
  ```
- **uv**
  ```
  uv add fastapi-cachekit[postgres]
  ```
- **poetry**
  ```
  poetry add fastapi-cachekit -E postgres
  ```

### **Memcached Backend**

- **pip**
  ```
  pip install fastapi-cachekit[memcached]
  ```
- **uv**
  ```
  uv add fastapi-cachekit[memcached]
  ```
- **poetry**
  ```
  poetry add fastapi-cachekit -E memcached
  ```

---

## 🧩 Install All Backends

If you want to install all supported backends at once:

- **pip**
  ```
  pip install fastapi-cachekit[all]
  ```
- **uv**
  ```
  uv add fastapi-cachekit[all]
  ```
- **poetry**
  ```
  poetry add fastapi-cachekit -E all
  ```

---

## 🛠️ Development & Testing

For development (with test and dev dependencies):

- **uv**
  ```
  uv sync --all-group
  ```
- **poetry**
  ```
  poetry install --with dev
  ```

---

## ⚡️ Notes

- You only need to install the backend(s) you plan to use.
- All backends support both **sync** and **async** APIs.

---

**Next:** [Usage Guide →](usage.md)