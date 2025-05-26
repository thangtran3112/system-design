
# Redis + Flink Java Sliding Window View Counter (Rising & Falling Edge Strategy)

This document explains how to implement an accurate, real-time sliding window Top-K system for video views using Apache Flink, Redis, and Kafka with a **rising/falling edge strategy**.

---

## 🧠 Concept Summary: Rising & Falling Edges

You want to track video views in **sliding time windows** (like 1 hour, 1 day, 1 week, and all-time). Every video view event affects multiple windows:

- **Rising edge** = when a view arrives → **increment** all relevant counters
- **Falling edge** = when that view is too old for a window → **decrement** that specific window’s counters

---

## 🗂 Redis Key Schema

### 1. Count Hashes

Stores raw view counts:
```
HINCRBY view:count:<window>:<time_bucket> <videoId> ±1
```

### 2. Sorted Sets (Top-K)

Tracks scores per video:
```
ZINCRBY top:videos:<window>:<time_bucket> ±1 <videoId>
```

### Time Buckets

- Hour: `2025-05-25T13`
- Day: `2025-05-25`
- Week: `2025-W21`
- All-Time: `all`

---

## 📥 Rising Edge Example

A new view at `2025-05-25T13:42:00` for `video123`:

```bash
HINCRBY view:count:hour:2025-05-25T13 video123 1
ZINCRBY top:videos:hour:2025-05-25T13 1 video123
...
(same for day/week/all)
```

---

## 📤 Falling Edge Example

At `2025-05-25T14:42:00`, the 1-hour window evicts the above view:

```bash
HINCRBY view:count:hour:2025-05-25T13 video123 -1
ZINCRBY top:videos:hour:2025-05-25T13 -1 video123
```

Other windows (day/week/all) retain it until their pointers catch up.

---

## ✅ Flink Java Processor Code

```java
import org.apache.flink.api.common.functions.RichFlatMapFunction;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.util.Collector;
import org.json.JSONObject;
import redis.clients.jedis.Jedis;

import java.time.*;
import java.time.format.DateTimeFormatter;

public class RedisViewProcessor extends RichFlatMapFunction<String, Void> {
    private transient Jedis redis;

    @Override
    public void open(Configuration parameters) {
        redis = new Jedis("your-redis-host", 6379);
    }

    @Override
    public void flatMap(String value, Collector<Void> out) {
        JSONObject json = new JSONObject(value);
        String videoId = json.getString("videoId");
        String eventTimeStr = json.getString("timestamp"); // ISO8601 format
        boolean isFallingEdge = json.optBoolean("falling", false);
        int increment = isFallingEdge ? -1 : 1;

        ZonedDateTime eventTime = ZonedDateTime.parse(eventTimeStr);
        String hour = eventTime.truncatedTo(ChronoUnit.HOURS).toString();
        String day = eventTime.toLocalDate().toString();
        String week = YearWeek.from(eventTime).toString();

        updateRedis("hour", hour, videoId, increment);
        updateRedis("day", day, videoId, increment);
        updateRedis("week", week, videoId, increment);
        updateRedis("all", "all", videoId, increment);
    }

    private void updateRedis(String window, String bucket, String videoId, int inc) {
        String countKey = String.format("view:count:%s:%s", window, bucket);
        String topKKey = String.format("top:videos:%s:%s", window, bucket);
        redis.hincrBy(countKey, videoId, inc);
        redis.zincrby(topKKey, inc, videoId);
    }

    @Override
    public void close() {
        if (redis != null) redis.close();
    }

    static class YearWeek {
        static String from(ZonedDateTime dt) {
            WeekFields weekFields = WeekFields.ISO;
            int weekNumber = dt.get(weekFields.weekOfWeekBasedYear());
            int year = dt.get(weekFields.weekBasedYear());
            return String.format("%d-W%02d", year, weekNumber);
        }
    }
}
```

---

## 🔁 Input Event Example

```json
{
  "videoId": "video123",
  "timestamp": "2025-05-25T13:42:00Z",
  "falling": false
}
```

---

## 🔧 Redis Queries

```bash
ZREVRANGE top:videos:hour:2025-05-25T13 0 9 WITHSCORES
ZREVRANGE top:videos:day:2025-05-25 0 9 WITHSCORES
ZREVRANGE top:videos:all 0 9 WITHSCORES
```

---

## 🧹 Expiring Old Keys

```bash
EXPIRE view:count:hour:2025-05-25T13 3600
EXPIRE top:videos:hour:2025-05-25T13 3600
```

---

## ✅ Summary

- **Kafka stream** feeds events into Flink
- Flink distinguishes **rising** vs **falling** edges
- Redis keys store windowed counters + Top-K
- Durable, accurate, real-time sliding windows
