# 🛠️ Scheduled Task Executor with Redis Sorted Sets and Distributed Locks

This system allows you to:
- Store long-term job/task metadata in **DynamoDB**
- Push near-future execution tasks into **Redis**
- Use **Redis Sorted Set (ZSET)** to sort tasks by `execution_timestamp`
- Enforce **distributed locking** via Redis to prevent double execution
- Automatically recover from crashed workers with lock expiration

---

## 🧱 Architecture

```
+----------------+         +--------------------+
| DynamoDB       |         |  Scheduler Service |
| - Jobs         |         |                    |
| - Tasks        |  --->   | Polls & pushes     |
| - Executions   |         | near-future tasks  |
+----------------+         | into Redis ZSET    |
                           +---------+----------+
                                     |
                          +----------v----------+
                          |  Redis               |
                          |  - ZSET: sorted by   |
                          |    execution time    |
                          |  - LOCKS per task ID |
                          +----------+-----------+
                                     |
                  +------------------+-------------------+
                  |                                      |
         +--------v---------+                  +---------v--------+
         | Worker A         |                  | Worker B         |
         | - Poll ZSET      |                  | - Poll ZSET      |
         | - Lock & execute |                  | - Lock & execute |
         +------------------+                  +------------------+
```

---

## 🔑 Redis Structures

### 🔹 Sorted Set: `scheduled_tasks`
- Key: `scheduled_tasks`
- Member: `task_id`
- Score: `execution_timestamp` (UNIX epoch)

### 🔹 Lock: `lock:task:{task_id}`
- Set via `SET key value NX PX 30000` (30s TTL)

---

## 🧪 Sample Redis Code (Python + redis-py)

```python
import redis
import time
import uuid

r = redis.Redis()

LOCK_TIMEOUT_MS = 30_000

def acquire_lock(task_id):
    lock_key = f"lock:task:{task_id}"
    lock_token = str(uuid.uuid4())
    success = r.set(lock_key, lock_token, nx=True, px=LOCK_TIMEOUT_MS)
    return lock_token if success else None

def release_lock(task_id, token):
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    r.eval(lua_script, 1, f"lock:task:{task_id}", token)

def get_due_tasks(current_ts):
    return r.zrangebyscore("scheduled_tasks", 0, current_ts)

# Example polling loop
def poll_and_execute():
    while True:
        now = int(time.time())
        tasks = get_due_tasks(now)
        for task_id in tasks:
            token = acquire_lock(task_id)
            if token:
                try:
                    print("Executing", task_id)
                    r.zrem("scheduled_tasks", task_id)
                    # your execution logic...
                finally:
                    release_lock(task_id, token)
        time.sleep(1)
```

---

## 🚦 Performance Notes & Concerns

| Concern                  | Mitigation                         |
|--------------------------|-------------------------------------|
| Too many tasks in Redis  | Only push next N minutes of tasks  |
| ZSET size grows unbounded | Periodically prune old items       |
| Lock leaks / crashes     | TTL auto-expires after 30s         |
| Worker starvation        | Use fair polling / partition by hash |
| High volume concurrency  | Shard ZSET per bucket/time window  |

---

## ✅ Best Practices

- Push only **next 5–15 minutes** of executions into Redis
- Use Redis `ZPOPMIN` (if atomic removal needed)
- Consider `BLPOP` or PubSub for push-style models
- Use a **dedicated Redis cluster** for lock-sensitive workloads

---

Let me know if you'd like a Terraform setup or production-ready retry/backoff logic!
