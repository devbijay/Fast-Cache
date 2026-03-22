# Changelog

## v0.2.0

### New Features
- Distributed cache stampede protection via Redis locking
- Python 3.14 support

### Bug Fixes
- Fix infinite loop in `InMemoryBackend` cleanup scheduler thread ([#3](https://github.com/devbijay/Fast-Cache/issues/3))
- Fix Firestore cleanup using wrong client type when batch exceeds 500 docs
- Fix DynamoDB async resource leak in `_get_async_table()` — properly handles `__aenter__`/`__aexit__`
- Fix cache decorator not caching `None` return values — uses sentinel value instead of `None` check
- Fix `AttributeError` after `InMemoryBackend.close()` — cache is now cleared instead of destroyed
- Fix async pool/table race condition in Postgres and DynamoDB backends using double-checked locking
- Add warning logs to silent exception handlers in Redis, Memcached, and DynamoDB backends

### Testing
- Add concurrency tests for async initialization in Postgres and DynamoDB backends
- Add Redis lock unit tests (acquire, release, exclusivity, auto-expiry)
- Add Python 3.14 to tox test matrix
