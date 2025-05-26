
# 📉 Price Drop Notification System with Kafka, Cassandra, Redis

This system processes real-time price drops and notifies users who are watching specific products based on their desired price threshold.

---

## 🏗️ Architecture Overview

```
+-------------------------+
| Kafka: price_updates    |
| (productId, newPrice)   |
+-------------------------+
           |
           v
+------------------------------+
| PriceDropNotifierService     |
| - Consumes Kafka stream      |
| - Reads from Cassandra/Redis |
| - Publishes notification req |
+------------------------------+
           |
           v
+-----------------------------+
| Kafka: user_notifications   |
+-----------------------------+
           |
           v
+-----------------------------+
| Notification Service        |
| - Reads notifications       |
| - Sends email/push/SMS      |
+-----------------------------+
```

---

## 🗃️ Cassandra Table Design

```sql
CREATE TABLE price_watch_alerts (
    product_id TEXT,
    price_watch_value DECIMAL,
    user_id TEXT,
    PRIMARY KEY ((product_id), price_watch_value, user_id)
) WITH CLUSTERING ORDER BY (price_watch_value ASC);
```

### ✅ Why This Works

- Partition key: `product_id` → efficient lookup by product
- Clustering key: `price_watch_value ASC` → efficient range scan for price drop match
- Query pattern:
```sql
SELECT user_id
FROM price_watch_alerts
WHERE product_id = 'P123'
AND price_watch_value >= 79.99;
```
→ Returns users who should be notified

---

## 🔥 Redis Optimization for Hot Products

Some products (e.g., iPhones) have many watchers = potential hot partition in Cassandra.

### ✅ Redis Caching Strategy

- On first query miss, cache the matching watchers:
  - `redis.setex("price_watch:P123:80", user_list, ttl=300)`
- On price update:
  - Check Redis for key: `price_watch:{product_id}:{new_price_bucket}`
  - Fall back to Cassandra if cache miss
- Invalidate or update cache asynchronously

---

## 🧠 Optimization for Products with Frequent Updates

When a product has very frequent price changes (e.g., auction items, flash sales), triggering a full read and notification for each small price drop causes:

- 🔁 Repeated fanout writes
- 🔥 Overloading Redis or Kafka producers
- 🐘 Cassandra pressure on hot partitions

### 💡 Solution: Bucketed Watch and Notification Design

Use price **buckets** to group watchers and minimize query fanout:

```sql
CREATE TABLE price_watch_buckets (
    product_id TEXT,
    price_bucket INT,
    user_id TEXT,
    PRIMARY KEY ((product_id, price_bucket), user_id)
)
```

#### ✅ How it works:

- Convert each user’s watch price into a bucket:
  - e.g., `price_bucket = FLOOR(watch_price / 10)`
- On price update:
  - Compute the bucket range:
    - If new_price = 83 → notify all users with `price_bucket >= 8`
  - Query only relevant buckets:
```sql
SELECT user_id FROM price_watch_buckets
WHERE product_id = 'P123' AND price_bucket >= 8;
```

- Reduces per-query result set size
- Smooths Cassandra partition distribution
- Improves Redis cache key precision

---

## 📬 Notification Publishing

When userIds are found, publish them to Kafka:

```json
{
  "userId": "user123",
  "productId": "P123",
  "newPrice": 79.99
}
```

Kafka topic: `user_notifications`

---

## 🛡️ Reliability Features

- Kafka offset checkpointing
- S3 sink for backup or retries
- Retry queue in Redis for temporary delivery failure
- Deduplication key: `userId:productId:newPrice`

---

## ✅ Suggestions

- Use Redis for hot-shard caching
- Use TTLs on Redis to reduce staleness
- Use async consumer group to scale `PriceDropNotifierService`
- Bucket prices if scan volume is large or price changes are frequent
- Monitor Cassandra read latency and partition heatmap

---

## 📁 Files Included

- `README.md` (this file)
