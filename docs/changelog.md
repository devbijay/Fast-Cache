# Changelog

## v0.2.1

### Bug Fixes
- Fix stampede protection recomputing the value once per waiting request — waiters now reuse the value cached by the lock holder
- Fix `timedelta` expiration being silently ignored by `RedisBackend`, which left values uncached
- Fix `MemcachedBackend` rejecting keys with whitespace or longer than 250 bytes, which prevented caching any function called with keyword arguments; such keys are now hashed
- Fix expiration timestamps being truncated to whole seconds in DynamoDB, MongoDB and Firestore backends, which could expire entries up to a second early
- Fix MongoDB TTL index never removing expired documents — entries now include an `expires_at_date` field used by the TTL index
- Fix `MongoDBBackend.set()` without `expire` keeping the previous expiration of an existing key
- Fix `lifespan_handler` failing on startup with `TypeError: 'State' object does not support item assignment`
- Fix `lifespan_handler` not awaiting async backend `close()`, leaving Redis, Memcached and DynamoDB connections open
- Pin `apscheduler<4`, as APScheduler 4 removes the scheduler API used by the in-memory, Postgres and Firestore backends

### Behavior Changes
- Cache backend errors inside `@cached` are now logged and the wrapped function runs normally, instead of the error propagating. Errors raised by the wrapped function itself still propagate.

### New Features
- `RedisBackend.try_acquire_lock()` / `atry_acquire_lock()`: single non-blocking lock attempt that raises on Redis errors. Used by `@cached` to skip lock waiting when Redis is unreachable.

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
