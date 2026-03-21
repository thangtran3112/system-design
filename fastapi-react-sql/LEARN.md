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
