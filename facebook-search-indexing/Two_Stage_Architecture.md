# Two-Stage Indexing Architecture for High-Volume Likes

This document captures a series of questions and answers regarding the two-stage indexing architecture used to handle systems where likes vastly outnumber posts (e.g., Facebook or Ticketmaster-like systems).

---

## ❓ User Question

**Q:** _Explain the two-stage architecture for indexing Facebook-like interactions, as the number of likes is very high, 10 times more than the number of posts._

### 📘 Context Provided
> We can do even better by only updating the like count in our indexes when it passes specific milestones like powers of 2 or 10. So we would write to the index when the post has 1 like, 2 likes, 4 likes, etc. This reduces the number of writes exponentially - we no longer have to make 1000 writes for 1000 likes, we only have to make 10.
> But this isn't without a tradeoff! This would mean our index is inherently stale - the data cannot be completely trusted. But the ordering is approximately correct. The post with 10k likes will definitely be in front of the post with 0 or 1 like.
> If we want to retrieve N posts for a given query, we grab the top N*2 posts from the Like index. For each post in that list, we query the Like Service for the up-to-date like count. Then we sort using that fresh like count before returning to the user.
> In this case our storage is an approximation but our end result is precise - it has the most recent data. This style of two-architecture, where we have an approximately correct service that is backed by a more expensive re-ranking is very common in information retrieval and recommendation systems.

---

## 🧠 Answer: Two-Stage Indexing Strategy

### Stage 1: Approximate, Low-Cost Indexing

#### ✅ Purpose
Reduce the write and storage overhead from the **massive number of likes** by storing **only milestone-like events**.

#### 📦 How It Works
- Index is updated only when like counts hit milestones (e.g., 1, 2, 4, 8, ...).
- Logarithmic write scaling: 1000 likes → only ~10 index updates.

#### 📉 Tradeoff
- Index is **stale** and doesn't reflect the exact number of likes.
- Approximate ordering is still mostly accurate for large deltas.

---

### Stage 2: Precise, High-Cost Reranking

#### ✅ Purpose
Ensure final results returned to the user are **accurate and real-time**.

#### 🔍 How It Works
1. Retrieve top N×2 posts from the approximate index.
2. Query **Like Service** for exact like counts.
3. Sort and rerank the results before returning to the user.

---

### ⚖️ Summary Comparison Table

| Feature               | Stage 1: Approximate Index      | Stage 2: Accurate Rerank         |
|-----------------------|----------------------------------|----------------------------------|
| Purpose               | Fast, low-cost writes & reads    | High-fidelity user results       |
| Update Frequency      | Sparse (e.g., at 2ⁿ milestones)  | Real-time on query               |
| Data Accuracy         | Stale, approximate               | Fresh, exact                     |
| Performance           | Fast and cheap                   | Slower and more expensive        |
| Example Use Cases     | Filtering, candidate generation  | Final sort, display              |

---

### ✅ Use Cases
- Large-scale feeds (e.g., Facebook, LinkedIn)
- Recommendation systems
- Ranking systems where freshness matters, but throughput is huge

---

## ❓ Follow-up Question

**Q:** _Is ZooKeeper leader-based or quorum-based?_

### 🧠 Answer
Apache **ZooKeeper** uses **both**:
- 👑 **Leader Node**: Elected to coordinate all **writes**.
- 👥 **Followers**: Serve **reads** and vote in quorum decisions.
- ✅ **Quorum-Based Consensus**: Writes only succeed when **majority (quorum)** of nodes acknowledge.
- 🛠️ Uses **ZAB protocol** to ensure consistency and leader election.

---

## ❓ Follow-up Question

**Q:** _What are possible libraries to write a coding editor like LeetCode or HackerRank for frontend?_

### 🧰 Libraries for Web-Based Code Editors

| Library         | Features                                                   |
|------------------|------------------------------------------------------------|
| **Monaco Editor** | Used in VS Code, supports IntelliSense, themes, languages |
| **CodeMirror**   | Lightweight, modular, used in Jupyter                      |
| **Ace Editor**   | Mature, performant, less modern                            |

### 🧠 Extras
- **Judge0** / Docker backend for execution
- **Yjs** or **Automerge** for real-time editing
- **shadcn/ui**, **Tailwind**, **Framer Motion** for UI

---

## ❓ Follow-up Question

**Q:** _Does the partition key need to be unique in DynamoDB?_

### 🧠 Answer

| Key Type                  | Partition Key Uniqueness |
|---------------------------|---------------------------|
| **Simple Primary Key**    | ✅ Must be unique          |
| **Composite Primary Key** | ❌ Not required to be unique |

- Composite key = (partition key + sort key) → the combination must be unique.
- Repeating partition keys with different sort keys is allowed.

---

## ❓ Follow-up Question

**Q:** _Explain how the 2-stage architecture is working in this diagram?_  
*(Diagram: Like Service, Kafka, Redis, Ingestion, Search Service)*

### 🧱 Stage 1: Approximate Indexing via Ingestion and Redis

- Like events go through Kafka → Batching → Ingestion Service
- Index is updated **only at milestone thresholds**
- Indexed into **Redis** and optionally into **Cold Indexes (Blob)**

### 🧠 Stage 2: Real-Time Re-ranking

- Client queries go through **CDN → API Gateway → Search Service**
- Results are fetched from Redis index
- Search Service fetches **fresh like counts from Like Service**
- Final sort is done and results are returned

---

## ✅ Benefits of the Architecture

- ✅ **Scalable writes** through batching
- ✅ **Low-latency reads** with Redis
- ✅ **Accuracy** preserved through re-ranking
- ✅ **Storage efficiency** using milestone thresholds and cold indexing

