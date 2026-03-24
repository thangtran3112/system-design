from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.models import Base
from app.schemas import TodoCreate, TodoUpdate, TodoResponse
from app import crud

# alembic manages the SQL schema and models now.
# Base.metadata.create_all(bind=engine)

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
    
# Async and threading
import time
import asyncio

@app.get("/slow-bad")
async def slow_bad():
    time.sleep(3)  # ← blocking call inside async = disaster
    return {"message": "This blocked everything"}

# GOOD — runs in thread pool, other requests keep flowing
@app.get("/slow-sync")
def slow_sync():
    time.sleep(3) # ← blocking, but FastAPI auto-runs this in a thread, because of def
    return {"message": "This didn't block other requests"}

# GOOD — async sleep yields control, other requests keep flowing
@app.get("/slow-async")
async def slow_async():
    await asyncio.sleep(3) # non blocking
    return {"message": "This didn't block other requests either"}


from fastapi import BackgroundTasks
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_notification(todo_title: str):
    time.sleep(2)
    logger.info(f"Notification sent for: {todo_title}")

@app.post("/todos-notify", response_model=TodoResponse, status_code=201)
def create_todo_with_notification(
    todo: TodoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    new_todo = crud.create_todo(db, todo)

    # This background task runs after the response it sent - client doesn't wait here
    background_tasks.add_task(send_notification, new_todo.title)
    return new_todo

### MIDDLEWARE
from fastapi.middleware.cors import CORSMiddleware

# CORS — allow your React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Custom middleware — logs how long each request takes
@app.middleware("http")
async def add_timing_header(request, call_next):
    import time as _time
    start = _time.perf_counter()
    response = await call_next(request)
    duration_ms = (_time.perf_counter() - start) * 10000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)")
    return response

# High concurrency
from app.database_async import get_async_db
from app import crud_async
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/async/todos", response_model=list[TodoResponse])
async def read_todos_async(db: AsyncSession = Depends(get_async_db)):
    return await crud_async.get_todos(db)

import httpx
# SLOW — sequential: 2 API calls × ~200ms each = ~400ms total
@app.get("/external/sequential")
async def fetch_sequential():
    async with httpx.AsyncClient() as client:
        resp1 = await client.get("https://httpbin.org/delay/1")
        resp2 = await client.get("https://httpbin.org/delay/1")
    return {"total_calls": 2, "note": "took ~2 seconds (sequential)"}

@app.get("/external/parallel")
async def fetch_parallel():
    async with httpx.AsyncClient() as client:
        resp1, resp2 = await asyncio.gather(
            client.get("https://httpbin.org/delay/1"),
            client.get("https://httpbin.org/delay/1"),
        )
    return {"total_calls": 2, "note": "took ~1 second (parallel)"}