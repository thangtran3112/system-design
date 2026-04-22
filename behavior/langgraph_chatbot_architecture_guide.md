# LangGraph Chatbot Architecture Guide
## Redis Active State + Postgres Durable State + Qdrant Cross-Thread Memory
### With FastAPI, orchestration prompts, MCP-style tool routing, and summarization

---

## Table of contents

1. [What this architecture solves](#what-this-architecture-solves)
2. [High-level architecture](#high-level-architecture)
3. [Why use Redis, Postgres, and Qdrant together](#why-use-redis-postgres-and-qdrant-together)
4. [Core data model](#core-data-model)
5. [End-to-end request flow](#end-to-end-request-flow)
6. [Short-term vs long-term memory](#short-term-vs-long-term-memory)
7. [Summarization strategy](#summarization-strategy)
8. [LangMem-style summarization concepts](#langmem-style-summarization-concepts)
9. [Orchestration node pattern](#orchestration-node-pattern)
10. [MCP tool execution pattern](#mcp-tool-execution-pattern)
11. [Reference project structure](#reference-project-structure)
12. [Example code: combined implementation](#example-code-combined-implementation)
13. [Production considerations](#production-considerations)
14. [Common pitfalls](#common-pitfalls)
15. [Interview-ready summary](#interview-ready-summary)

---

## What this architecture solves

A production chatbot usually needs three different storage behaviors at the same time:

- **Fast active state** so a conversation can continue with low latency.
- **Durable state** so the system can recover after crashes, restarts, or deployments.
- **Cross-thread semantic memory** so the agent can remember useful things across multiple threads and retrieve them later.

A good split is:

- **Redis** for active thread state and hot cache.
- **Postgres** for durable conversation history and checkpoints.
- **Qdrant** for semantic memory, summaries, and extracted user preferences across threads.

This gives you:

- low latency
- recovery after failures
- auditability
- thread continuity
- cross-thread memory retrieval
- cleaner prompt management via summarization

---

## High-level architecture

```text
Client
  ↓
FastAPI
  ↓
LangGraph
  ├── Orchestration / planner node
  ├── Memory retrieval node
  ├── Summarization node
  ├── Tool execution node(s)
  └── Response generation node
  ↓
Storage / memory layers
  ├── Redis      → active thread state, TTL cache
  ├── Postgres   → durable messages, checkpoints, audit trail
  └── Qdrant     → cross-thread summaries and semantic memories
```

---

## Why use Redis, Postgres, and Qdrant together

### Redis
Use Redis for:

- current thread state
- recent messages
- current workflow step
- temporary tool outputs
- rate-limited session data
- short-lived cache

Why:

- very fast
- ideal for active conversations
- easy TTL eviction
- reduces repeated database reads

### Postgres
Use Postgres for:

- full conversation transcript
- exact message chronology
- checkpoints
- audit logs
- approvals
- operational recovery

Why:

- durable
- transactional
- queryable
- good system of record

### Qdrant
Use Qdrant for:

- semantic summaries
- user preferences
- extracted long-term memories
- retrieval across threads
- optional embedding storage for selected turns

Why:

- semantic search
- metadata filtering
- strong fit for multi-tenant memory retrieval

---

## Core data model

Think in terms of three layers of memory.

### 1. Active thread state
Hot state for the current thread.

```python
class AgentState(TypedDict, total=False):
    tenant_id: str
    user_id: str
    thread_id: str
    messages: list[dict]
    summary: str
    retrieved_memories: list[dict]
    plan: dict
    tool_result: dict
    final_answer: str
```

### 2. Durable transcript
Canonical exact history in Postgres.

Example tables:

- `conversation_threads`
- `conversation_messages`
- `workflow_checkpoints`

### 3. Semantic memory
Stored in Qdrant with payload metadata like:

- `tenant_id`
- `user_id`
- `thread_id`
- `kind` = `summary` or `memory`
- `timestamp`
- `source`

---

## End-to-end request flow

A good request flow looks like this:

1. Receive user message in FastAPI.
2. Load active state from Redis.
3. If Redis misses, rebuild from Postgres checkpoint/history.
4. Append the new user message.
5. Retrieve relevant long-term semantic memory from Qdrant.
6. Run orchestration node to decide what happens next.
7. Optionally summarize old messages if active context is large.
8. Execute tool or workflow if needed.
9. Generate final response.
10. Save updated active state back to Redis.
11. Save durable transcript and checkpoint to Postgres.
12. Save summary or memory extracts to Qdrant when relevant.

---

## Short-term vs long-term memory

### Short-term memory
Thread-scoped memory:

- recent user and assistant messages
- current workflow step
- current tool outputs
- latest running summary

Best store:

- Redis as hot store
- Postgres as durable store

### Long-term memory
Cross-thread memory:

- user preferences
- recurring facts
- durable goals
- past issue summaries
- previously resolved technical context

Best store:

- Qdrant for semantic retrieval
- Postgres optionally for source-of-truth backup

---

## Summarization strategy

A chatbot eventually hits context-window and cost problems if every message is sent to the LLM forever.

The standard pattern is:

- keep the **latest few turns** verbatim
- maintain a **running summary** of older turns
- retrieve **cross-thread semantic memory** only when relevant

### Recommended summary contents

When summarizing, preserve:

- user preferences
- goals
- important facts
- unresolved tasks
- decisions already made
- relevant project and technical context

Avoid preserving:

- trivial chit-chat
- repeated pleasantries
- low-value turns

### Simple summarization rule

A simple rule is:

- if `messages` length exceeds a threshold, summarize the older part
- keep the last `N` turns untouched
- update `summary`
- optionally store the new summary in Qdrant

---

## LangMem-style summarization concepts

You asked to include LangMem ideas. The key useful ideas are:

1. **Do not lose the full transcript.**  
   Summaries are for model context efficiency, not for replacing durable conversation records.

2. **Keep separate stores for:**
   - full message history
   - running summary
   - extracted memory facts

3. **Summarize older content, not everything.**  
   Keep recent turns available verbatim for immediate coherence.

4. **Extract explicit long-term memory separately.**  
   Example:
   - “User prefers concise answers”
   - “User is working on EKS”
   - “User wants examples in FastMCP”

This is stronger than relying only on a single large summary.

### A practical memory split

- **messages**: exact recent thread turns
- **summary**: compressed history
- **memory facts**: reusable cross-thread semantic facts

---

## Orchestration node pattern

The orchestration node is where the LLM decides the next best action.

This node should not directly execute tools. It should produce a structured plan.

Typical plan fields:

- `intent`
- `needs_tool`
- `selected_tool`
- `tool_args`
- `follow_up_needed`
- `reasoning`

### Example orchestration prompt

```text
You are an orchestration agent for a support chatbot.

Available tools:
- get_user_orders
- create_refund_request
- search_knowledge_base
- get_account_profile

Rules:
- Use search_knowledge_base for policy and FAQ questions.
- Use tools only when they are clearly needed.
- If information is missing, set follow_up_needed=true.
- Never invent tool arguments.
- Return structured output only.
```

### Example structured plan

```json
{
  "intent": "order_status",
  "needs_tool": true,
  "selected_tool": "get_user_orders",
  "tool_args": {
    "user_id": "123"
  },
  "follow_up_needed": false,
  "reasoning": "The user asked for order status."
}
```

---

## MCP tool execution pattern

The clean separation is:

- orchestration node decides
- validation layer checks
- tool node executes
- response node explains result to user

This keeps:

- LLM responsible for planning
- LangGraph responsible for control flow
- MCP tools responsible for execution

---

## Reference project structure

```text
app/
  main.py
  api/
    chat.py
  graph/
    state.py
    graph.py
    nodes/
      orchestrate.py
      retrieve_memory.py
      summarize.py
      extract_memory.py
      execute_tool.py
      respond.py
  storage/
    redis_store.py
    postgres_store.py
    qdrant_store.py
  db/
    models.py
    session.py
  prompts/
    orchestration_prompt.py
    summary_prompt.py
    response_prompt.py
  tools/
    mcp_client.py
```

---

## Example code: combined implementation

This section gives a compact but realistic example.

### Example 1: Redis + Postgres combined state pattern

```python
from typing import TypedDict, List, Dict, Any, Optional
from redis import Redis
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, ForeignKey, JSON, func
)
from sqlalchemy.orm import declarative_base, sessionmaker
import json

redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)
REDIS_TTL_SECONDS = 3600

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/chatbot"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class ConversationThread(Base):
    __tablename__ = "conversation_threads"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, nullable=False, unique=True, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True)
    thread_id = Column(String, ForeignKey("conversation_threads.thread_id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"

    id = Column(Integer, primary_key=True)
    thread_id = Column(String, nullable=False, index=True)
    state_json = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Base.metadata.create_all(bind=engine)


class AgentState(TypedDict, total=False):
    tenant_id: str
    user_id: str
    thread_id: str
    messages: List[Dict[str, str]]
    summary: str
    retrieved_memories: List[Dict[str, Any]]
    plan: Dict[str, Any]
    tool_result: Dict[str, Any]
    final_answer: str
    version: int


def redis_key(thread_id: str) -> str:
    return f"langgraph:thread:{thread_id}"


def load_state_from_redis(thread_id: str) -> Optional[AgentState]:
    raw = redis_client.get(redis_key(thread_id))
    return json.loads(raw) if raw else None


def save_state_to_redis(thread_id: str, state: AgentState) -> None:
    redis_client.setex(redis_key(thread_id), REDIS_TTL_SECONDS, json.dumps(state))


def ensure_thread_exists(db, tenant_id: str, user_id: str, thread_id: str) -> None:
    thread = db.query(ConversationThread).filter_by(thread_id=thread_id).first()
    if not thread:
        thread = ConversationThread(
            tenant_id=tenant_id,
            user_id=user_id,
            thread_id=thread_id,
            title="Chat thread",
        )
        db.add(thread)
        db.commit()


def append_message_to_postgres(db, thread_id: str, role: str, content: str, metadata: Optional[dict] = None) -> None:
    db.add(
        ConversationMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
    )
    db.commit()


def save_checkpoint_to_postgres(db, thread_id: str, state: AgentState) -> None:
    db.add(
        WorkflowCheckpoint(
            thread_id=thread_id,
            state_json=state,
            version=int(state.get("version", 1)),
        )
    )
    db.commit()


def load_latest_checkpoint(db, thread_id: str) -> Optional[AgentState]:
    row = (
        db.query(WorkflowCheckpoint)
        .filter_by(thread_id=thread_id)
        .order_by(WorkflowCheckpoint.id.desc())
        .first()
    )
    return row.state_json if row else None


def load_recent_messages(db, thread_id: str, limit: int = 20) -> List[Dict[str, str]]:
    rows = (
        db.query(ConversationMessage)
        .filter_by(thread_id=thread_id)
        .order_by(ConversationMessage.id.asc())
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in rows][-limit:]


def build_state_from_postgres(db, tenant_id: str, user_id: str, thread_id: str) -> AgentState:
    checkpoint = load_latest_checkpoint(db, thread_id)
    if checkpoint:
        return checkpoint

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "messages": load_recent_messages(db, thread_id),
        "summary": "",
        "retrieved_memories": [],
        "version": 1,
    }
```

---

### Example 2: Qdrant semantic memory store

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
QDRANT_COLLECTION = "chat_memory"

embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
qdrant_client = QdrantClient(path="./qdrant_data")
vectorstore = QdrantVectorStore(
    client=qdrant_client,
    collection_name=QDRANT_COLLECTION,
    embedding=embeddings,
)

existing = [c.name for c in qdrant_client.get_collections().collections]
if QDRANT_COLLECTION not in existing:
    dim = len(embeddings.embed_query("hello"))
    qdrant_client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
    )


@dataclass
class AuthContext:
    tenant_id: str
    user_id: str


def build_memory_filter(
    auth: AuthContext,
    thread_id: Optional[str] = None,
    kind: Optional[str] = None,
) -> models.Filter:
    must = [
        models.FieldCondition(
            key="metadata.tenant_id",
            match=models.MatchValue(value=auth.tenant_id),
        ),
        models.FieldCondition(
            key="metadata.user_id",
            match=models.MatchValue(value=auth.user_id),
        ),
    ]

    if thread_id:
        must.append(
            models.FieldCondition(
                key="metadata.thread_id",
                match=models.MatchValue(value=thread_id),
            )
        )

    if kind:
        must.append(
            models.FieldCondition(
                key="metadata.kind",
                match=models.MatchValue(value=kind),
            )
        )

    return models.Filter(must=must)


def save_summary(auth: AuthContext, thread_id: str, summary_text: str) -> None:
    doc = Document(
        page_content=summary_text,
        metadata={
            "tenant_id": auth.tenant_id,
            "user_id": auth.user_id,
            "thread_id": thread_id,
            "kind": "summary",
        },
    )
    vectorstore.add_documents([doc])


def save_memory(auth: AuthContext, thread_id: str, memory_text: str) -> None:
    doc = Document(
        page_content=memory_text,
        metadata={
            "tenant_id": auth.tenant_id,
            "user_id": auth.user_id,
            "thread_id": thread_id,
            "kind": "memory",
        },
    )
    vectorstore.add_documents([doc])


def retrieve_memories(auth: AuthContext, query: str, k: int = 4) -> List[Dict[str, Any]]:
    flt = build_memory_filter(auth=auth)
    docs = vectorstore.similarity_search(query=query, k=k, filter=flt)
    return [{"text": d.page_content, "metadata": d.metadata} for d in docs]
```

---

### Example 3: Orchestration node

```python
from typing import TypedDict, Dict, Any, Optional
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class Plan(BaseModel):
    intent: str
    needs_tool: bool
    selected_tool: Optional[str] = None
    tool_args: Dict[str, Any] = {}
    follow_up_needed: bool
    reasoning: str


orchestration_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an orchestration agent for a support assistant.

Available tools:
- get_user_orders
- create_refund_request
- search_knowledge_base
- get_account_profile

Rules:
- Prefer search_knowledge_base for policy and FAQ questions.
- Use tools only when they are clearly needed.
- If required information is missing, set follow_up_needed=true.
- Never invent tool arguments.
- Return structured output only.
"""
    ),
    ("human", "{user_input}")
])


def orchestration_node(state: dict) -> dict:
    chain = orchestration_prompt | llm.with_structured_output(Plan)
    plan = chain.invoke({"user_input": state["messages"][-1]["content"]})
    return {"plan": plan.model_dump()}
```

---

### Example 4: Summarization node

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def summarize_if_needed_node(state: dict) -> dict:
    messages = state.get("messages", [])
    summary = state.get("summary", "")

    if len(messages) < 12:
        return {}

    older = messages[:-6]
    recent = messages[-6:]

    prompt = f'''
Update the running summary.

Existing summary:
{summary}

Older messages:
{older}

Preserve:
- user preferences
- goals
- important facts
- unresolved tasks
- decisions already made
'''

    new_summary = llm.invoke(prompt).content

    return {
        "summary": new_summary,
        "messages": recent,
    }
```

---

### Example 5: Memory extraction node

```python
def extract_memory_node(state: dict) -> dict:
    latest_user_msg = state["messages"][-1]["content"]

    prompt = f'''
Decide whether the following user message contains a durable memory worth storing
for future conversations.

User message:
{latest_user_msg}

Only return one concise memory sentence if useful.
If not useful, return exactly: NONE
'''

    memory = llm.invoke(prompt).content.strip()

    if memory != "NONE":
        # Save to Qdrant here
        pass

    return {}
```

---

### Example 6: MCP tool execution node

```python
import asyncio
from fastmcp import Client

MCP_SERVER_URL = "http://localhost:8000/mcp"

async def call_mcp_tool(tool_name: str, args: dict):
    client = Client(MCP_SERVER_URL)
    async with client:
        return await client.call_tool(tool_name, args)

def execute_tool_node(state: dict) -> dict:
    plan = state["plan"]
    result = asyncio.run(
        call_mcp_tool(plan["selected_tool"], plan["tool_args"])
    )
    return {"tool_result": result}
```

---

### Example 7: Response node

```python
def respond_node(state: dict) -> dict:
    summary = state.get("summary", "")
    memories = state.get("retrieved_memories", [])
    recent = state.get("messages", [])
    plan = state.get("plan", {})
    tool_result = state.get("tool_result", {})

    memory_text = "\n".join(f"- {m['text']}" for m in memories) or "(none)"

    prompt = f'''
You are a helpful assistant.

Running summary:
{summary or "(none)"}

Relevant long-term memory:
{memory_text}

Recent messages:
{recent}

Plan:
{plan}

Tool result:
{tool_result}

Write the next assistant response.
'''

    answer = llm.invoke(prompt).content

    return {
        "final_answer": answer,
        "messages": recent + [{"role": "assistant", "content": answer}],
    }
```

---

### Example 8: LangGraph wiring

```python
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict, total=False):
    tenant_id: str
    user_id: str
    thread_id: str
    messages: list[dict]
    summary: str
    retrieved_memories: list[dict]
    plan: dict
    tool_result: dict
    final_answer: str

def route_after_plan(state: AgentState) -> str:
    plan = state["plan"]

    if plan["follow_up_needed"]:
        return "follow_up"

    if plan["needs_tool"]:
        return "execute_tool"

    return "respond"

def follow_up_node(state: AgentState) -> dict:
    return {"final_answer": "I need a bit more information before I continue."}

builder = StateGraph(AgentState)

builder.add_node("retrieve_memory", lambda s: s)
builder.add_node("summarize_if_needed", summarize_if_needed_node)
builder.add_node("orchestrate", orchestration_node)
builder.add_node("execute_tool", execute_tool_node)
builder.add_node("respond", respond_node)
builder.add_node("follow_up", follow_up_node)

builder.add_edge(START, "retrieve_memory")
builder.add_edge("retrieve_memory", "summarize_if_needed")
builder.add_edge("summarize_if_needed", "orchestrate")

builder.add_conditional_edges(
    "orchestrate",
    route_after_plan,
    {
        "execute_tool": "execute_tool",
        "respond": "respond",
        "follow_up": "follow_up",
    },
)

builder.add_edge("execute_tool", "respond")
builder.add_edge("respond", END)
builder.add_edge("follow_up", END)

graph = builder.compile()
```

---

## Production considerations

### 1. Redis should not be your source of truth
Redis is for hot state, not the canonical durable record.

### 2. Postgres should keep exact chronology
Store exact messages and checkpoints there.

### 3. Qdrant should store semantic memory, not necessarily everything
Avoid embedding every trivial turn.

### 4. Keep memory extraction selective
Only save durable facts.

### 5. Always filter Qdrant by tenant and user
Never trust the client or LLM to supply tenant scope correctly.

### 6. Separate summary from transcript
The summary is prompt optimization, not your audit record.

### 7. Watch token growth
Even summaries can grow. Re-summarize summaries if needed.

### 8. Save cross-thread memory carefully
Examples worth saving:
- preferences
- recurring technical context
- durable goals

Not worth saving:
- temporary clarifications
- low-value pleasantries

### 9. Use background jobs if summarization becomes expensive
You can summarize inline for smaller systems, but larger systems may summarize asynchronously.

### 10. Keep orchestration output structured
Avoid free-text routing decisions.

---

## Common pitfalls

### Pitfall 1: putting full transcript in Redis forever
This bloats memory and slows down retrieval.

### Pitfall 2: using Qdrant as the only chat store
Vector DBs are not ideal as the canonical exact-history store.

### Pitfall 3: not filtering semantic memory by tenant/user
This creates data leakage risk.

### Pitfall 4: over-saving memories
If you embed everything, retrieval quality degrades.

### Pitfall 5: mixing planning and execution
Let the planner decide, then let LangGraph enforce and execute.

### Pitfall 6: trusting the LLM to enforce security
Always validate tools, inputs, tenant scope, and permissions in code.

---

## Interview-ready summary

A strong way to explain this architecture is:

> I split chatbot memory into three layers. Redis holds hot thread state for low-latency continuation, Postgres stores durable transcripts and checkpoints for recovery and auditing, and Qdrant stores semantic summaries or extracted long-term memories for retrieval across threads. In LangGraph, I use an orchestration node with a structured planning prompt, a summarization node to compress older turns, and a retrieval node that pulls relevant semantic memory from Qdrant before generating the final response. This keeps the system scalable, recoverable, and context-efficient.

---

## Final takeaway

Use:

- **Redis** for active thread state
- **Postgres** for durable exact history
- **Qdrant** for semantic memory across threads
- **LangGraph** for control flow
- **orchestration prompt** for planning
- **summaries + memory extraction** to manage context cleanly

That combination is one of the strongest practical patterns for production chatbots.
