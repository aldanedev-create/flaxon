
# Performance

## Overview

Flaxon is designed to provide efficient performance for modern backend applications.

It focuses on:

- Low framework overhead
- Efficient asynchronous I/O
- Scalable request handling
- Developer-friendly performance optimization

Flaxon is optimized for **I/O-bound workloads** such as:

- APIs
- Web applications
- Real-time applications
- Dashboards
- Chat systems
- Background services

It is not designed to make CPU-heavy calculations faster. CPU-intensive workloads should use specialized tools, worker processes, or optimized services.

---

# Performance Philosophy

"Fast" should be measured by real-world performance.

Flaxon's performance goals focus on:

- Low request overhead
- Efficient concurrency
- Reduced unnecessary processing
- Predictable scaling behavior

Performance claims should be based on measurable benchmarks rather than comparing languages or frameworks in general.

Flaxon does not claim that Python is always faster than Node.js, Java, Go, or Rust. Instead, it focuses on making Python practical for scalable production applications.

---

# Optimization Areas

| Area | Optimization | Measurement |
|------|--------------|-------------|
| Routing | Precompiled routes and efficient route matching | Requests/second, latency |
| JSON Handling | Compact encoding and optional faster serializers | Serialization time, payload size |
| Middleware | Minimal processing overhead | Per-layer execution time |
| Validation | Cached schema metadata | Validation latency |
| Templates | Compiled template caching | Render time, cache hit rate |
| WebSockets | Efficient connections, queues, and room management | Connections, messages/second |

---

# Scaling Model

Flaxon applications should scale using proven backend architecture patterns.

Recommended approach:

1. Keep HTTP workers stateless.
2. Run multiple application processes for reliability and performance.
3. Store persistent data in databases and object storage.
4. Use Redis for:
   - Caching
   - Rate limiting
   - Sessions
   - WebSocket message distribution
5. Move CPU-heavy workloads to background workers or specialized services.
6. Use reverse proxies for:
   - TLS termination
   - Traffic management
   - Health checks
   - Rolling deployments

---

# Benchmarking

Flaxon provides benchmark tools inside the `benchmarks/` directory.

Run all benchmarks:

```bash
python scripts/benchmark.py
````

Run a specific benchmark:

```bash
python benchmarks/routing_benchmark.py
```

Benchmark results should always be measured on the target hardware and deployment environment.

---

# Performance Tips

## Use Async Where Possible

For I/O operations such as databases, APIs, and file operations, use asynchronous functions.

### Recommended

```python
async def get_user(user_id: int):
    return await db.fetch_row(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
```

### Avoid Blocking Operations

```python
def get_user(user_id: int):
    return db.fetch_row_sync(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
```

Blocking operations can reduce concurrency and slow down applications handling many requests.

---

# Use Connection Pooling

Database connection pools improve performance by reusing existing connections.

Example:

```python
@app.on_startup
async def startup():
    app.state.db = await create_pool()


@app.get("/users")
async def get_users():

    async with app.state.db.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM users"
        )
```

---

# Cache Frequently Accessed Data

Caching reduces repeated database queries and improves response times.

Example:

```python
from flaxon.caching import cached_async


@cached_async(ttl=60)
async def get_users():

    return await db.fetch_all(
        "SELECT * FROM users"
    )
```

---

# Use Redis for Distributed Rate Limiting

For applications running multiple servers, distributed rate limiting can be handled with Redis.

Example:

```python
from flaxon.security import DistributedRateLimiter


limiter = DistributedRateLimiter(
    redis_client
)


@app.get("/api")
async def api(request):

    allowed = await limiter.check(
        request.client[0],
        requests=60
    )

    if not allowed:
        raise HTTPException(
            429,
            "Too many requests"
        )
```

---

# Realistic Performance Goals

Flaxon aims to make Python a strong choice for many production workloads, including:

* APIs
* Social platforms
* Chat applications
* Dashboards
* Mobile backends
* Internal enterprise systems

For extremely high-performance components, applications can combine Flaxon with:

* Background workers
* Message queues
* Optimized databases
* Specialized services
* Other programming languages when required

The goal is not to replace every technology, but to provide a flexible foundation for building scalable applications with Python.


## Measured request-path improvements

Endpoint argument metadata is prepared at route registration, and untouched sessions are not stored. See [request performance and migration](guides/request-security-upgrade.md) and the reproducible `benchmarks/cross_runtime/` suite. Results are workload-specific; development time and developer-defect reduction remain unmeasured.
