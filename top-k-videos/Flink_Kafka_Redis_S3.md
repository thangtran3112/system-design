
# Real-Time Video View Counting and Top-K Ranking with Apache Flink, Kafka, Redis, and S3

This project demonstrates how to build a real-time data pipeline using **Apache Flink** to process video view events from **Kafka**, increment per-video counters in **Redis**, and maintain **Top-K rankings** using Redis Sorted Sets. Flink state is checkpointed to **Amazon S3** for fault tolerance.

---

## 📌 Architecture Overview

```
           +------------+           +-------------+         +--------+
Viewers -> |   Kafka    |  ----->   |   Flink App  |  --->   | Redis  |
           +------------+           +-------------+         +--------+
                                       |     |                |
                                       |     +--> Checkpoints |
                                       |           to S3      |
                                       v
                         +--------------------------------+
                         | Redis Sorted Set: top_videos   |
                         | Redis Keys: video:view:count:* |
                         +--------------------------------+
```

---

## 🔁 Kafka Input Schema

Each Kafka message is expected to be a JSON object:
```json
{
  "userId": "user123",
  "videoId": "video456",
  "timestamp": "2025-05-25T13:00:00Z"
}
```

---

## 🔧 Redis Data Model

- **Sorted Set** (`top_videos`):  
  Stores view counts for each `videoId`:
  ```
  ZINCRBY top_videos 1 video456
  ```

- **String Counter** (`video:view:count:<videoId>`):  
  Stores individual video view count:
  ```
  INCR video:view:count:video456
  ```

---

## ✅ Java Flink Snippet

### Flink Setup with Kafka and Redis

```java
FlinkKafkaConsumer<String> kafkaConsumer = new FlinkKafkaConsumer<>(
    "video-views",
    new SimpleStringSchema(),
    properties
);

env
    .addSource(kafkaConsumer)
    .flatMap(new RedisIncrProcessor());
```

### RedisIncrProcessor

```java
public static class RedisIncrProcessor extends RichFlatMapFunction<String, Void> {
    private transient Jedis jedis;

    @Override
    public void open(Configuration parameters) {
        this.jedis = new Jedis("your-redis-host", 6379);
    }

    @Override
    public void flatMap(String value, Collector<Void> out) {
        JSONObject json = new JSONObject(value);
        String videoId = json.getString("videoId");
        if (videoId != null && !videoId.isEmpty()) {
            jedis.zincrby("top_videos", 1, videoId);
            jedis.incr("video:view:count:" + videoId);
        }
    }

    @Override
    public void close() {
        if (jedis != null) jedis.close();
    }
}
```

---

## 🗃️ Checkpointing to S3

Enable checkpointing in Flink:
```java
env.enableCheckpointing(60000, CheckpointingMode.EXACTLY_ONCE);
env.getCheckpointConfig().setCheckpointStorage("s3://your-s3-bucket/flink-checkpoints");
```

Make sure to:
- Use the correct **S3 credentials**
- Include Flink S3 filesystem plugin (`flink-s3-fs-hadoop` or `presto`)
- Replace `"s3://your-s3-bucket/..."` with a valid bucket path

---

## 🧠 Optional Enhancements

- Use `ZREVRANGE top_videos 0 9 WITHSCORES` to query top 10 videos
- Implement Redis expiration for daily/hourly leaderboards
- Use RedisBloom Top-K for memory efficiency (if RedisBloom module is available)
- Add sliding windows in Flink for time-bounded top-k tracking

---

## ✅ Tools and Versions

- Apache Flink 1.14+
- Kafka 2.x
- Redis 5.x or 6.x
- Java 8 or 11
- AWS S3 with proper permissions

---

## 📬 Contact

Feel free to reach out for questions about scaling, state backend tuning, or stream partitioning strategies.
