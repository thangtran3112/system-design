ZooKeeper-based URL Shortener with Base62 and Kafka Integration

This document explains how to build a URL shortener system using:
• ✅ Apache ZooKeeper for global unique ID generation
• ✅ Base62 encoding for short and URL-safe codes
• ✅ Redis or PostgreSQL for mapping short → long URLs
• ✅ Optional Kafka for logging or processing events asynchronously

⸻

🧠 Architecture Overview

          +--------------+         +-------------+

User ---> | Flask API | -----> | ZooKeeper | (generates sequential ID)
+------+-------+ +-------------+
|
v
+--------+---------+
| Encode to Base62 |
+--------+---------+
|
+----------+----------+
| Store in Redis/Postgres |
| (short → long mapping) |
+----------+----------+
|
v
[ Optional Kafka ]
(Produce usage/log event)

⸻

🧠 Why Use ZooKeeper for URL Shortening?

ZooKeeper offers strong consistency and atomic operations that make it useful for distributed counters:
• Generates globally unique sequential IDs
• Guarantees ordered ID assignment
• Enables concurrent-safe short code generation

⸻

🧠 How to Use ZooKeeper to Manage Counter for Short URLs

ZooKeeper can act as a distributed, strongly consistent counter system by using sequential znodes:

✅ Step-by-Step 1. Create a sequential znode under a base path:

/create /shorturl/url\_ -

This creates znodes like:

/shorturl/url_0000000001
/shorturl/url_0000000002

    2.	When a new short URL is requested, your app:
    •	Calls zk.create('/shorturl/url_', sequence=True)
    •	Gets back a znode name like /shorturl/url_0000000057
    3.	Extract the numeric part and encode with Base62:

unique*id = int(znode_path.split("*")[-1])
short_code = base62_encode(unique_id)

    4.	Store the mapping in a key-value store:

redis.set(f"url:{short_code}", long_url)

✅ Benefits
• Globally consistent IDs with no race conditions
• Distributed-safe generation from multiple nodes
• No need for a centralized auto-increment SQL ID

⚠️ Caveats

Limitation Detail
Performance ZooKeeper is not meant for high-frequency writes
Expiry You’ll need to clean up znodes over time
Complexity Adds infrastructure overhead vs simple counters

Use ZooKeeper when you want strong consistency and reliable ID generation in a distributed system.

⸻

🔍 Step-by-Step Workflow

1. ZooKeeper generates a unique sequential znode:

/create /shorturl/url\_ -

Example: /shorturl/url_0000000007

2. Extract numeric suffix and convert to Base62:

unique*id = int(znode_name.split("*")[-1])
short_code = base62_encode(unique_id)

3. Store the mapping in Redis/PostgreSQL:

rdb.set(f"url:{short_code}", original_url)

4. (Optional) Produce event to Kafka:

producer.send("url_created", {"code": short_code, "url": original_url})

⸻

⚙️ Base62 Encoding

import string
BASE62 = string.digits + string.ascii_letters

def base62_encode(num):
result = []
while num > 0:
num, rem = divmod(num, 62)
result.append(BASE62[rem])
return ''.join(reversed(result)) or '0'

⸻

🌐 Flask API Example

from flask import Flask, request, jsonify, redirect
from kazoo.client import KazooClient
import redis, string

app = Flask(**name**)
BASE62 = string.digits + string.ascii_letters

def base62_encode(num):
result = []
while num > 0:
num, rem = divmod(num, 62)
result.append(BASE62[rem])
return ''.join(reversed(result)) or '0'

zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()
zk.ensure_path("/shorturl")

rdb = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.route("/shorten", methods=["POST"])
def shorten():
long_url = request.json.get("url")
if not long_url:
return jsonify({"error": "Missing URL"}), 400

    node_path = zk.create("/shorturl/url_", b"", sequence=True, ephemeral=False)
    seq = int(node_path.split("_")[-1])
    short_code = base62_encode(seq)

    rdb.set(f"url:{short_code}", long_url)
    return jsonify({"short_code": short_code, "short_url": f"http://localhost:5000/{short_code}"})

@app.route("/<short_code>")
def redirect_short(short_code):
long_url = rdb.get(f"url:{short_code}")
if not long_url:
return jsonify({"error": "Not found"}), 404
return redirect(long_url)

⸻

🎯 Kafka Integration (Optional)

from kafka import KafkaProducer
import json

kafka_producer = KafkaProducer(
bootstrap_servers='localhost:9092',
value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

kafka_producer.send('url_created', {
"short_code": short_code,
"long_url": long_url
})

⸻

🔗 Component Summary

Component Responsibility
ZooKeeper Centralized, consistent ID generation
Redis/Postgres Mapping short → long URLs
Flask API User interface to shorten/redirect
Base62 URL-safe short codes
Kafka Asynchronous event pipeline (optional)

⸻

📈 Scalability Notes
• ZooKeeper is great for strong consistency but not for high-frequency ID generation
• Consider Snowflake, Redis INCR, or UUID + hash for massive scale
• TTLs can be used on Redis keys if links are meant to expire

⸻

Let us know if you’d like:
• A Docker Compose setup
• PostgreSQL-backed persistence
• Prometheus/Grafana monitoring
• Analytics pipeline with Kafka consumers
