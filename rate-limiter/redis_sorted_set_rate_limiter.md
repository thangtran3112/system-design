
# Redis Sorted Set Rate Limiter

This document provides a detailed implementation of a **sliding window rate limiter** using **Redis Sorted Sets**, along with Python and Lua scripting examples, and a system architecture overview.

---

## 🔹 Use Case

> Limit each user to **100 requests per 60 seconds**, with precise sliding window behavior.

---

## 📈 Architecture Overview

```
+------------+     HTTP Request     +------------------+
|   Client   |  ----------------->  |  API Gateway /   |
|            |                      |   Rate Limiter   |
+------------+                      +--------+---------+
                                            |
                                            v
                                    +---------------+
                                    | Redis (ZSET)  |
                                    +---------------+
```

- **API Gateway / Rate Limiter** performs Redis ZSET operations per user
- Sorted Set stores request timestamps (as scores)
- Tracks only requests in the last N seconds

---

## 🔧 Python Implementation

```python
import time
import redis

r = redis.Redis(host='localhost', port=6379)

def is_allowed(user_id: str, limit: int = 100, window: int = 60) -> bool:
    key = f"rate:{user_id}"
    now = time.time()
    start = now - window

    pipeline = r.pipeline()

    # Remove expired entries
    pipeline.zremrangebyscore(key, 0, start)

    # Add current request with unique member and current time as score
    entry = f"{now}-{user_id}"
    pipeline.zadd(key, {entry: now})

    # Count entries in the window
    pipeline.zcard(key)

    # Set key expiry to auto-clean
    pipeline.expire(key, window)

    _, _, count, _ = pipeline.execute()

    return count <= limit
```

### ✅ Explanation of Redis Commands

#### `ZREMRANGEBYSCORE key min max`
Removes all elements in the sorted set where the score is between `min` and `max`.
- Used here to remove all timestamps older than the sliding window.
- Keeps only recent requests (within the last N seconds).

#### `ZCARD key`
Returns the number of elements in the sorted set.
- After cleaning old entries, this gives the count of valid requests in the current time window.

---

## 🧪 Lua Script for Atomic Operation

```lua
-- rate_limiter.lua
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

-- Remove old entries
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- Add new request
redis.call('ZADD', key, now, member)

-- Count requests in window
local count = redis.call('ZCARD', key)

-- Set TTL
redis.call('EXPIRE', key, window)

if count > limit then
    return 0
else
    return 1
end
```

### Python usage:

```python
with open("rate_limiter.lua", "r") as f:
    lua_script = f.read()

rate_limiter = r.register_script(lua_script)

user_id = "user123"
now = time.time()
member = f"{now}-{user_id}"
allowed = rate_limiter(keys=[f"rate:{user_id}"], args=[now, 60, 100, member])
if allowed:
    print("✅ Allowed")
else:
    print("⛔ Blocked")
```

---

## 🗃 Redis Key Example

```
Key:    rate:user123
Type:   Sorted Set
Member: 1715891530.123-user123
Score:  1715891530.123 (event time)
```

---

## ✅ Benefits

| Feature           | Description                             |
|------------------|-----------------------------------------|
| Sliding accuracy | Rolling window, not fixed intervals     |
| Precision        | Based on event timestamp                |
| Clean-up         | Auto-remove old entries and expire keys |
| Scalability      | One key per user                        |

---

## 🔐 Best Practices

- Set TTL with `EXPIRE` to prevent memory leaks
- Use `ZREMRANGEBYSCORE` frequently to avoid stale data
- Include unique members (e.g. timestamp-userid) to avoid collisions

---

## 🌐 Summary

- Redis Sorted Set lets you build a **sliding window rate limiter** with per-request granularity
- Supports **high-throughput**, **accurate** throttling
- Use **Lua scripting** for atomicity in distributed environments

---

Would you like to combine this with a Flask or FastAPI middleware for real-time API protection?
