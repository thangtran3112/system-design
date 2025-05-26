
# Real-Time Top-K Songs View Count with PyFlink, Kafka, Redis, and S3

This project implements a scalable, streaming architecture to compute **Top-K most viewed songs** for each `videoId` using **sliding windows** over the **last hour**, **last day**, and **last week**.

---

## 📐 Architecture Overview

```
Kafka (video_view_events topic)
        |
        V
+----------------------+
|   Flink Jobs (per    |
|   videoId shard)     |
|  - 1h sliding window |
|  - 1d sliding window |
|  - 1w sliding window |
+----------------------+
        |
        V
Redis (per-video Top-K store)
        |
        V
+-------------------------+
| Global Aggregator       |
| - Scans Redis keys      |
| - Merges per-video topK |
| - Updates global_topk:* |
+-------------------------+
```

- **Kafka**: Receives real-time song view events.
- **Flink (PyFlink)**: Processes events per videoId and computes top-K using sliding event-time windows.
- **Redis**: Stores the top-K results per videoId and window (`topk:{videoId}:{window}`).
- **Global Aggregator**: Merges all per-video results into a global Top-K (`global_topk:{window}`).
- **S3**: Used for checkpointing Flink jobs.

---

## 🧪 Sliding Window Jobs

Each Flink job uses the following windows:

| Window    | Size        | Slide Interval |
|-----------|-------------|----------------|
| `1h`      | 60 minutes  | 5 minutes      |
| `1d`      | 24 hours    | 1 hour         |
| `1w`      | 7 days      | 1 day          |

---

## 📁 Files Included

- `pyflink_topk_global.py`: Main PyFlink job code + Redis aggregator
- `flink_topk_architecture.java`: Java version for windowed Top-K jobs (per-videoId shard)
- `README.md`: This file

---

## ✅ Setup Suggestions

- Use **Kafka partitions** to shard by `videoId` for parallelism.
- Use **event-time watermarks** for time correctness with late data.
- Use **Redis Sorted Sets** (`ZADD`) for efficient top-K inserts and reads.
- Run the global aggregator periodically (e.g., every minute/hour/day).
- Monitor **Redis memory** usage as key cardinality grows.
- Scale Flink parallelism by `videoId % num_shards`.

---

## 💡 Improvements

- Use **Flink SQL** or **Table API** for declarative windowing.
- Use **Redis Cluster** if scaling to large cardinality.
- Use **Bloom Filters** to reduce unnecessary Redis ZADD operations.
- Push global_topk to **Elasticsearch or REST API** for analytics frontend.

