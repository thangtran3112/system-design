
# Scalable Sharded Video View Counter with Redis and Java

This guide outlines a scalable architecture and Java implementation for tracking and aggregating video view counts across billions of videos using Redis. It uses **hash-based sharding** and **time-based partitioning**, suitable for large-scale platforms like YouTube.

---

## 📌 Architecture Overview

```
                   Kafka / API Ingest
                          ↓
                     +--------+
                     | Shard  |  (hash(videoId) % N)
                     +--------+
                          ↓
                +------------------+
                | Redis Shard Keys |
                +------------------+
                | video:view:shard:{shard_id}:day:YYYY-MM-DD
                +------------------+
                          ↓
        Periodic Aggregator (Flink / Spark / Cron Job)
                          ↓
            Redis Sorted Set: top_videos:day:YYYY-MM-DD
```

---

## 🔧 Redis Shard Key Strategy

Use hashed shard buckets:
```
HINCRBY video:view:shard:{shard_id}:day:2025-05-25 video123 1
```

Or:
```
ZINCRBY video:view:shard:{shard_id}:day:2025-05-25 1 video123
```

---

## ✅ Java Code Example: Shard Writing

```java
import redis.clients.jedis.Jedis;
import java.time.LocalDate;
import java.util.zip.CRC32;

public class VideoViewSharder {
    private static final int NUM_SHARDS = 128;
    private final Jedis redis;

    public VideoViewSharder(String redisHost) {
        this.redis = new Jedis(redisHost, 6379);
    }

    private int getShardIndex(String videoId) {
        CRC32 crc = new CRC32();
        crc.update(videoId.getBytes());
        return (int)(crc.getValue() % NUM_SHARDS);
    }

    public void incrementView(String videoId) {
        int shard = getShardIndex(videoId);
        String date = LocalDate.now().toString();  // e.g., 2025-05-25
        String key = String.format("video:view:shard:%d:day:%s", shard, date);
        redis.zincrby(key, 1, videoId);
    }
}
```

---

## 🧮 Java Code Example: Aggregation from Shards

```java
import java.util.*;
import redis.clients.jedis.Jedis;

public class TopKAggregator {

    private static final int NUM_SHARDS = 128;
    private static final int TOP_K = 100;

    private final Jedis redis;

    public TopKAggregator(String redisHost) {
        this.redis = new Jedis(redisHost);
    }

    public void aggregateTopK(String date) {
        Map<String, Double> globalCounts = new HashMap<>();

        for (int i = 0; i < NUM_SHARDS; i++) {
            String key = String.format("video:view:shard:%d:day:%s", i, date);
            Set<redis.clients.jedis.Tuple> data = redis.zrevrangeWithScores(key, 0, -1);
            for (redis.clients.jedis.Tuple t : data) {
                globalCounts.merge(t.getElement(), t.getScore(), Double::sum);
            }
        }

        // Write to top_videos global sorted set
        String topKey = "top_videos:day:" + date;
        redis.del(topKey);
        globalCounts.entrySet().stream()
            .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
            .limit(TOP_K)
            .forEach(e -> redis.zadd(topKey, e.getValue(), e.getKey()));
    }
}
```

---

## 🧠 Why This Works

- ✅ Sharding prevents hotspots on Redis
- ✅ Time-based partitioning allows TTL and time-windowed analytics
- ✅ Aggregation is decoupled and parallelizable
- ✅ Sorted sets enable real-time top-K ranking

---

## 🔧 Requirements

- Java 8+
- Redis 6+
- Jedis client (`redis.clients:jedis`)
- Optional: Flink/Spark/cron scheduler for aggregations

---

## 📈 Querying Top Videos

```bash
ZREVRANGE top_videos:day:2025-05-25 0 9 WITHSCORES
```

---

For advanced sharding strategies, TTL cleanup, or Flink integration, feel free to reach out.
