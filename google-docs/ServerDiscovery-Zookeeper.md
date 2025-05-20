# 📝 Real-Time Document Editing with Consistent Hashing and Zookeeper

This guide explains how to design a **Google Docs-style collaborative editor** using:
- **WebSocket-based backend servers**
- **Zookeeper for service discovery**
- **Consistent Hashing** to route users to appropriate servers

---

## 📦 Core Components

| Component         | Purpose                                           |
|------------------|----------------------------------------------------|
| WebSocket Servers | Handle client sessions and document sync          |
| Zookeeper         | Tracks live server nodes (ephemeral)              |
| Gateway           | Assigns users to correct backend using hash ring  |
| Redis/Postgres    | Stores persistent document state (optional)       |

---

## 🧱 High-Level Architecture

```
            +-----------+
  Clients → |  Gateway  | (routes by consistent hashing)
            +-----------+
                 ↓
        +---------------------+
        | Hash Ring (Zookeeper)|
        +---------------------+
         ↓         ↓         ↓
   +--------+ +--------+ +--------+
   | Server1| |Server2 | |Server3 |
   +--------+ +--------+ +--------+
        ↓
     Document DB / CRDT
```

---

## 🔐 Zookeeper: Server Registration

Each WebSocket server registers under `/doc-servers` as an **ephemeral znode**:

```shell
/doc-servers/server-1
/doc-servers/server-2
/doc-servers/server-3
```

Each node's data may include host and port info:

```json
{
  "host": "10.1.2.3",
  "port": 8080
}
```

### 🔧 Server Registration Example

```python
from kazoo.client import KazooClient
import json, socket

zk = KazooClient(hosts='localhost:2181')
zk.start()

server_id = socket.gethostname()
meta = json.dumps({"host": "10.1.2.3", "port": 8080}).encode()

zk.ensure_path("/doc-servers")
zk.create(f"/doc-servers/{server_id}", meta, ephemeral=True)
```

---

## 🔄 How Zookeeper Tracks Server Liveness (Ephemeral Nodes)

### What is an Ephemeral Node?

- A znode that exists only as long as the session that created it remains alive.
- If the client **crashes**, **loses network**, or **exceeds the session timeout**, the ephemeral node is deleted.

### Session Keep-Alive Mechanism:

1. Zookeeper client sends **heartbeats (pings)**.
2. If no heartbeat is received within the configured `sessionTimeout`, the session **expires**.
3. All ephemeral nodes created by the client are **deleted automatically**.
4. Other services watching `/doc-servers` will be notified of server loss.

### Watchers for Server List:

```python
@zk.ChildrenWatch("/doc-servers")
def on_change(children):
    print("Active servers:", children)
```

### Best Practices:

| Tip                         | Reason                                      |
|-----------------------------|---------------------------------------------|
| Use ephemeral znodes        | Automatically reflect live servers          |
| Handle session expiry       | Re-register upon reconnect                  |
| Use short timeouts + pings  | Detect failures quickly                     |

---

## 🔁 Consistent Hash Ring

We use a consistent hashing ring to ensure that:

- All users working on the same `doc_id` go to the same server
- The ring adjusts dynamically when servers join/leave

### Python Example

```python
import hashlib
from bisect import bisect_right

class ConsistentHashRing:
    def __init__(self, nodes, replicas=100):
        self.ring = {}
        self.sorted_keys = []
        for node in nodes:
            for i in range(replicas):
                key = self.hash(f"{node}:{i}")
                self.ring[key] = node
                self.sorted_keys.append(key)
        self.sorted_keys.sort()

    def hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def get_node(self, key):
        h = self.hash(key)
        index = bisect_right(self.sorted_keys, h) % len(self.sorted_keys)
        return self.ring[self.sorted_keys[index]]
```

---

## 🌐 Client Routing via Gateway

On WebSocket connect:

1. Extract `doc_id`
2. Query Zookeeper for active `/doc-servers`
3. Use consistent hash ring to get target server
4. **Redirect client** (HTTP 307 / WebSocket reconnect) to that server

```python
doc_id = "doc-123"
server_id = ring.get_node(doc_id)

# Lookup server metadata
data, _ = zk.get(f"/doc-servers/{server_id}")
info = json.loads(data.decode())  # {host: x, port: y}
```

### 🧭 Redirect Protocol

- If using HTTP handshake → return 307 redirect to correct WebSocket URL
- Or send initial message to client telling them to reconnect

```json
{
  "action": "redirect",
  "target": "wss://doc-server-3.example.com"
}
```

Client then disconnects and reconnects to the correct host.

---

## 🛠️ Server Failover

- When a WebSocket server crashes:
  - Its znode disappears (ephemeral)
  - Hash ring is rebuilt
  - Future clients route to a new server

---

## ✅ Summary

| Feature             | Solution                            |
|---------------------|--------------------------------------|
| Server coordination | Zookeeper + ephemeral znodes         |
| Load distribution   | Consistent hashing on `doc_id`       |
| Server discovery    | ZK path `/doc-servers/`              |
| Real-time sync      | WebSocket + CRDT or OT               |
| Client redirection  | Gateway or client-side logic         |

---

Let me know if you'd like a codebase template or demo cluster to try it out!
