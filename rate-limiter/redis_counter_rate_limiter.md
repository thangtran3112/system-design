
# Redis Counter Rate Limiter (Fixed Window)

This document explains how to implement a simple **fixed window rate limiter** using Redis `INCR` and `EXPIRE`. It also compares this approach with other Redis-based techniques like **Sliding Window with ZSET**, **Leaky Bucket**, and **Token Bucket**.

---

## 🎯 Use Case

> Allow N requests per user per fixed time window (e.g. 100 requests per minute).

---

## 🧱 How It Works

- Redis key is based on user ID and time window
- Use `INCR` to increment count
- Use `EXPIRE` to reset counter after window ends

### Redis Key Format:
```
rate:<user_id>:<time_bucket>
```
Example:
```
rate:user123:20240516T1015
```

---

## 🧪 Python Example

```python
import time
import redis
from datetime import datetime

r = redis.Redis()

def is_allowed(user_id, limit=100, window_seconds=60):
    now = int(time.time())
    window = now // window_seconds
    key = f"rate:{user_id}:{window}"

    current = r.incr(key)
    if current == 1:
        r.expire(key, window_seconds)

    return current <= limit
```

If `is_allowed()` returns `False`, your server should return an HTTP `429 Too Many Requests` response:

```python
if not is_allowed(user_id):
    return Response("Rate limit exceeded", status=429)
```

---

## 🏗️ Architecture Overview

```
+------------+     Request     +---------------------+
|   Client   |  ------------>  |  Web API / Gateway  |
+------------+                +-----------+---------+
                                        |
                              +---------v----------+
                              | Redis (Fixed Key)  |
                              +--------------------+
```

- Each client sends requests to the API Gateway
- The gateway checks a Redis counter with `INCR`
- If the request count is over the limit, it returns HTTP **429**

---

## 🔄 Redis Command Summary

- `INCR key`: Atomically increases the counter
- `EXPIRE key TTL`: Sets TTL so key is auto-removed at window boundary

---

## ✅ Benefits

| Feature         | Benefit                          |
|----------------|----------------------------------|
| Fast           | One atomic Redis call (`INCR`)   |
| Simple         | No sorted sets or hashing needed |
| Scalable       | Independent keys per user        |

---

## ⚠️ Limitations

| Limitation        | Description                                                     |
|-------------------|-----------------------------------------------------------------|
| Bursts allowed    | Allows full limit at start and end of window (double burst)     |
| Rigid time window | All users reset at the same boundary (e.g., :00, :01, ...)      |
| Inflexible window | Cannot slide or overlap; fixed interval only                    |

---

## 🧠 Comparison with Other Redis Rate Limiter Techniques

| Technique        | Precision       | Bursty | Complexity | Storage    | Use Case                            |
|------------------|----------------|--------|------------|------------|-------------------------------------|
| Counter (Fixed)  | ❌ Coarse       | ✅ Yes  | ⭐ Very low | 🔑 1 key/user/window | Simple APIs, coarse limits         |
| Sliding Window   | ✅ High         | ✅ Yes  | ⭐⭐ Medium | 📚 Sorted Set        | Fine-grained, rolling limits       |
| Leaky Bucket     | ✅ Medium       | ✅ Yes  | ⭐⭐ Medium | 🧩 Hash + time        | Smooth flow control, bursty APIs   |
| Token Bucket     | ✅ Medium       | ✅ Yes  | ⭐⭐ Medium | 🧩 Hash + math        | Credit-based, refillable access    |

---

## 📌 Summary

The **fixed window counter** rate limiter with Redis is:
- ⚡ Fast and atomic
- 🧠 Easy to reason about
- ✅ Best for **basic throttling**

However, consider **sliding window** or **leaky bucket** approaches when you need:
- Smoother request distribution
- Burst mitigation
- Rolling windows

---

Would you like to add a Lua version, metrics tracking, or combine it with Flask/FastAPI middleware?
