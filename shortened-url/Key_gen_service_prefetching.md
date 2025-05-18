Key Generation Service (KGS) Design

This document outlines the design and implementation strategy for a scalable, collision-free Key Generation Service (KGS), typically used in systems like URL shorteners.

⸻

📏 Goals
• Pre-generate short keys (e.g., Base62 7-char strings)
• Guarantee uniqueness and no collisions
• Handle concurrent access safely
• Provide a consistent, auditable record of used keys
• Optimize performance using in-memory buffering

⸻

🛠️ Architecture Overview

+--------------------+ +-----------------+
| Key Generation API | -----> | available_keys | (SELECT/UPDATE key)
+--------+-----------+ +-----------------+
|
| Move on use
v
+--------+-----------+ +-----------------+
| In-Memory Queue | -----> | used_keys | (audit log)
+--------------------+ +-----------------+

⸻

📄 Database Schema

available_keys

id (PK) key is_reserved reserved_at
1 abcD12X false NULL

used_keys

id (PK) key used_at
1 abcD12X 2024-05-16T12:00:00Z

⸻

🔐 Handling Concurrent Access

Option 1: Atomic SQL Update

UPDATE available_keys
SET is_reserved = true, reserved_at = NOW()
WHERE is_reserved = false
ORDER BY id
LIMIT 1
RETURNING key;

Option 2: Transactional Move (Preferred)

BEGIN;
DELETE FROM available_keys
WHERE id = (SELECT id FROM available_keys LIMIT 1 FOR UPDATE SKIP LOCKED)
RETURNING key;

INSERT INTO used_keys (key, used_at) VALUES ($1, NOW());
COMMIT;

This prevents race conditions and double-use of the same key.

⸻

⚡ In-Memory Buffering

Use a memory queue to improve read speed:

from collections import deque
key_cache = deque()

def preload_keys(n=1000):
rows = db.query("""
UPDATE available_keys
SET is_reserved = TRUE, reserved_at = NOW()
WHERE is_reserved = FALSE
LIMIT %s RETURNING key
""", (n,))
for row in rows:
key_cache.append(row['key'])

def get_next_key():
if not key_cache:
preload_keys()
key = key_cache.popleft()
db.execute("INSERT INTO used_keys (key, used_at) VALUES (%s, NOW())", (key,))
return key

⸻

🌐 Key Generation Job

A batch job can prefill the pool with keys:

def generate*keys(n=1_000_000):
for * in range(n):
new_key = generate_random_base62(length=7)
db.execute("INSERT INTO available_keys (key) VALUES (%s) ON CONFLICT DO NOTHING", (new_key,))

⸻

🏛 Scaling and Safety
• Works across multiple KGS server instances
• Central DB or distributed store ensures consistency
• Optionally use Redis with SPOP for atomic pops
• Optional rate-limiting or key expiration policies

⸻

🔒 Reliability and Guarantees

Feature Implementation
Unique keys UNIQUE constraint in available_keys
No duplication Atomic DELETE + INSERT transaction
Concurrent-safe FOR UPDATE SKIP LOCKED or Redis pop
Fast access In-memory prefetch queue
Auditable usage used_keys table with timestamps

⸻

🔗 Summary

Component Role
DB Table 1 Store unused/pre-generated keys
DB Table 2 Archive used keys
KGS API Serve next available key
Buffer Speed up access with local memory
Batch Job Periodically refill the key pool

⸻

Let us know if you want code for:
• PostgreSQL schema migrations
• Docker-compose for DB + KGS
• REST or gRPC API endpoints for use in production
