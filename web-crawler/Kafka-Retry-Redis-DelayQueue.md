# 🔁 Kafka Retry Topics + Redis ZSET Delay Queue

This document explains how to combine Kafka **retry topics** with a **Redis ZSET-based delay queue** to implement scheduled and retryable job execution — useful for crawlers, data pipelines, and task scheduling.

---

## 📦 Components

| Component        | Purpose                                       |
|------------------|-----------------------------------------------|
| Kafka Topic      | Real-time execution of due jobs               |
| Retry Topics     | Delay retry attempts for failed jobs          |
| Redis ZSET       | Time-based delay queue for job scheduling     |
| DLQ              | Dead-letter queue for permanent failures      |

---

## 🧱 Architecture

```
+--------------+       +-------------------+
| Redis ZSET   | <---> | Scheduler Worker  | (polls due jobs)
| (delayed jobs)|      |                   |
+------+-------+       +---------+---------+
                            |
                            v
                    +---------------+
                    | Kafka Topic   | ("crawl-jobs")
                    +---------------+
                            |
                            v
                   +----------------+
                   | Crawler Worker |
                   +----------------+
                            |
              +-------------+--------------+
              | Retry Topics (5s, 30s, 1m) |
              +-------------+--------------+
                            |
                            v
                          DLQ
```

---

## 🧠 Redis ZSET Delay Queue

### 🔹 Schema:
- Redis ZSET where:
  - `key`: `delay-queue`
  - `member`: JSON job
  - `score`: UNIX timestamp (when the job is due)

### 🔹 Producer: Add scheduled job to Redis

```python
import redis
import time
import json

r = redis.Redis()

def schedule_job(job, delay_seconds):
    due_time = int(time.time()) + delay_seconds
    r.zadd("delay-queue", {json.dumps(job): due_time})
```

---

### 🔹 Scheduler Worker: Poll due jobs and push to Kafka

```python
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode()
)

def fetch_and_enqueue_due_jobs():
    now = int(time.time())
    jobs = r.zrangebyscore("delay-queue", 0, now)

    for job_json in jobs:
        job = json.loads(job_json)
        producer.send("crawl-jobs", value=job)
        r.zrem("delay-queue", job_json)  # remove after enqueue
```

⏱ Run every few seconds via a cron job, scheduler, or loop.

---

## 🔁 Kafka Retry Topic Strategy (Exponential Backoff)

When a job fails in the crawler:

```python
def send_to_retry_topic(job, retry_count):
    retry_topics = {
        1: ("crawl-jobs-retry-5s", 5),
        2: ("crawl-jobs-retry-30s", 30),
        3: ("crawl-jobs-retry-1m", 60),
    }

    topic, delay = retry_topics.get(retry_count, ("crawl-jobs-dlq", 0))
    job["retry_count"] = retry_count
    producer.send(topic, value=job)
```

---

### 🔄 Retry Consumers

Each retry topic has a consumer that waits `delay` seconds and requeues the job:

```python
def retry_consumer(retry_topic, delay_seconds):
    consumer = KafkaConsumer(
        retry_topic,
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda v: json.loads(v.decode()),
        group_id=f"{retry_topic}-group"
    )
    for msg in consumer:
        time.sleep(delay_seconds)
        producer.send("crawl-jobs", value=msg.value)
```

---

## ✅ Use Cases

| Use Case               | Solution                      |
|------------------------|-------------------------------|
| Scheduled crawling     | Redis ZSET delay queue        |
| Retry after failure    | Kafka retry topics            |
| Exponential backoff    | Multiple retry topics         |
| Long delay persistence | Redis or external store       |

---

## 🛠️ Tips

- Use Redis key expiration or ZREM to manage memory
- Ensure job ID is unique or deduplicated
- Monitor DLQ for failed jobs

---

Let me know if you'd like Flink or Airflow integration!
