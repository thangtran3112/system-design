# Two-Stage Indexing Strategy for High-Volume Systems

This document explains the two-stage indexing architecture used to efficiently handle large-scale interactions like Facebook-style post "likes", where write volume (likes) significantly outpaces read volume (posts).

---

## 🧱 Stage 1: Approximate Indexing via Ingestion and Redis

### 💡 Goal
Efficiently ingest a **large volume of likes and post creations**, minimizing storage and processing overhead.

### 🔁 Workflow Breakdown

1. **Event Ingestion**
   - **Post Service** and **Like Service** emit events when users create posts or like content.
   - These events are routed through a **Load Balancer → Event Writer → Kafka** pipeline.
   - **Kafka** decouples producers (services) and consumers (like the ingestion system), enabling scalable buffering and stream processing.

2. **Like Batcher**
   - Pulls events from Kafka, **aggregates likes** (e.g., only significant count changes like powers of 2).
   - Reduces write amplification by not writing every single like.
   - Follows the pattern described earlier: write only when like counts cross thresholds (1, 2, 4, 8, ...).

3. **Ingestion Service**
   - Consumes batched events.
   - Updates the **"Likes" and "Creation" indexes in Redis**, which serve as the fast-access approximate index.
     - Likes: `keyword → [PostIds]` sorted by milestone-like counts.
     - Creation: `keyword → [PostIds]` for recent/new content.

4. **Cold Indexing**
   - Less-frequently accessed or historical index data is pushed to **blob storage**.
   - This allows for efficient large-scale backup, batch processing, or archival search.

---

## 🧠 Stage 2: Real-Time Re-ranking via Search Service and Like Service

### 💡 Goal
Deliver **precise and up-to-date results** to the client, compensating for stale data in the fast index.

### 🔍 Query Path (Client Search):

1. **Client Query Flow**
   - A client sends a search request (e.g., for trending or relevant posts).
   - The request hits a **CDN**, then routes to the **API Gateway** and **Search Service**.

2. **Fast Lookup**
   - The **Search Service** consults:
     - **Search Cache (Redis)** for hot queries.
     - **Index (Redis)** for precomputed like-based and creation-based post lists.

3. **Re-ranking Step**
   - After retrieving a **larger candidate set** (e.g., top 2×N posts), the Search Service **queries the Like Service** to get the **latest like counts**.
   - It **reranks posts** based on fresh like counts before returning the final result set to the client.

---

## 📦 Summary of the Two-Stage Strategy

| Stage | Component(s)                   | Role                                         |
|-------|--------------------------------|----------------------------------------------|
| **1** | Kafka, Like Batcher, Redis     | Approximate indexing at milestone thresholds |
| **2** | Search Service, Like Service   | Reranking with real-time precision           |

---

## ✅ Benefits

- **Write efficiency**: Reduces pressure from high-like-volume by batching.
- **Fast reads**: Redis-based approximate index gives low-latency initial results.
- **Accuracy**: Final reranking ensures fresh and trustworthy results.
- **Scalability**: Kafka and blob storage allow for asynchronous and decoupled processing.
