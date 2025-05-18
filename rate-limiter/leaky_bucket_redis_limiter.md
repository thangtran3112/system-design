
# Redis Leaky Bucket Rate Limiter

This document provides an overview and implementation of a **Leaky Bucket** rate limiter using **Redis**. The Leaky Bucket algorithm is a popular traffic shaping method that **allows bursts** of traffic but **enforces a steady outflow rate** over time.

---

## 💧 What Is the Leaky Bucket Algorithm?

Imagine a bucket with a **small hole** at the bottom:
- Water (requests) can be added to the bucket (within capacity)
- Water leaks out at a **fixed rate**
- If you add water too fast (more than leak rate), the bucket overflows → requests are **rejected**

---

## 🎯 Use Case

> Allow short bursts of requests, but ensure an average rate of N requests per T seconds.

Examples:
- Allow 10 requests immediately
- Then allow 1 request every second after that

---

## 📦 Redis Data Model

Use a Redis `HASH` to store per-user bucket state:

```
Key: bucket:user123
Fields:
  tokens        → number of remaining tokens in bucket
  last_refill   → UNIX timestamp of last refill check
```

---

## 🧪 Python Implementation

```python
import time
import redis

r = redis.Redis()

def allow_request(user_id, capacity=10, leak_rate=1):
    key = f"bucket:{user_id}"
    now = time.time()

    # Load existing bucket or default values
    bucket = r.hmget(key, "tokens", "last_refill")
    tokens = int(bucket[0]) if bucket[0] else capacity
    last_refill = float(bucket[1]) if bucket[1] else now

    # Calculate leaked tokens since last update
    elapsed = now - last_refill
    leaked_tokens = int(elapsed * leak_rate)
    tokens = min(capacity, tokens + leaked_tokens)
    last_refill = last_refill + leaked_tokens / leak_rate if leaked_tokens else last_refill

    if tokens > 0:
        tokens -= 1
        r.hmset(key, {"tokens": tokens, "last_refill": last_refill})
        return True
    else:
        r.hmset(key, {"tokens": tokens, "last_refill": last_refill})
        return False
```

### 🧾 Explanation of Redis Commands

#### `HMGET key field1 field2 ...`
Fetches the values of specified fields in a hash. Returns `None` for missing fields.
- Used here to retrieve `tokens` and `last_refill` values.

#### `HMSET key field1 value1 field2 value2 ...`
Sets multiple fields of a hash in a single atomic operation.
- Used to update the current token count and refill timestamp.

---

## 🔄 Behavior Summary

| Time (s) | Bucket Tokens | last_refill        | Action             |
|----------|----------------|--------------------|--------------------|
| 0        | 10             | 1715891700.0       | ✅ Request allowed |
| 1        | 9              | 1715891700.0       | ✅ Request allowed |
| 2        | 9 (leaks 1)    | 1715891701.0       | ✅ Request allowed |
| 3        | 9 (leaks 1)    | 1715891702.0       | ✅ Request allowed |
| ...      | ...            | ...                |                    |
| 12       | 10             | 1715891710.0       | Bucket refilled    |

---

## 🔁 Redis Key Example

```
Key:    bucket:user123
Type:   Hash
Fields:
  tokens      → 3
  last_refill → 1715891703.82
```

---

## 🧪 Lua Script Implementation (Atomic)

```lua
-- leaky_bucket.lua
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local rate = tonumber(ARGV[3])

local bucket = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

local elapsed = now - last_refill
local leaked = math.floor(elapsed * rate)
tokens = math.min(capacity, tokens + leaked)
if leaked > 0 then
  last_refill = last_refill + leaked / rate
end

if tokens > 0 then
  tokens = tokens - 1
  redis.call("HMSET", key, "tokens", tokens, "last_refill", last_refill)
  return 1
else
  redis.call("HMSET", key, "tokens", tokens, "last_refill", last_refill)
  return 0
end
```

### Python usage:

```python
with open("leaky_bucket.lua", "r") as f:
    lua_script = f.read()

leaky_bucket = r.register_script(lua_script)
user_id = "user123"
now = time.time()
allowed = leaky_bucket(keys=[f"bucket:{user_id}"], args=[now, 10, 1])
if allowed:
    print("✅ Allowed")
else:
    print("⛔ Blocked")
```

---

## ⚙️ Best Practices

- Set `EXPIRE` on Redis keys for inactive users (e.g., 10× refill interval)
- Use Lua script for atomic behavior in distributed environments
- Prevent drift using Redis time or NTP synchronization

---

## ✅ Advantages

| Feature       | Benefit                            |
|---------------|-------------------------------------|
| Bursty access | Allows short traffic bursts         |
| Leak control  | Smooths out request spikes          |
| Stateless     | Each bucket is isolated in Redis    |
| Extensible    | Add IP-level or route-level buckets |

---

## 📌 Summary

- The **Leaky Bucket** algorithm enforces rate limiting with **burst tolerance** and **steady draining**
- Redis provides fast, atomic state management via hash updates or Lua scripting
- Suitable for **user**, **IP**, or **API route-level** controls

---

Would you like integration with a real-time framework like FastAPI or a Docker Compose setup for testing?
