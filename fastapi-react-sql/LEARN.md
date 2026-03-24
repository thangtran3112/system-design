# FastAPI + SQLite CRUD — Learning Guide

A hands-on, step-by-step guide to learn FastAPI with CRUD operations and SQLite.
**You type everything yourself** — copy from snippets, edit, and learn by doing.

---

## Phase 1: Environment Setup

Run these commands **one by one** in your terminal:

```bash
# 1. Create venv with a pinned Python version (isolated from system Python)
uv venv --python 3.12

# 2. Activate it
source .venv/bin/activate

# 3. Install dependencies
uv pip install fastapi uvicorn sqlalchemy pydantic pytest httpx

# 4. Create project structure
mkdir -p app tests
touch app/__init__.py app/main.py app/models.py app/database.py app/schemas.py app/crud.py
touch tests/__init__.py tests/conftest.py tests/test_main.py
```

> **Why `uv`?** It downloads + manages Python versions for you (no need for `pyenv` separately),
> creates the venv in `.venv/`, and installs packages ~10-50x faster than `pip`.
> If Python 3.12 isn't installed yet, `uv` will download it automatically.

Your folder should now look like:
```
fastapi-react-sql/
├── app/
│   ├── __init__.py
│   ├── crud.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_main.py
└── .venv/
```

---

## Phase 2: Database Setup (SQLAlchemy + SQLite)

### File: `app/database.py`

Type this into `app/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### What you just learned:
| Concept | What it does |
|---------|-------------|
| `create_engine` | Connects to SQLite file `app.db` |
| `check_same_thread=False` | Required — FastAPI uses multiple threads, SQLite doesn't allow that by default |
| `SessionLocal` | Factory that creates new database sessions |
| `Base` | Parent class for all your database models |
| `get_db()` | A **generator** that FastAPI injects into route handlers via dependency injection |

---

## Phase 3: Models & Schemas

### File: `app/models.py` — The database table

```python
from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, default="")
    completed = Column(Boolean, default=False)
```

### File: `app/schemas.py` — API request/response shapes

```python
from pydantic import BaseModel

class TodoCreate(BaseModel):
    title: str
    description: str = ""
    completed: bool = False

class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None

class TodoResponse(BaseModel):
    id: int
    title: str
    description: str
    completed: bool

    model_config = {"from_attributes": True}
```

### What you just learned:

**Model vs Schema — why two files?**

| | Model (`models.py`) | Schema (`schemas.py`) |
|---|---|---|
| Library | SQLAlchemy | Pydantic |
| Purpose | Defines the **database table** | Defines the **API request/response** shape |
| Used for | Reading/writing rows in SQLite | Validating JSON input & serializing output |

- `TodoCreate` — what the client sends when creating (no `id` needed, DB generates it)
- `TodoUpdate` — all fields optional (only update what's sent)
- `TodoResponse` — what the API returns (includes `id`)
- `from_attributes = True` — tells Pydantic to read SQLAlchemy model attributes directly

---

## Phase 4: CRUD Operations

### File: `app/crud.py` — The database logic

```python
from sqlalchemy.orm import Session
from app.models import Todo
from app.schemas import TodoCreate, TodoUpdate

def create_todo(db: Session, todo: TodoCreate) -> Todo:
    db_todo = Todo(**todo.model_dump())
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def get_todos(db: Session) -> list[Todo]:
    return db.query(Todo).all()

def get_todo(db: Session, todo_id: int) -> Todo | None:
    return db.query(Todo).filter(Todo.id == todo_id).first()

def update_todo(db: Session, todo_id: int, todo: TodoUpdate) -> Todo | None:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if db_todo is None:
        return None
    for key, value in todo.model_dump(exclude_unset=True).items():
        setattr(db_todo, key, value)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: int) -> bool:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if db_todo is None:
        return False
    db.delete(db_todo)
    db.commit()
    return True
```

### What you just learned:

| Pattern | What it does |
|---------|-------------|
| `todo.model_dump()` | Converts Pydantic schema → dict, e.g. `{"title": "Buy milk", "completed": False}` |
| `Todo(**dict)` | Unpacks dict into SQLAlchemy model constructor |
| `db.add() → db.commit()` | Stages then saves to database (like git add + commit) |
| `db.refresh(obj)` | Reloads from DB after commit — gets the auto-generated `id` |
| `exclude_unset=True` | Only includes fields the client actually sent — so partial updates work |
| `setattr(obj, key, value)` | Dynamically sets attributes: `obj.title = "new title"` |

---

## Phase 5: FastAPI Routes

### File: `app/main.py` — The API endpoints

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.models import Base
from app.schemas import TodoCreate, TodoUpdate, TodoResponse
from app import crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Todo API")

@app.post("/todos", response_model=TodoResponse, status_code=201)
def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    return crud.create_todo(db, todo)

@app.get("/todos", response_model=list[TodoResponse])
def read_todos(db: Session = Depends(get_db)):
    return crud.get_todos(db)

@app.get("/todos/{todo_id}", response_model=TodoResponse)
def read_todo(todo_id: int, db: Session = Depends(get_db)):
    todo = crud.get_todo(db, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@app.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, todo: TodoUpdate, db: Session = Depends(get_db)):
    updated = crud.update_todo(db, todo_id, todo)
    if updated is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return updated

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    if not crud.delete_todo(db, todo_id):
        raise HTTPException(status_code=404, detail="Todo not found")
```

### What you just learned:

| Concept | What it does |
|---------|-------------|
| `@app.post("/todos")` | Decorator that registers a route — maps HTTP method + path to a function |
| `Depends(get_db)` | **Dependency injection** — FastAPI calls `get_db()` and passes the session to your function |
| `response_model=TodoResponse` | Auto-serializes the return value & generates OpenAPI docs |
| `status_code=201` | Returns 201 Created instead of default 200 |
| `HTTPException(status_code=404)` | Returns a proper HTTP error response |
| `Base.metadata.create_all()` | Creates all tables in the database on app startup |
| `{todo_id}` in path | **Path parameter** — FastAPI extracts it and passes as function argument |

### How the request flows:
```
Client POST /todos {"title": "Learn"}
  → FastAPI validates JSON against TodoCreate schema
  → FastAPI calls get_db() → injects db session
  → create_todo() runs → calls crud.create_todo()
  → crud adds row to SQLite, returns Todo object
  → FastAPI serializes Todo → TodoResponse JSON
  → Client gets {"id": 1, "title": "Learn", ...}
```

---

## Phase 6: Tests

### File: `tests/conftest.py` — Test fixtures

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

# Use a separate test database — not your real app.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Provide a clean database session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    """
    FastAPI test client that uses our test database.
    Overrides the get_db dependency so the app talks to test.db, not app.db.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

### What you just learned about test fixtures:

| Fixture | Purpose |
|---------|---------|
| `setup_database` | `autouse=True` means it runs for **every** test automatically — creates tables before, drops after |
| `db` | Gives each test its own clean database session |
| `client` | A fake HTTP client that calls your FastAPI app directly (no real server needed) |
| `dependency_overrides` | The key trick — swaps the real `get_db` with one that uses `test.db` instead of `app.db` |

### File: `tests/test_main.py` — The actual tests

```python
"""
Tests for the Todo CRUD API.
Each test gets a fresh database (tables created/dropped per test via conftest.py).
"""


# ─── CREATE ───────────────────────────────────────────────────────────

def test_create_todo(client):
    """POST /todos should create a new todo and return it with an id."""
    response = client.post("/todos", json={
        "title": "Learn FastAPI",
        "description": "Build a CRUD app",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Learn FastAPI"
    assert data["description"] == "Build a CRUD app"
    assert data["completed"] is False  # default value
    assert "id" in data


def test_create_todo_minimal(client):
    """POST /todos with only required field (title) should work."""
    response = client.post("/todos", json={"title": "Minimal todo"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal todo"
    assert data["description"] == ""  # default


# ─── READ ALL ─────────────────────────────────────────────────────────

def test_read_todos_empty(client):
    """GET /todos on empty database should return empty list."""
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []


def test_read_todos(client):
    """GET /todos should return all created todos."""
    client.post("/todos", json={"title": "First"})
    client.post("/todos", json={"title": "Second"})

    response = client.get("/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "First"
    assert data[1]["title"] == "Second"


# ─── READ ONE ─────────────────────────────────────────────────────────

def test_read_todo(client):
    """GET /todos/{id} should return the specific todo."""
    create_resp = client.post("/todos", json={"title": "Find me"})
    todo_id = create_resp.json()["id"]

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Find me"


def test_read_todo_not_found(client):
    """GET /todos/{id} with non-existent id should return 404."""
    response = client.get("/todos/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"


# ─── UPDATE ───────────────────────────────────────────────────────────

def test_update_todo(client):
    """PUT /todos/{id} should update specified fields only."""
    create_resp = client.post("/todos", json={
        "title": "Original",
        "description": "Old description",
    })
    todo_id = create_resp.json()["id"]

    response = client.put(f"/todos/{todo_id}", json={
        "title": "Updated",
        "completed": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["completed"] is True
    assert data["description"] == "Old description"  # unchanged


def test_update_todo_not_found(client):
    """PUT /todos/{id} with non-existent id should return 404."""
    response = client.put("/todos/999", json={"title": "Nope"})
    assert response.status_code == 404


# ─── DELETE ───────────────────────────────────────────────────────────

def test_delete_todo(client):
    """DELETE /todos/{id} should remove the todo and return 204."""
    create_resp = client.post("/todos", json={"title": "Delete me"})
    todo_id = create_resp.json()["id"]

    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = client.get(f"/todos/{todo_id}")
    assert get_resp.status_code == 404


def test_delete_todo_not_found(client):
    """DELETE /todos/{id} with non-existent id should return 404."""
    response = client.delete("/todos/999")
    assert response.status_code == 404
```

---

## Phase 7: Run & Verify

```bash
# Run all tests (should see 10 passed)
pytest -v

# Start the live server
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** — FastAPI auto-generates interactive Swagger UI where you can test every endpoint from the browser.

---

## Quick Reference: HTTP Methods → CRUD

| HTTP Method | CRUD | Route | What it does |
|-------------|------|-------|-------------|
| `POST` | **C**reate | `/todos` | Create a new todo |
| `GET` | **R**ead | `/todos` | List all todos |
| `GET` | **R**ead | `/todos/{id}` | Get one todo |
| `PUT` | **U**pdate | `/todos/{id}` | Update a todo |
| `DELETE` | **D**elete | `/todos/{id}` | Delete a todo |

---
---

# Part 2: Advanced FastAPI Concepts

Now that you have a working CRUD app, let's level up.

---

## Phase 8: `async def` vs `def` — How FastAPI Handles Concurrency

### The big picture

FastAPI runs on **uvicorn**, which uses an **async event loop** (like Node.js). Here's how it handles your route functions:

```
┌─────────────────────────────────────────────────┐
│              uvicorn (async event loop)          │
│                                                  │
│  async def route() ← runs directly on the loop  │
│        def route() ← runs in a thread pool       │
│                                                  │
└─────────────────────────────────────────────────┘
```

| You write | FastAPI does | Good for |
|-----------|-------------|----------|
| `def endpoint()` | Runs it in a **thread pool** (won't block the loop) | Blocking I/O: SQLAlchemy, file reads, `requests` library |
| `async def endpoint()` | Runs it **directly on the event loop** | Non-blocking I/O: `httpx.AsyncClient`, `aiofiles`, async DB drivers |

### Rule of thumb
- If you call **anything that blocks** (SQLAlchemy `db.query()`, `time.sleep()`, `open()`), use `def`
- If you call **only async things** (`await`), use `async def`
- If you use `async def` but call blocking code inside → **you freeze the entire server**

### File: `app/main.py` — Add these new endpoints to see the difference

```python
import time
import asyncio

# BAD — blocks the event loop for 3 seconds. ALL other requests wait.
@app.get("/slow-bad")
async def slow_bad():
    time.sleep(3)  # ← blocking call inside async = disaster
    return {"message": "This blocked everything"}

# GOOD — runs in thread pool, other requests keep flowing
@app.get("/slow-sync")
def slow_sync():
    time.sleep(3)  # ← blocking, but FastAPI auto-runs this in a thread
    return {"message": "This didn't block other requests"}

# GOOD — async sleep yields control, other requests keep flowing
@app.get("/slow-async")
async def slow_async():
    await asyncio.sleep(3)  # ← non-blocking
    return {"message": "This didn't block other requests either"}
```

### Try it yourself — the concurrency test

Open **3 terminal tabs** and run these at the same time:

```bash
# Tab 1: start server
uvicorn app.main:app --reload

# Tab 2: hit the endpoint
time curl http://127.0.0.1:8000/slow-sync

# Tab 3: hit a fast endpoint AT THE SAME TIME as tab 2
time curl http://127.0.0.1:8000/todos
```

With `/slow-sync` (def): Tab 3 returns instantly — the slow request runs in a thread.
Now try `/slow-bad` (async def + time.sleep): Tab 3 **also waits 3 seconds** — the event loop is frozen.

### What you just learned:

| Concept | Detail |
|---------|--------|
| Event loop | Single thread that handles all async work — if you block it, everything stops |
| Thread pool | FastAPI automatically runs `def` routes here (default pool size: 40 threads) |
| `await` | Yields control back to the event loop so other requests can be served |
| Golden rule | Never put blocking code inside `async def` |

---

## Phase 9: Background Tasks

Sometimes you need to do work **after** returning a response — sending emails, writing logs, processing uploads.

### File: `app/main.py` — Add background task endpoint

```python
from fastapi import BackgroundTasks
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_notification(todo_title: str):
    """Simulate sending a notification (runs after response is sent)."""
    time.sleep(2)  # simulate slow email/webhook
    logger.info(f"Notification sent for: {todo_title}")

@app.post("/todos-notify", response_model=TodoResponse, status_code=201)
def create_todo_with_notification(
    todo: TodoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    new_todo = crud.create_todo(db, todo)
    # This runs AFTER the response is sent — client doesn't wait
    background_tasks.add_task(send_notification, new_todo.title)
    return new_todo
```

### Try it yourself

```bash
# POST returns immediately, but check your server logs 2 seconds later
curl -X POST http://127.0.0.1:8000/todos-notify \
  -H "Content-Type: application/json" \
  -d '{"title": "Test notification"}'
```

You'll see the response instantly, then `Notification sent for: Test notification` in the server logs 2 seconds later.

### What you just learned:

| Concept | Detail |
|---------|--------|
| `BackgroundTasks` | FastAPI dependency — inject it like `get_db` |
| `add_task(fn, *args)` | Queues a function to run after the response is sent |
| Use `def` not `async def` | Background functions with blocking I/O should be regular `def` |
| Not a job queue | For heavy work, use Celery/Redis. `BackgroundTasks` is for lightweight fire-and-forget |

---

## Phase 10: Middleware & Request Lifecycle

Middleware wraps **every** request — useful for logging, timing, CORS, auth checks.

### File: `app/main.py` — Add timing middleware

```python
from fastapi.middleware.cors import CORSMiddleware

# CORS — allow your React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware — logs how long each request takes
@app.middleware("http")
async def add_timing_header(request, call_next):
    import time as _time
    start = _time.perf_counter()
    response = await call_next(request)
    duration_ms = (_time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)")
    return response
```

### Try it yourself

```bash
# Check the response headers — you'll see X-Process-Time-Ms
curl -v http://127.0.0.1:8000/todos 2>&1 | grep X-Process
```

### How the request lifecycle flows:

```
Client request
  → Middleware 1 (CORS)
    → Middleware 2 (timing)
      → Dependency injection (get_db)
        → Route handler (create_todo)
      → Dependency cleanup (db.close)
    → Middleware 2 adds timing header
  → Middleware 1 adds CORS headers
Client response
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| Middleware | Wraps every request/response — runs before AND after your route |
| `call_next(request)` | Passes request to the next middleware or route handler |
| CORS middleware | Required when your frontend (React) is on a different port/domain |
| Execution order | Middleware → Dependencies → Route → Dependencies cleanup → Middleware |

---

## Phase 11: Async Database with `aiosqlite`

Your current setup uses synchronous SQLAlchemy — every `db.query()` blocks a thread. For high concurrency, you can go fully async.

### Install

```bash
uv pip install aiosqlite
```

### File: `app/database_async.py` — Async database setup

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./app.db"

async_engine = create_async_engine(
    ASYNC_DATABASE_URL, connect_args={"check_same_thread": False}
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### File: `app/crud_async.py` — Async CRUD

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Todo
from app.schemas import TodoCreate

async def create_todo(db: AsyncSession, todo: TodoCreate) -> Todo:
    db_todo = Todo(**todo.model_dump())
    db.add(db_todo)
    await db.commit()
    await db.refresh(db_todo)
    return db_todo

async def get_todos(db: AsyncSession) -> list[Todo]:
    result = await db.execute(select(Todo))
    return list(result.scalars().all())

async def get_todo(db: AsyncSession, todo_id: int) -> Todo | None:
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    return result.scalar_one_or_none()
```

### File: `app/main.py` — Async route example

```python
from app.database_async import get_async_db
from app import crud_async
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/async/todos", response_model=list[TodoResponse])
async def read_todos_async(db: AsyncSession = Depends(get_async_db)):
    return await crud_async.get_todos(db)
```

### Sync vs Async comparison:

| | Sync (current) | Async (new) |
|---|---|---|
| Engine | `create_engine` | `create_async_engine` |
| Session | `Session` | `AsyncSession` |
| Query | `db.query(Todo).all()` | `await db.execute(select(Todo))` |
| Route | `def` | `async def` |
| DB driver | `sqlite3` (built-in) | `aiosqlite` (installed separately) |
| When to use | Simple apps, low traffic | High concurrency, many simultaneous users |

### What you just learned:

| Concept | Detail |
|---------|--------|
| `select(Todo)` | SQLAlchemy 2.0 style query — works for both sync and async |
| `result.scalars().all()` | Extracts model objects from the raw result |
| `expire_on_commit=False` | Prevents lazy-load errors after commit in async context |
| `async with` session | Auto-closes session when done — cleaner than try/finally |

---

## Phase 12: Concurrent External API Calls

Real apps often call multiple external services. With `async`, you can call them **in parallel**.

### Install

```bash
uv pip install httpx
```

### File: `app/main.py` — Parallel vs sequential external calls

```python
import httpx

# SLOW — sequential: 2 API calls × ~200ms each = ~400ms total
@app.get("/external/sequential")
async def fetch_sequential():
    async with httpx.AsyncClient() as client:
        resp1 = await client.get("https://httpbin.org/delay/1")
        resp2 = await client.get("https://httpbin.org/delay/1")
    return {"total_calls": 2, "note": "took ~2 seconds (sequential)"}

# FAST — parallel: 2 API calls at once = ~200ms total
@app.get("/external/parallel")
async def fetch_parallel():
    async with httpx.AsyncClient() as client:
        resp1, resp2 = await asyncio.gather(
            client.get("https://httpbin.org/delay/1"),
            client.get("https://httpbin.org/delay/1"),
        )
    return {"total_calls": 2, "note": "took ~1 second (parallel)"}
```

### Try it yourself

```bash
# Compare the two — notice the time difference
time curl http://127.0.0.1:8000/external/sequential
time curl http://127.0.0.1:8000/external/parallel
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| `httpx.AsyncClient` | Async HTTP client (replaces `requests` in async code) |
| `asyncio.gather()` | Runs multiple coroutines **concurrently** — returns when ALL complete |
| Why async matters | 10 parallel API calls take the same time as 1 — huge performance win |

---

## Cheat Sheet: When to Use What

```
Is my code blocking? (db.query, time.sleep, open(), requests.get)
  ├─ YES → use `def` (FastAPI auto-threads it)
  └─ NO  → use `async def` + `await`

Do I need work done after the response?
  ├─ Lightweight → BackgroundTasks
  └─ Heavy/reliable → Celery + Redis (separate topic)

Am I calling multiple external APIs?
  ├─ YES → asyncio.gather() for parallel calls
  └─ NO  → simple await is fine

Do I need to run code on every request?
  └─ YES → Middleware
```

---

## Phase 13: Rate Limiting & Throttling

Protect your API from abuse. No external library needed — use a simple in-memory approach first, then understand production options.

### File: `app/rate_limit.py`

```python
import time
from collections import defaultdict
from fastapi import HTTPException, Request

# Simple sliding window rate limiter
class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check(self, client_ip: str):
        now = time.time()
        # Remove expired timestamps
        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if now - t < self.window_seconds
        ]
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Try again later.",
            )
        self.requests[client_ip].append(now)

limiter = RateLimiter(max_requests=5, window_seconds=10)
```

### File: `app/main.py` — Use it as a dependency

```python
from app.rate_limit import limiter

async def rate_limit_dep(request: Request):
    limiter.check(request.client.host)

# Apply to a single route
@app.get("/todos", dependencies=[Depends(rate_limit_dep)])
async def read_todos(db: Session = Depends(get_db)):
    ...

# OR apply to the whole app
# app = FastAPI(dependencies=[Depends(rate_limit_dep)])
```

### Try it yourself

```bash
# Hit it 6 times fast — the 6th should return 429
for i in $(seq 1 6); do
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/todos
done
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| Sliding window | Track timestamps, remove expired ones, count remaining |
| `dependencies=[Depends()]` | Apply a dependency to a route without injecting a return value |
| 429 status code | Standard HTTP code for "Too Many Requests" |
| In-memory limitation | This resets on restart and doesn't work across multiple workers — production uses Redis |

> **Production approach:** Use `slowapi` or Redis-backed rate limiting (token bucket / sliding window in Redis) when running multiple Uvicorn workers.

---

## Phase 14: Dependency Injection Deep Dive

FastAPI's `Depends()` is its most powerful feature. You've used it for `get_db` — now learn the full pattern.

### File: `app/dependencies.py`

```python
from fastapi import Depends, Header, HTTPException, Query

# 1. Simple dependency — returns a value
async def common_parameters(skip: int = 0, limit: int = Query(default=100, le=1000)):
    return {"skip": skip, "limit": limit}

# 2. Dependency that raises — acts as a guard
async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != "secret-key-123":
        raise HTTPException(status_code=403, detail="Invalid API key")

# 3. Dependency with sub-dependencies (chaining)
async def get_current_user(x_api_key: str = Header()):
    # In real apps: decode JWT, look up user in DB
    if x_api_key == "admin-key":
        return {"user": "admin", "role": "admin"}
    elif x_api_key == "user-key":
        return {"user": "viewer", "role": "viewer"}
    raise HTTPException(status_code=401, detail="Unknown key")

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user
```

### File: `app/main.py` — Using dependencies

```python
from app.dependencies import common_parameters, verify_api_key, require_admin

# Pagination via shared dependency
@app.get("/todos")
async def read_todos(
    commons: dict = Depends(common_parameters),
    db: Session = Depends(get_db),
):
    return db.query(Todo).offset(commons["skip"]).limit(commons["limit"]).all()

# Guard — no return value needed, just blocks if invalid
@app.delete("/todos/{todo_id}", dependencies=[Depends(verify_api_key)])
async def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    ...

# Chained — require_admin calls get_current_user automatically
@app.post("/admin/reset", dependencies=[Depends(require_admin)])
async def admin_reset():
    return {"message": "Admin action performed"}
```

### Try it yourself

```bash
# Without API key — 422 (missing header)
curl http://127.0.0.1:8000/admin/reset -X POST

# Wrong key — 403
curl -H "x-api-key: wrong" http://127.0.0.1:8000/admin/reset -X POST

# User key — 403 (not admin)
curl -H "x-api-key: user-key" http://127.0.0.1:8000/admin/reset -X POST

# Admin key — 200
curl -H "x-api-key: admin-key" http://127.0.0.1:8000/admin/reset -X POST
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| `Depends()` return value | Injected into the route parameter |
| `dependencies=[Depends()]` | Run the dependency but discard return value (guards) |
| Sub-dependencies | Dependencies can depend on other dependencies — FastAPI resolves the chain |
| `Header()` | Extract values from HTTP headers |
| `Query(le=1000)` | Validation on query parameters |

---

## Phase 15: Caching Responses

Avoid redundant work — cache expensive queries. Start simple, then understand the production path.

### File: `app/cache.py`

```python
import time
from functools import wraps

# Simple in-memory TTL cache
_cache: dict[str, tuple[float, any]] = {}

def cached(ttl_seconds: int = 30):
    """Decorator that caches a function's return value by its arguments."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build a cache key from function name + args
            key = f"{func.__name__}:{args}:{kwargs}"
            now = time.time()

            if key in _cache:
                expires_at, value = _cache[key]
                if now < expires_at:
                    return value  # Cache HIT

            # Cache MISS — call the actual function
            result = await func(*args, **kwargs)
            _cache[key] = (now + ttl_seconds, result)
            return result
        return wrapper
    return decorator

def invalidate_cache(prefix: str = ""):
    """Clear cache entries matching a prefix (or all if empty)."""
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for k in keys_to_delete:
        del _cache[k]
```

### File: `app/main.py` — Cache the list endpoint

```python
from app.cache import cached, invalidate_cache

@cached(ttl_seconds=10)
async def _get_all_todos(skip: int, limit: int):
    """Cached query — separated so the decorator works cleanly."""
    db = SessionLocal()
    try:
        return db.query(Todo).offset(skip).limit(limit).all()
    finally:
        db.close()

@app.get("/todos")
async def read_todos(skip: int = 0, limit: int = 100):
    return await _get_all_todos(skip, limit)

# Invalidate on writes
@app.post("/todos", status_code=201)
async def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    result = crud.create_todo(db, todo)
    invalidate_cache("_get_all_todos")  # bust the cache
    return result
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| TTL cache | Store result + expiry timestamp, return cached if not expired |
| Cache key | Built from function name + arguments — same args = same cache |
| Cache invalidation | Clear on writes so stale data isn't served |
| Why in-memory is limited | Resets on restart, not shared across workers — production uses Redis |

> **Production approach:** Use `redis` with `aioredis` for distributed caching, or HTTP-level caching with `Cache-Control` headers + CDN.

---

## Phase 16: Streaming Responses & Server-Sent Events (SSE)

For long-running operations, stream results back instead of making the client wait.

### File: `app/main.py` — Streaming

```python
from fastapi.responses import StreamingResponse
import asyncio, json

# Stream large data instead of loading all into memory
@app.get("/todos/export")
async def export_todos(db: Session = Depends(get_db)):
    def generate():
        todos = db.query(Todo).all()
        yield "["
        for i, todo in enumerate(todos):
            if i > 0:
                yield ","
            yield json.dumps({
                "id": todo.id,
                "title": todo.title,
                "completed": todo.completed,
            })
        yield "]"

    return StreamingResponse(generate(), media_type="application/json")

# Server-Sent Events — push updates to the client
@app.get("/todos/stream")
async def stream_todos():
    async def event_generator():
        while True:
            # In production: listen to a message queue or DB change stream
            yield f"data: {json.dumps({'time': time.time(), 'message': 'heartbeat'})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Try it yourself

```bash
# Streaming export
curl http://127.0.0.1:8000/todos/export

# SSE — watch events arrive every 2 seconds (Ctrl+C to stop)
curl http://127.0.0.1:8000/todos/stream
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| `StreamingResponse` | Send data in chunks — client receives data as it's generated |
| Generator function | `yield` produces chunks one at a time, doesn't load everything into memory |
| SSE format | `data: {...}\n\n` — the browser's `EventSource` API reads this natively |
| When to stream | Large exports, real-time updates, progress indicators |

---

## Phase 17: Running with Multiple Workers & `lifespan`

In production, Uvicorn runs multiple worker processes. This changes how startup/shutdown and shared state work.

### File: `app/main.py` — Lifespan events

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP — runs once per worker process
    print("Starting up... creating tables")
    Base.metadata.create_all(bind=engine)
    yield
    # SHUTDOWN — runs when worker stops
    print("Shutting down... cleanup")

app = FastAPI(lifespan=lifespan)
```

### Running with workers

```bash
# Single worker (development) — what you've been using
uvicorn app.main:app --reload

# Multiple workers (production simulation)
uvicorn app.main:app --workers 4

# What happens with multiple workers:
# - Each worker is a separate process with its own memory
# - In-memory rate limiting / caching is PER WORKER (not shared!)
# - Database connections are per-worker
# - lifespan runs once per worker
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| `lifespan` | Replaces deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` |
| `@asynccontextmanager` | Code before `yield` = startup, after `yield` = shutdown |
| `--workers 4` | Runs 4 separate processes — each with its own memory space |
| Why Redis matters | In-memory state (cache, rate limits) isn't shared across workers |

---

## Phase 18: Concurrency Patterns — `asyncio.Semaphore` & Timeouts

Control how many concurrent operations run and set time limits.

### File: `app/main.py` — Bounded concurrency

```python
import asyncio
import httpx

# Limit concurrent external API calls (don't overwhelm downstream services)
SEMAPHORE = asyncio.Semaphore(3)  # max 3 concurrent requests

async def fetch_with_limit(client: httpx.AsyncClient, url: str):
    async with SEMAPHORE:  # blocks if 3 are already running
        response = await client.get(url)
        return response.json()

@app.get("/external/bounded")
async def fetch_bounded():
    urls = [f"https://httpbin.org/delay/1" for _ in range(10)]
    async with httpx.AsyncClient() as client:
        # 10 requests, but only 3 at a time
        results = await asyncio.gather(
            *[fetch_with_limit(client, url) for url in urls]
        )
    return {"fetched": len(results)}
```

### Timeouts — don't wait forever

```python
@app.get("/external/with-timeout")
async def fetch_with_timeout():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Also works at the asyncio level:
            result = await asyncio.wait_for(
                client.get("https://httpbin.org/delay/10"),
                timeout=2.0,
            )
            return result.json()
    except (httpx.TimeoutException, asyncio.TimeoutError):
        raise HTTPException(status_code=504, detail="Upstream service timed out")
```

### `asyncio.gather` — error handling

```python
@app.get("/external/safe")
async def fetch_safe():
    async with httpx.AsyncClient(timeout=3.0) as client:
        results = await asyncio.gather(
            client.get("https://httpbin.org/status/200"),
            client.get("https://httpbin.org/status/500"),
            client.get("https://httpbin.org/delay/10"),
            return_exceptions=True,  # don't crash on failure, return the exception
        )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [str(r) for r in results if isinstance(r, Exception)]
    return {"ok": len(successes), "failed": len(failures), "errors": failures}
```

### What you just learned:

| Concept | Detail |
|---------|--------|
| `asyncio.Semaphore(n)` | Limits concurrency — at most `n` coroutines run the guarded block simultaneously |
| `async with SEMAPHORE` | Acquires a slot, releases it when the block exits |
| `asyncio.wait_for(coro, timeout)` | Raises `TimeoutError` if the coroutine doesn't finish in time |
| `httpx.AsyncClient(timeout=)` | Client-level timeout — applies to all requests from this client |
| `return_exceptions=True` | `gather` returns exceptions as values instead of raising — lets you handle partial failures |

---

## Updated Cheat Sheet: Concurrency & Optimization

```
Rate limiting?
  ├─ Dev / single worker → in-memory sliding window
  └─ Prod / multi-worker → Redis + slowapi

Caching?
  ├─ Dev / single worker → in-memory dict with TTL
  ├─ Prod / multi-worker → Redis (aioredis)
  └─ Static / public data → Cache-Control headers + CDN

Dependencies?
  ├─ Need the return value → param: Type = Depends(func)
  ├─ Just a guard (auth) → dependencies=[Depends(func)]
  └─ Shared across routes → app = FastAPI(dependencies=[...])

Concurrent external calls?
  ├─ Few calls → asyncio.gather()
  ├─ Many calls → asyncio.Semaphore + gather
  └─ Must not hang → asyncio.wait_for() or httpx timeout

Streaming?
  ├─ Large response → StreamingResponse + generator
  └─ Real-time push → SSE (text/event-stream)

Production deployment?
  ├─ Multiple workers → uvicorn --workers N
  ├─ Startup/shutdown → lifespan context manager
  └─ In-memory state → moves to Redis (not shared across workers)
```

---
---

# Part 3: React Fundamentals — Todo Frontend

Build a React frontend for the Todo API. No external UI libraries — just React + native HTML elements.

---

## Phase 8: React Project Setup

```bash
cd /Users/ttran/personal/system-design/fastapi-react-sql
npx create-react-app frontend
cd frontend
npm start
```

Then clean up the boilerplate. Replace `src/App.js` with:

```jsx
function App() {
  return (
    <div>
      <h1>Todo App</h1>
      <p>React is working!</p>
    </div>
  );
}

export default App;
```

Clear out `src/App.css` (delete all contents, keep the file).

---

## Phase 9: Component Basics & JSX

**Concepts:** functional components, props, rendering lists with `key`

### Create `src/components/TodoItem.jsx`

```jsx
function TodoItem({ id, title, description, completed, onDelete }) {
  return (
    <li>
      <span style={{ textDecoration: completed ? "line-through" : "none" }}>
        <strong>{title}</strong>
        {description && <> — {description}</>}
      </span>
      <button type="button" onClick={() => onDelete(id)}>Delete</button>
    </li>
  );
}

export default TodoItem;
```

### Create `src/components/TodoList.jsx`

```jsx
import TodoItem from "./TodoItem";

function TodoList({ todos, onDelete }) {
  if (todos.length === 0) {
    return <p>No todos yet. Add one above!</p>;
  }

  return (
    <ul>
      {todos.map((todo) => (
        <TodoItem
          key={todo.id}
          id={todo.id}
          title={todo.title}
          description={todo.description}
          completed={todo.completed}
          onDelete={onDelete}
        />
      ))}
    </ul>
  );
}

export default TodoList;
```

### Update `src/App.js` — use hardcoded data for now

```jsx
import TodoList from "./components/TodoList";

const FAKE_TODOS = [
  { id: 1, title: "Learn React", description: "Components and JSX", completed: false },
  { id: 2, title: "Learn FastAPI", description: "Already done!", completed: true },
];

function App() {
  const handleDelete = (id) => {
    console.log("Delete todo:", id);
  };

  return (
    <div>
      <h1>Todo App</h1>
      <TodoList todos={FAKE_TODOS} onDelete={handleDelete} />
    </div>
  );
}

export default App;
```

### What you just learned

| Concept | Example |
|---------|---------|
| Functional component | `function TodoItem({ title }) { return <li>{title}</li> }` |
| Props destructuring | `{ id, title, completed }` in the function signature |
| `key` prop | `key={todo.id}` — React uses this to track which items changed |
| `.map()` for lists | `todos.map(todo => <TodoItem ... />)` |
| Conditional rendering | `{description && <> — {description}</>}` |
| Fragment shorthand | `<>...</>` — wraps multiple elements without adding a DOM node |
| Callback prop | `onDelete={handleDelete}` — parent passes function, child calls it |

---

## Phase 10: State & Events — `useState`

**Concepts:** useState, controlled components, form submission

### Create `src/components/TodoForm.jsx`

```jsx
import { useState } from "react";

function TodoForm({ onAdd }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!title.trim()) return;

    onAdd({ title: title.trim(), description: description.trim() });
    setTitle("");
    setDescription("");
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="title">Title</label>
        <input
          id="title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What needs to be done?"
        />
      </div>

      <div>
        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional details..."
          rows={3}
        />
      </div>

      <button type="submit">Add Todo</button>
    </form>
  );
}

export default TodoForm;
```

### Update `src/App.js` — add form with local state

```jsx
import { useState } from "react";
import TodoList from "./components/TodoList";
import TodoForm from "./components/TodoForm";

function App() {
  const [todos, setTodos] = useState([]);

  const handleAdd = (newTodo) => {
    const todo = { ...newTodo, id: Date.now(), completed: false };
    setTodos([...todos, todo]);
  };

  const handleDelete = (id) => {
    setTodos(todos.filter((todo) => todo.id !== id));
  };

  return (
    <div>
      <h1>Todo App</h1>
      <TodoForm onAdd={handleAdd} />
      <TodoList todos={todos} onDelete={handleDelete} />
    </div>
  );
}

export default App;
```

### What you just learned

| Concept | Detail |
|---------|--------|
| `useState("")` | Declares state variable + setter. Re-renders component when set. |
| Controlled component | `<input value={title} onChange={...} />` — React owns the value, not the DOM |
| `e.preventDefault()` | Stops the browser from reloading the page on form submit |
| `htmlFor` | JSX version of HTML's `for` attribute (links label to input) |
| `<textarea>` in React | Uses `value` prop, not children like in HTML |
| Immutable update | `[...todos, newTodo]` — create new array, never mutate state directly |
| `filter` for delete | `todos.filter(t => t.id !== id)` — returns new array without the deleted item |

### HTML elements reviewed

| Element | Key attributes |
|---------|---------------|
| `<form>` | `onSubmit` |
| `<input type="text">` | `value`, `onChange`, `placeholder`, `id` |
| `<textarea>` | `value`, `onChange`, `rows`, `placeholder` |
| `<label>` | `htmlFor` — matches input's `id` for accessibility |
| `<button type="submit">` | Inside a `<form>`, triggers `onSubmit` |
| `<button type="button">` | Does NOT trigger form submit — use for non-form actions |

---

## Phase 11: Side Effects — `useEffect` & API Calls

**Concepts:** useEffect, fetch, loading/error states, dependency array

### Update `src/App.js` — wire up to real backend

```jsx
import { useState, useEffect } from "react";
import TodoList from "./components/TodoList";
import TodoForm from "./components/TodoForm";

const API = "http://127.0.0.1:8000";

function App() {
  const [todos, setTodos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch todos on mount
  useEffect(() => {
    async function fetchTodos() {
      try {
        const res = await fetch(`${API}/todos`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setTodos(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchTodos();
  }, []); // ← empty array = run once on mount

  const handleAdd = async (newTodo) => {
    try {
      const res = await fetch(`${API}/todos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newTodo),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const created = await res.json();
      setTodos([...todos, created]);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`${API}/todos/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setTodos(todos.filter((t) => t.id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;

  return (
    <div>
      <h1>Todo App</h1>
      <TodoForm onAdd={handleAdd} />
      <TodoList todos={todos} onDelete={handleDelete} />
    </div>
  );
}

export default App;
```

### What you just learned

| Concept | Detail |
|---------|--------|
| `useEffect(fn, [])` | Empty deps = run once after first render (like componentDidMount) |
| `useEffect(fn, [x])` | Runs when `x` changes |
| `useEffect(fn)` | No deps = runs after EVERY render (usually a bug) |
| Why async inside | `useEffect` callback can't be async itself — define async function inside and call it |
| Loading pattern | `isLoading` starts true, set false in `finally` |
| Error pattern | `try/catch` around fetch, store error in state |
| `res.ok` | `fetch` doesn't throw on 404/500 — you must check `res.ok` yourself |
| `Content-Type` header | Required for POST/PUT so the server knows you're sending JSON |

### useEffect dependency array cheat sheet

```
useEffect(() => { ... }, [])      // Mount only — fetch initial data
useEffect(() => { ... }, [id])    // When id changes — fetch single item
useEffect(() => { ... })          // Every render — usually wrong
useEffect(() => {
  return () => { ... }            // Cleanup — runs before next effect or unmount
}, [])
```

---

## Phase 12: Editing & More Form Elements

**Concepts:** inline editing, toggling state, `<select>`, `<checkbox>`, more input types

### Update `src/components/TodoItem.jsx` — add edit mode

```jsx
import { useState } from "react";

function TodoItem({ id, title, description, completed, onUpdate, onDelete }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(title);
  const [editDescription, setEditDescription] = useState(description);
  const [editCompleted, setEditCompleted] = useState(completed);

  const handleSave = () => {
    onUpdate(id, {
      title: editTitle,
      description: editDescription,
      completed: editCompleted,
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditTitle(title);
    setEditDescription(description);
    setEditCompleted(completed);
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <li>
        <div>
          <label htmlFor={`title-${id}`}>Title</label>
          <input
            id={`title-${id}`}
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor={`desc-${id}`}>Description</label>
          <textarea
            id={`desc-${id}`}
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor={`status-${id}`}>Status</label>
          <select
            id={`status-${id}`}
            value={editCompleted ? "completed" : "active"}
            onChange={(e) => setEditCompleted(e.target.value === "completed")}
          >
            <option value="active">Active</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        <div>
          <label>
            <input
              type="checkbox"
              checked={editCompleted}
              onChange={(e) => setEditCompleted(e.target.checked)}
            />
            Mark completed
          </label>
        </div>

        <button type="button" onClick={handleSave}>Save</button>
        <button type="button" onClick={handleCancel}>Cancel</button>
      </li>
    );
  }

  return (
    <li>
      <span style={{ textDecoration: completed ? "line-through" : "none" }}>
        <strong>{title}</strong>
        {description && <> — {description}</>}
        {completed ? " ✓" : ""}
      </span>
      <button type="button" onClick={() => setIsEditing(true)}>Edit</button>
      <button type="button" onClick={() => onDelete(id)}>Delete</button>
    </li>
  );
}

export default TodoItem;
```

### Update `src/App.js` — add handleUpdate

Add this function in App alongside handleAdd and handleDelete:

```jsx
const handleUpdate = async (id, updates) => {
  try {
    const res = await fetch(`${API}/todos/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const updated = await res.json();
    setTodos(todos.map((t) => (t.id === id ? updated : t)));
  } catch (err) {
    setError(err.message);
  }
};
```

And pass it down:

```jsx
<TodoList todos={todos} onUpdate={handleUpdate} onDelete={handleDelete} />
```

Update TodoList to pass `onUpdate` through to each TodoItem.

### What you just learned

| Concept | Detail |
|---------|--------|
| Boolean state toggle | `isEditing` flips between view and edit mode |
| `<select>` + `<option>` | Dropdown — `value` on select, not `selected` on option (React way) |
| `<input type="checkbox">` | Uses `checked` not `value`, and `e.target.checked` not `e.target.value` |
| Cancel = reset state | Copy original props back into edit state variables |
| `map` for update | `todos.map(t => t.id === id ? updated : t)` — replace one item in array |

### HTML elements reviewed

| Element | React gotcha |
|---------|-------------|
| `<select value={x}>` | Controlled via `value` on `<select>`, not `selected` on `<option>` |
| `<option value="x">` | Value is what JS sees, text content is what user sees |
| `<input type="checkbox">` | `checked` + `onChange`, NOT `value` |
| `<input type="number">` | `value` is still a string — use `parseInt(e.target.value)` |
| `<input type="date">` | Value format is `"YYYY-MM-DD"` string |

---

## Phase 13: `useRef` & DOM Access

**Concepts:** useRef, focus management, uncontrolled inputs

### Update `src/components/TodoForm.jsx` — auto-focus

```jsx
import { useState, useRef, useEffect } from "react";

function TodoForm({ onAdd }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const titleInputRef = useRef(null);

  // Auto-focus the title input on mount
  useEffect(() => {
    titleInputRef.current.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    onAdd({ title: title.trim(), description: description.trim() });
    setTitle("");
    setDescription("");
    titleInputRef.current.focus(); // re-focus after submit
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="title">Title</label>
        <input
          ref={titleInputRef}
          id="title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What needs to be done?"
        />
      </div>
      <div>
        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional details..."
          rows={3}
        />
      </div>
      <button type="submit">Add Todo</button>
    </form>
  );
}

export default TodoForm;
```

### Bonus: uncontrolled form example (for comparison)

```jsx
import { useRef } from "react";

function UncontrolledForm({ onAdd }) {
  const titleRef = useRef(null);
  const descRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    onAdd({
      title: titleRef.current.value,
      description: descRef.current.value,
    });
    e.target.reset(); // reset the form DOM directly
  };

  return (
    <form onSubmit={handleSubmit}>
      <input ref={titleRef} type="text" placeholder="Title" />
      <textarea ref={descRef} placeholder="Description" />
      <button type="submit">Add</button>
    </form>
  );
}
```

### What you just learned

| Concept | Detail |
|---------|--------|
| `useRef(null)` | Creates a mutable ref object — `.current` holds the value |
| `ref={titleInputRef}` | Attaches ref to a DOM element |
| `.current.focus()` | Direct DOM manipulation — call methods on the element |
| Ref vs state | Changing a ref does NOT cause a re-render |
| Controlled | React state = source of truth. `value={state}` |
| Uncontrolled | DOM = source of truth. Read via `ref.current.value` |
| When to use ref | Focus, scroll, measure, integrate with non-React code |

---

## Phase 14: Custom Hooks

**Concepts:** extract reusable logic, hook composition

### Create `src/hooks/useTodos.js`

```jsx
import { useState, useEffect } from "react";

const API = "http://127.0.0.1:8000";

function useTodos() {
  const [todos, setTodos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchTodos() {
      try {
        const res = await fetch(`${API}/todos`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setTodos(await res.json());
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchTodos();
  }, []);

  const addTodo = async (newTodo) => {
    const res = await fetch(`${API}/todos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newTodo),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const created = await res.json();
    setTodos((prev) => [...prev, created]);
    return created;
  };

  const updateTodo = async (id, updates) => {
    const res = await fetch(`${API}/todos/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const updated = await res.json();
    setTodos((prev) => prev.map((t) => (t.id === id ? updated : t)));
    return updated;
  };

  const deleteTodo = async (id) => {
    const res = await fetch(`${API}/todos/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    setTodos((prev) => prev.filter((t) => t.id !== id));
  };

  return { todos, isLoading, error, addTodo, updateTodo, deleteTodo };
}

export default useTodos;
```

### Create `src/hooks/useForm.js`

```jsx
import { useState } from "react";

function useForm(initialValues) {
  const [values, setValues] = useState(initialValues);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setValues((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const reset = () => setValues(initialValues);

  return { values, handleChange, reset, setValues };
}

export default useForm;
```

### Simplified `src/App.js` — using custom hooks

```jsx
import useTodos from "./hooks/useTodos";
import TodoList from "./components/TodoList";
import TodoForm from "./components/TodoForm";

function App() {
  const { todos, isLoading, error, addTodo, updateTodo, deleteTodo } = useTodos();

  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;

  return (
    <div>
      <h1>Todo App</h1>
      <TodoForm onAdd={addTodo} />
      <TodoList todos={todos} onUpdate={updateTodo} onDelete={deleteTodo} />
    </div>
  );
}

export default App;
```

### What you just learned

| Concept | Detail |
|---------|--------|
| Custom hook | Just a function that calls other hooks — must start with `use` |
| `useTodos()` | Encapsulates ALL API + state logic. Component just consumes return values. |
| `useForm()` | Generic — works for any form. Uses `name` attribute to map inputs to state. |
| `setTodos(prev => ...)` | Functional update — safer when state depends on previous value |
| `[name]: value` | Computed property name — dynamic key based on input's `name` attribute |
| Hook rules | Only call hooks at top level (not inside if/loops). Only call in React functions. |

---

## Phase 15: Filtering, Searching & Derived State

**Concepts:** derived state, useMemo, radio buttons, search

### Create `src/components/TodoFilters.jsx`

```jsx
function TodoFilters({ search, onSearchChange, filter, onFilterChange, sortBy, onSortChange }) {
  return (
    <div>
      <div>
        <label htmlFor="search">Search</label>
        <input
          id="search"
          type="search"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Filter by title..."
        />
      </div>

      <div>
        <label htmlFor="filter-status">Status</label>
        <select
          id="filter-status"
          value={filter}
          onChange={(e) => onFilterChange(e.target.value)}
        >
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      <fieldset>
        <legend>Sort by</legend>
        <label>
          <input
            type="radio"
            name="sortBy"
            value="title"
            checked={sortBy === "title"}
            onChange={(e) => onSortChange(e.target.value)}
          />
          Title
        </label>
        <label>
          <input
            type="radio"
            name="sortBy"
            value="id"
            checked={sortBy === "id"}
            onChange={(e) => onSortChange(e.target.value)}
          />
          Date added
        </label>
      </fieldset>
    </div>
  );
}

export default TodoFilters;
```

### Update `src/App.js` — derived state with useMemo

```jsx
import { useState, useMemo } from "react";
import useTodos from "./hooks/useTodos";
import TodoList from "./components/TodoList";
import TodoForm from "./components/TodoForm";
import TodoFilters from "./components/TodoFilters";

function App() {
  const { todos, isLoading, error, addTodo, updateTodo, deleteTodo } = useTodos();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("id");

  // Derived state — computed from todos + filter settings
  // useMemo avoids recalculating on every render (only when dependencies change)
  const filteredTodos = useMemo(() => {
    let result = todos;

    // Filter by search text
    if (search) {
      result = result.filter((t) =>
        t.title.toLowerCase().includes(search.toLowerCase())
      );
    }

    // Filter by status
    if (filter === "active") {
      result = result.filter((t) => !t.completed);
    } else if (filter === "completed") {
      result = result.filter((t) => t.completed);
    }

    // Sort
    if (sortBy === "title") {
      result = [...result].sort((a, b) => a.title.localeCompare(b.title));
    }

    return result;
  }, [todos, search, filter, sortBy]);

  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;

  return (
    <div>
      <h1>Todo App</h1>
      <TodoForm onAdd={addTodo} />
      <TodoFilters
        search={search}
        onSearchChange={setSearch}
        filter={filter}
        onFilterChange={setFilter}
        sortBy={sortBy}
        onSortChange={setSortBy}
      />
      <p>{filteredTodos.length} of {todos.length} todos</p>
      <TodoList todos={filteredTodos} onUpdate={updateTodo} onDelete={deleteTodo} />
    </div>
  );
}

export default App;
```

### What you just learned

| Concept | Detail |
|---------|--------|
| Derived state | `filteredTodos` is computed from `todos` + filters — NOT stored in useState |
| `useMemo(fn, [deps])` | Caches the result — only recalculates when dependencies change |
| Anti-pattern | `useEffect` to sync filtered list into state — just compute it directly |
| `<input type="search">` | Same as text but has a clear button in some browsers |
| `<input type="radio">` | Group with same `name`. `checked` = controlled, `onChange` to update. |
| `<fieldset>` + `<legend>` | Groups related inputs — important for accessibility |
| `[...result].sort()` | Copy before sort — `.sort()` mutates the array in place |

### Common anti-patterns to avoid

```jsx
// BAD — storing derived state
const [filteredTodos, setFilteredTodos] = useState([]);
useEffect(() => {
  setFilteredTodos(todos.filter(...));
}, [todos, filter]);

// GOOD — compute it directly
const filteredTodos = useMemo(() => todos.filter(...), [todos, filter]);

// ALSO FINE for cheap computations — no useMemo needed
const filteredTodos = todos.filter(...);
```

---

## React Quick Reference

### Hooks learned

| Hook | Purpose |
|------|---------|
| `useState` | Component state — triggers re-render on change |
| `useEffect` | Side effects — fetch data, subscriptions, DOM mutations |
| `useRef` | Mutable value that persists across renders without re-rendering |
| `useMemo` | Cache expensive computations — recalculates only when deps change |

### HTML elements reviewed

| Element | Key React attributes |
|---------|---------------------|
| `<input type="text">` | `value`, `onChange` |
| `<input type="checkbox">` | `checked`, `onChange` (use `e.target.checked`) |
| `<input type="search">` | `value`, `onChange` |
| `<input type="radio">` | `name`, `value`, `checked`, `onChange` |
| `<input type="number">` | `value`, `onChange` (value is string, parse it) |
| `<input type="date">` | `value` (YYYY-MM-DD string), `onChange` |
| `<textarea>` | `value`, `onChange` (not children) |
| `<select>` + `<option>` | `value` on select (not `selected` on option) |
| `<form>` | `onSubmit` (always `e.preventDefault()`) |
| `<label>` | `htmlFor` (not `for`) |
| `<fieldset>` + `<legend>` | Group related inputs |
| `<button type="submit">` | Triggers form submit |
| `<button type="button">` | Does NOT trigger form submit |
