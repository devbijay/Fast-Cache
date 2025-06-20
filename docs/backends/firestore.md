# Firestore Backend

## Installation

```bash
pip install fastapi-cachekit[firestore]
```

## Setup with FastAPI

```python
from fast_cache import cache, FirestoreBackend

backend = FirestoreBackend(
    credential_path="path/to/your/service-account.json",  # Optional if using GOOGLE_APPLICATION_CREDENTIALS
    namespace="my-namespace",                             # Optional
    collection_name="cache_entries"                       # Optional
)
cache.init_app(app, backend)
```

## Options

- `credential_path`: Path to your Google Cloud service account JSON file.  
  If not provided, uses the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
- `namespace`: Key prefix for all cache entries (default: `"fastapi_cache"`).
- `collection_name`: Firestore collection to use for cache entries (default: `"cache_entries"`).

## Example Usage

```python
@app.get("/expensive")
@cache.cached(expire=60)
async def expensive_operation(x: int):
    return {"result": x * 2}
```

## Tips

- Use Firestore for serverless, scalable caching with Google Cloud.
- For local development or CI, you can use the [Firestore Emulator](https://cloud.google.com/sdk/gcloud/reference/beta/emulators/firestore/).
- Make sure your service account has Firestore access, or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
- The backend supports both sync and async operations.