# 🗄️ Backends Overview

FastAPI Cachekit supports multiple cache backends, so you can choose the best fit for your application’s needs—whether you want blazing-fast in-memory caching for development, or distributed caching for production.

---

## Supported Backends

| Backend           | Description                                         | Best For                | Docs                                   |
|-------------------|-----------------------------------------------------|-------------------------|----------------------------------------|
| InMemoryBackend   | Stores cache in the app’s memory (LRU support)      | Development, testing    | [In-Memory](backends/in_memory.md)     |
| RedisBackend      | Uses Redis for distributed, production caching       | Production, scaling     | [Redis](backends/redis.md)             |
| PostgresBackend   | Uses PostgreSQL for persistent SQL-based caching     | Data persistence, SQL   | [Postgres](backends/postgres.md)       |
| MemcachedBackend  | Uses Memcached for high-speed distributed caching    | High-speed, stateless   | [Memcached](backends/memcached.md)     |
| MongoDBBackend    | Uses MongoDB for document-based distributed caching  | NoSQL, flexible schema  | [MongoDB](backends/mongodb.md)         |
| FirestoreBackend  | Uses Google Firestore for serverless NoSQL caching   | Serverless, GCP users   | [Firestore](backends/firestore.md)     |
| DynamoDBBackend   | Uses AWS DynamoDB for serverless NoSQL caching       | Serverless, AWS users   | [DynamoDB](backends/dynamodb.md)       |
---

## How to Choose a Backend

- **InMemoryBackend**  
  - 🟢 Easiest to set up, no extra dependencies.
  - 🟡 Not shared between processes or servers.
  - 🟡 Data lost on restart.
  

- **RedisBackend**  
  - 🟢 Distributed, scalable, and fast.
  - 🟢 Widely used in production.
  - 🟡 Requires a running Redis server.

- **PostgresBackend**  
  - 🟢 Uses your existing PostgreSQL database.
  - 🟢 Data persists across restarts.
  - 🟡 Slightly slower than in-memory or Redis.
  

- **MemcachedBackend**  
  - 🟢 High-speed, distributed, simple.
  - 🟡 No persistence (data lost on restart).
  - 🟡 No built-in authentication by default.
  

- **MongoDBBackend**
  - 🟢 Persistent storage (data survives restarts).
  - 🟢 Built-in TTL index for automatic cache expiration.
  - 🟢 Supports authentication and access control.
  - 🟡 Slower than in-memory caches (e.g., Memcached).
  

- **FirestoreBackend**
  - 🟢 Persistent, serverless NoSQL storage (data survives restarts).
  - 🟢 Native TTL support for automatic cache expiration.
  - 🟢 Scales automatically with Google Cloud infrastructure.
  - 🟢 Supports authentication and fine-grained access control.
  - 🟡 Slightly higher latency compared to in-memory caches.
  - 🟡 Requires Google Cloud project and credentials.
  

- **DynamoDBBackend**
  - 🟢 Persistent, serverless NoSQL storage (data survives restarts).
  - 🟢 Native TTL support for automatic cache expiration.
  - 🟢 Scales automatically with AWS infrastructure.
  - 🟢 Supports IAM authentication and access control.
  - 🟡 Slightly higher latency compared to in-memory caches.
  - 🟡 Requires AWS account and credentials.

---
---

## Installation for Each Backend

See the [Installation Guide](installation.md) for details on installing optional dependencies for each backend.

---

## Backend Setup Guides

- [In-Memory Backend](backends/in_memory.md)
- [Redis Backend](backends/redis.md)
- [Postgres Backend](backends/postgres.md)
- [Memcached Backend](backends/memcached.md)
- [MongoDB Backend](backends/mongodb.md)
- [Firestore Backend](backends/firestore.md)
- [DynamoDB Backend](backends/dynamodb.md)
---

## Adding More Backends

Want to add support for another backend?  
Open an issue or submit a pull request on [GitHub](https://github.com/devbijay/fast-cache)!

---

**FastAPI Cachekit makes it easy to switch backends with minimal code changes—just swap the backend class and you’re ready to go!**