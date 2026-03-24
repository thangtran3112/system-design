# FastAPI + GraphQL + OAuth + AWS ECS — Learning Guide

A hands-on guide to learn GraphQL with FastAPI, OAuth flows (with and without Cognito), and deploying to AWS ECS.
**You type everything yourself** — copy from snippets, edit, and learn by doing.

---

## Part 1: FastAPI + GraphQL

---

### Phase 1: Environment Setup

```bash
cd /Users/ttran/personal/system-design/fastapi-graphql-oauth

# 1. Create venv
uv venv --python 3.12

# 2. Activate
source .venv/bin/activate

# 3. Install dependencies
uv pip install fastapi uvicorn sqlalchemy strawberry-graphql pydantic pytest httpx

# 4. Create project structure
mkdir -p app tests
touch app/__init__.py app/main.py app/models.py app/database.py app/schemas.py
touch app/graphql_schema.py app/resolvers.py
touch tests/__init__.py tests/conftest.py tests/test_graphql.py
```

Your folder:
```
fastapi-graphql-oauth/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── graphql_schema.py
│   ├── main.py
│   ├── models.py
│   ├── resolvers.py
│   └── schemas.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_graphql.py
└── .venv/
```

---

### Phase 2: Database + SQLAlchemy Models

> Same pattern as your REST app. GraphQL sits on top of the same DB layer.

**`app/database.py`** — SQLite + SQLAlchemy session:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./graphql_todos.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**`app/models.py`** — User + Todo with a relationship:

```python
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    picture = Column(String, nullable=True)  # profile pic from OAuth provider
    provider = Column(String, default="local")  # "google", "cognito", "local"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    todos = relationship("Todo", back_populates="owner")

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    completed = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="todos")
```

> **Why add User now?** OAuth gives us user identity. The User model stores profile info
> from providers (Google, Cognito). The `provider` field tracks where the user came from.
> We link todos to users via `owner_id` so each user sees only their own todos.

---

### Phase 3: GraphQL Concepts — REST vs GraphQL

Before writing code, understand why GraphQL exists:

| Problem with REST | How GraphQL solves it |
|---|---|
| **Over-fetching**: `GET /users/1` returns ALL fields even if you only need `name` | Client specifies exact fields: `{ user { name } }` |
| **Under-fetching**: Need user + their todos = 2 requests (`/users/1` then `/users/1/todos`) | Single query: `{ user { name todos { title } } }` |
| **Rigid endpoints**: New UI needs = new endpoints or query params | One endpoint, flexible queries |
| **N+1 API calls**: List page needs data from multiple endpoints | Nested queries resolve in one round-trip |

**Key vocabulary:**

```
Schema    — The contract. Defines what you can query/mutate and the shape of data.
Query     — Read operations (like GET). "Give me data."
Mutation  — Write operations (like POST/PUT/DELETE). "Change data."
Resolver  — The function that actually fetches/modifies data for a field.
Type      — A shape of data (like a Pydantic model for GraphQL).
Field     — A single piece of data on a type.
```

**How a GraphQL request works:**

```
Client sends POST to /graphql with:
{
  "query": "{ todos { id title completed } }"
}

Server:
1. Parses the query string
2. Validates against the schema (do these fields exist?)
3. Calls resolvers for each field
4. Returns JSON matching the exact shape requested
```

> **One endpoint**: GraphQL always uses `POST /graphql`. No more designing URL structures.
> The query string IS the API contract.

---

### Phase 4: Strawberry GraphQL Types

> **Strawberry** is the modern Python GraphQL library. It uses dataclasses + type hints
> (no strings like `graphene`). FastAPI has first-class support for it.

**`app/graphql_schema.py`** — Define GraphQL types:

```python
import strawberry
from typing import Optional

# GraphQL types — these define what the CLIENT sees
# They are NOT your DB models. They're the "response shape."

@strawberry.type
class UserType:
    id: int
    email: str
    name: str
    picture: Optional[str]
    provider: str

@strawberry.type
class TodoType:
    id: int
    title: str
    description: str
    completed: bool
    owner: UserType  # nested! Client can query todo { owner { name } }

# Input types — what the client SENDS for mutations
# Like Pydantic's "Create" schemas

@strawberry.input
class CreateTodoInput:
    title: str
    description: str = ""

@strawberry.input
class UpdateTodoInput:
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
```

**Key differences from REST/Pydantic approach:**

```
REST:                               GraphQL:
- Pydantic schema → serialization   - Strawberry type → schema definition
- Multiple endpoints                 - One endpoint, multiple operations
- Response shape fixed by server     - Response shape chosen by client
- TodoResponse(id, title, ...)       - TodoType(id, title, owner: UserType)
                                       Client picks which fields they want
```

> **`@strawberry.type` vs `@strawberry.input`:**
> - `type` = output (server → client). What queries return.
> - `input` = input (client → server). What mutations accept.
> Same idea as Pydantic's `TodoResponse` vs `TodoCreate`.

---

### Phase 5: Resolvers — The Business Logic

> Resolvers are the functions that run when a query or mutation is executed.
> Think of them as your CRUD functions, but called by the GraphQL engine.

**`app/resolvers.py`** — Query and mutation resolvers:

```python
import strawberry
from typing import Optional
from app.database import SessionLocal
from app.models import Todo, User
from app.graphql_schema import TodoType, UserType, CreateTodoInput, UpdateTodoInput

def db_todo_to_type(todo: Todo) -> TodoType:
    """Convert SQLAlchemy model → GraphQL type."""
    return TodoType(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        owner=UserType(
            id=todo.owner.id,
            email=todo.owner.email,
            name=todo.owner.name,
            picture=todo.owner.picture,
            provider=todo.owner.provider,
        ),
    )

@strawberry.type
class Query:
    @strawberry.field
    def todos(self, owner_id: Optional[int] = None) -> list[TodoType]:
        """Fetch all todos, optionally filtered by owner."""
        db = SessionLocal()
        try:
            query = db.query(Todo)
            if owner_id is not None:
                query = query.filter(Todo.owner_id == owner_id)
            return [db_todo_to_type(t) for t in query.all()]
        finally:
            db.close()

    @strawberry.field
    def todo(self, id: int) -> Optional[TodoType]:
        """Fetch a single todo by ID."""
        db = SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            return db_todo_to_type(todo) if todo else None
        finally:
            db.close()

    @strawberry.field
    def users(self) -> list[UserType]:
        db = SessionLocal()
        try:
            return [
                UserType(
                    id=u.id, email=u.email, name=u.name,
                    picture=u.picture, provider=u.provider,
                )
                for u in db.query(User).all()
            ]
        finally:
            db.close()

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_todo(self, input: CreateTodoInput, owner_id: int) -> TodoType:
        db = SessionLocal()
        try:
            todo = Todo(
                title=input.title,
                description=input.description,
                owner_id=owner_id,
            )
            db.add(todo)
            db.commit()
            db.refresh(todo)
            return db_todo_to_type(todo)
        finally:
            db.close()

    @strawberry.mutation
    def update_todo(self, id: int, input: UpdateTodoInput) -> Optional[TodoType]:
        db = SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            if not todo:
                return None
            if input.title is not None:
                todo.title = input.title
            if input.description is not None:
                todo.description = input.description
            if input.completed is not None:
                todo.completed = input.completed
            db.commit()
            db.refresh(todo)
            return db_todo_to_type(todo)
        finally:
            db.close()

    @strawberry.mutation
    def delete_todo(self, id: int) -> bool:
        db = SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            if not todo:
                return False
            db.delete(todo)
            db.commit()
            return True
        finally:
            db.close()
```

> **Why `db_todo_to_type()`?** SQLAlchemy models ≠ GraphQL types. The resolver bridges them.
> In REST you had Pydantic's `model_validate()` doing this. Same idea, manual mapping.

> **Why `SessionLocal()` directly instead of `Depends(get_db)`?**
> Strawberry resolvers aren't FastAPI route handlers — they don't support `Depends()`.
> We manage the session manually. (There are patterns with context/dataloaders for production.)

---

### Phase 6: Wire It Up — FastAPI + Strawberry

**`app/main.py`** — Mount GraphQL on FastAPI:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import strawberry
from strawberry.fastapi import GraphQLRouter
from app.database import engine, Base
from app.resolvers import Query, Mutation

# Create tables
Base.metadata.create_all(bind=engine)

# Build the GraphQL schema from our Query + Mutation classes
schema = strawberry.Schema(query=Query, mutation=Mutation)

# GraphQLRouter is a FastAPI router that handles POST /graphql
graphql_app = GraphQLRouter(schema)

app = FastAPI(title="GraphQL Todo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount at /graphql — this gives us the endpoint AND the GraphiQL playground
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok"}
```

Run the server:
```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/graphql** — you get **GraphiQL**, an interactive playground.

---

### Phase 7: Try It in GraphiQL

> GraphiQL is like Swagger but for GraphQL. You type queries and see results live.

First, seed a test user. In a new terminal:
```bash
source .venv/bin/activate
python -c "
from app.database import SessionLocal, engine, Base
from app.models import User
Base.metadata.create_all(bind=engine)
db = SessionLocal()
user = User(email='test@example.com', name='Test User', provider='local')
db.add(user)
db.commit()
print(f'Created user id={user.id}')
db.close()
"
```

Now try these in GraphiQL (http://localhost:8000/graphql):

**Query all users:**
```graphql
{
  users {
    id
    name
    email
  }
}
```

**Create a todo:**
```graphql
mutation {
  createTodo(input: { title: "Learn GraphQL", description: "With Strawberry" }, ownerId: 1) {
    id
    title
    owner {
      name
    }
  }
}
```

> Notice: the response only contains `id`, `title`, and `owner.name` — exactly what we asked for.
> If we also wanted `description` and `completed`, we'd add them to the query. This is the
> core value of GraphQL: the client controls the response shape.

**Query todos with nested owner:**
```graphql
{
  todos {
    id
    title
    completed
    owner {
      name
      email
    }
  }
}
```

> In REST, this would be either 2 API calls (GET /todos + GET /users/:id for each),
> or a custom endpoint with joins. In GraphQL, it's one query.

**Update a todo:**
```graphql
mutation {
  updateTodo(id: 1, input: { completed: true }) {
    id
    title
    completed
  }
}
```

**Delete a todo:**
```graphql
mutation {
  deleteTodo(id: 1)
}
```

**Filter by owner:**
```graphql
{
  todos(ownerId: 1) {
    title
    completed
  }
}
```

---

### Phase 8: Testing GraphQL

**`tests/conftest.py`:**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.main import app
from app.models import User

TEST_DB_URL = "sqlite:///./test_graphql.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Seed a test user
    db = TestSession()
    user = User(email="test@test.com", name="Tester", provider="local")
    db.add(user)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)
```

> **Note:** For this to work with our resolvers (which use `SessionLocal()` directly),
> you'd need to monkeypatch `SessionLocal` or use dependency injection. For learning
> purposes, this shows the pattern. In production, use a proper DI approach.

**`tests/test_graphql.py`:**

```python
def test_create_and_query_todo(client):
    # Create
    mutation = """
        mutation {
            createTodo(input: { title: "Test Todo" }, ownerId: 1) {
                id
                title
                description
                completed
            }
        }
    """
    response = client.post("/graphql", json={"query": mutation})
    assert response.status_code == 200
    data = response.json()["data"]["createTodo"]
    assert data["title"] == "Test Todo"
    assert data["completed"] is False
    todo_id = data["id"]

    # Query
    query = f"""
        {{
            todo(id: {todo_id}) {{
                title
                completed
                owner {{
                    name
                }}
            }}
        }}
    """
    response = client.post("/graphql", json={"query": query})
    data = response.json()["data"]["todo"]
    assert data["title"] == "Test Todo"
    assert data["owner"]["name"] == "Tester"

def test_update_todo(client):
    # Create first
    create = """
        mutation {
            createTodo(input: { title: "Update Me" }, ownerId: 1) { id }
        }
    """
    response = client.post("/graphql", json={"query": create})
    todo_id = response.json()["data"]["createTodo"]["id"]

    # Update
    update = f"""
        mutation {{
            updateTodo(id: {todo_id}, input: {{ completed: true, title: "Updated" }}) {{
                title
                completed
            }}
        }}
    """
    response = client.post("/graphql", json={"query": update})
    data = response.json()["data"]["updateTodo"]
    assert data["title"] == "Updated"
    assert data["completed"] is True

def test_delete_todo(client):
    create = """
        mutation {
            createTodo(input: { title: "Delete Me" }, ownerId: 1) { id }
        }
    """
    response = client.post("/graphql", json={"query": create})
    todo_id = response.json()["data"]["createTodo"]["id"]

    delete = f"""
        mutation {{
            deleteTodo(id: {todo_id})
        }}
    """
    response = client.post("/graphql", json={"query": delete})
    assert response.json()["data"]["deleteTodo"] is True

def test_query_empty_todos(client):
    query = "{ todos { id title } }"
    response = client.post("/graphql", json={"query": query})
    assert response.json()["data"]["todos"] == []
```

> **Key testing pattern:** GraphQL tests always POST to `/graphql` with `{"query": "..."}`.
> The response is always `{"data": {...}}` on success or `{"errors": [...]}` on failure.

Run tests:
```bash
pytest tests/ -v
```

---

## Part 2: OAuth — Concepts and Flows

---

### Phase 9: OAuth2 Core Concepts

Before writing any code, understand what OAuth2 actually solves:

**The problem:**
Your app wants to know who a user is (authentication) and access their data (authorization),
but you don't want to handle their password. If every app stored passwords, one breach
leaks everything.

**The solution: delegate authentication to a trusted provider (Google, GitHub, etc.)**

**Key roles:**

```
Resource Owner    — The user (you, clicking "Login with Google")
Client            — Your app (this FastAPI server)
Authorization     — Google, GitHub, Cognito (the login page provider)
  Server
Resource Server   — The API that holds user data (Google's user info API)
```

**The Authorization Code Flow (most common, most secure):**

```
┌──────────┐     1. Click "Login with Google"      ┌──────────┐
│          │ ──────────────────────────────────────→ │          │
│  Your    │     2. Redirect to Google login         │  Google  │
│  App     │ ←────────────────────────────────────── │  Auth    │
│ (Client) │     3. User logs in, Google redirects   │  Server  │
│          │        back with AUTHORIZATION CODE     │          │
│          │ ──────────────────────────────────────→ │          │
│          │     4. App exchanges code for TOKENS    │          │
│          │ ←────────────────────────────────────── │          │
│          │     5. App uses access_token to get     │          │
│          │        user info from Google API        │          │
└──────────┘                                         └──────────┘
```

**Why the authorization code? Why not return the token directly?**

```
The redirect URL is visible in the browser address bar.
If Google put the access_token in the URL, anyone looking at
the screen or browser history could steal it.

Instead, Google returns a short-lived CODE in the URL.
Your server (not the browser) exchanges this code for tokens
using a server-to-server request that includes your CLIENT_SECRET.

This means: even if someone steals the code, they can't get
tokens without your secret.
```

**The tokens:**

```
access_token   — Short-lived (minutes to hours). Used to call APIs.
                 "Here's my badge, let me in."

refresh_token  — Long-lived (days to months). Used to get new access_tokens
                 without making the user log in again.
                 "I already proved who I am, give me a new badge."

id_token       — JWT containing user profile info (email, name, picture).
                 Only in OpenID Connect (OIDC), which is OAuth2 + identity.
                 "Here's my ID card with my photo."
```

**JWT (JSON Web Token) — the format of most tokens:**

```
eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjM0NTYiLCJlbWFpbCI6InVzZXJAZ21haWwuY29tIn0.signature
│                      │                                                    │
│  Header (base64)     │  Payload (base64)                                  │  Signature
│  {"alg": "RS256"}    │  {"sub": "123456", "email": "user@gmail.com"}      │  (verified with
│                      │                                                    │   public key)

It's NOT encrypted — anyone can decode the payload.
The signature proves it wasn't tampered with.
NEVER put secrets in a JWT.
```

---

### Phase 10: OAuth2 Without Cognito — Direct Google OAuth

> This is "raw" OAuth. Your app talks directly to Google. No middleware.
> Understanding this first makes Cognito make sense later.

**Step 1: Google Cloud Console Setup (real steps, do once):**

```
1. Go to https://console.cloud.google.com/
2. Create a project (or use existing)
3. Go to APIs & Services → Credentials
4. Create OAuth 2.0 Client ID:
   - Application type: Web application
   - Authorized redirect URIs: http://localhost:8000/auth/google/callback
5. Copy the CLIENT_ID and CLIENT_SECRET
```

**Step 2: Configuration**

Create **`app/config.py`**:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

Create **`.env`** (NEVER commit this):
```
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
JWT_SECRET=a-random-secret-string
```

> **`pydantic_settings`**: Reads env vars automatically. `GOOGLE_CLIENT_ID` env var maps
> to `google_client_id` field. Install with: `uv pip install pydantic-settings`

**Step 3: The OAuth Flow in Code**

Create **`app/auth.py`** — the full authorization code flow:

```python
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse
import httpx
import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.database import SessionLocal
from app.models import User

router = APIRouter(prefix="/auth")

# ──────────────────────────────────────────────
# Step 1: Redirect user to Google's login page
# ──────────────────────────────────────────────
@router.get("/google/login")
def google_login():
    """User clicks "Login with Google" → we redirect them to Google."""
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&response_type=code"          # We want an authorization CODE
        "&scope=openid email profile"  # What data we want access to
        "&access_type=offline"         # Also give us a refresh_token
        "&prompt=consent"              # Always show consent screen
    )
    return RedirectResponse(url=google_auth_url)

# ──────────────────────────────────────────────
# Step 2: Google redirects back here with ?code=xxx
# ──────────────────────────────────────────────
@router.get("/google/callback")
async def google_callback(code: str):
    """
    Google sends the user back here after login.
    The 'code' query param is the authorization code.
    We exchange it for tokens.
    """
    # Exchange authorization code for tokens (server-to-server, not visible to browser)
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")

    tokens = token_response.json()
    # tokens = {
    #   "access_token": "ya29.xxx...",
    #   "refresh_token": "1//xxx...",
    #   "id_token": "eyJhbG...",       ← JWT with user info
    #   "expires_in": 3599,
    #   "token_type": "Bearer"
    # }

    # ──────────────────────────────────────────────
    # Step 3: Get user info from Google
    # ──────────────────────────────────────────────
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")

    google_user = userinfo_response.json()
    # google_user = {
    #   "id": "123456789",
    #   "email": "user@gmail.com",
    #   "name": "John Doe",
    #   "picture": "https://lh3.googleusercontent.com/..."
    # }

    # ──────────────────────────────────────────────
    # Step 4: Create or update user in our database
    # ──────────────────────────────────────────────
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == google_user["email"]).first()
        if not user:
            user = User(
                email=google_user["email"],
                name=google_user["name"],
                picture=google_user.get("picture"),
                provider="google",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    # ──────────────────────────────────────────────
    # Step 5: Issue OUR OWN JWT for the session
    # ──────────────────────────────────────────────
    # We don't use Google's token for our API. We create our own.
    # This way our app isn't dependent on Google's token lifecycle.
    app_token = create_app_token(user_id=user.id, email=user.email)

    # In a real app, you'd set this as an HTTP-only cookie
    # or return it to the frontend to store.
    return {"access_token": app_token, "user": {"id": user.id, "name": user.name}}


def create_app_token(user_id: int, email: str) -> str:
    """Create a JWT token for our app's session."""
    payload = {
        "sub": str(user_id),       # subject — who this token is for
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes),
        "iat": datetime.now(timezone.utc),  # issued at
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_app_token(token: str) -> dict:
    """Verify and decode our app's JWT."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Step 4: Protect GraphQL with auth**

Create **`app/dependencies.py`**:

```python
from fastapi import Depends, HTTPException, Request
from app.auth import verify_app_token
from app.database import SessionLocal
from app.models import User

def get_current_user(request: Request) -> User:
    """Extract and verify JWT from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    payload = verify_app_token(token)

    db = SessionLocal()
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    db.close()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

**Step 5: Update main.py to include auth routes**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import strawberry
from strawberry.fastapi import GraphQLRouter
from app.database import engine, Base
from app.resolvers import Query, Mutation
from app.auth import router as auth_router  # ← add this

Base.metadata.create_all(bind=engine)

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

app = FastAPI(title="GraphQL Todo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graphql_app, prefix="/graphql")
app.include_router(auth_router)  # ← add this

@app.get("/health")
def health():
    return {"status": "ok"}
```

**The complete flow when a user clicks "Login with Google":**

```
1. Browser → GET /auth/google/login
2. Server responds with 302 Redirect → Google's login page
3. User enters Google credentials (on Google's site, NOT yours)
4. Google redirects → GET /auth/google/callback?code=abc123
5. Server exchanges code for tokens (POST to Google, server-to-server)
6. Server gets user info from Google API using access_token
7. Server creates/updates User in DB
8. Server creates its OWN JWT and returns it
9. Frontend stores JWT, sends it with every GraphQL request
```

> **Why issue our own JWT instead of using Google's access_token?**
> - Google's token expires based on Google's rules, not ours
> - If we switch from Google to GitHub later, our API doesn't change
> - We control the payload (user_id, roles, permissions)
> - Our backend only needs to verify our own secret, not call Google on every request

---

### Phase 11: OAuth State Parameter — CSRF Protection

The flow above has a security hole. Here's the attack:

```
Attacker's plan:
1. Attacker starts OAuth flow, gets their authorization code from Google
2. Attacker crafts a URL: /auth/google/callback?code=ATTACKERS_CODE
3. Attacker tricks victim into clicking this link (phishing email, etc.)
4. Victim's browser hits your callback with the ATTACKER'S code
5. Your app logs the victim in as the attacker
6. Victim adds sensitive data, thinking it's their account
7. Attacker logs in and sees victim's data
```

**The fix — `state` parameter:**

```python
import secrets

@router.get("/google/login")
def google_login():
    # Generate a random, unguessable string
    state = secrets.token_urlsafe(32)

    # Store it in the session/cookie so we can verify it later
    # (In production, use a signed cookie or server-side session)
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile"
        f"&state={state}"  # ← Include state
    )
    response = RedirectResponse(url=google_auth_url)
    response.set_cookie("oauth_state", state, httponly=True, max_age=300)
    return response

@router.get("/google/callback")
async def google_callback(code: str, state: str, request: Request):
    # Verify state matches what we stored
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state — possible CSRF attack")

    # Continue with code exchange...
```

> **How it works:** Your server creates a random `state`, stores it in a cookie,
> and includes it in the Google URL. Google sends it back unchanged. If the `state`
> in the callback doesn't match your cookie, someone tampered with the flow.
> The attacker can't forge the cookie because they don't control the victim's browser cookies.

---

### Phase 12: OAuth with AWS Cognito

> Cognito is a managed auth service. Instead of talking to Google directly,
> Cognito sits in the middle and handles multiple providers for you.

**Without Cognito (Phase 10):**
```
Your App → Google directly
Your App → GitHub directly
Your App → Facebook directly
(Each provider needs separate code)
```

**With Cognito:**
```
Your App → Cognito → Google
                   → GitHub
                   → Facebook
(One integration, Cognito handles all providers)
```

**Cognito concepts:**

```
User Pool       — A directory of users. Like a database of accounts.
                  Handles sign-up, sign-in, password reset, MFA.
                  Issues JWTs (id_token, access_token, refresh_token).

App Client      — Your app's registration with Cognito (like Google's CLIENT_ID).
                  Has a client_id and optional client_secret.

Hosted UI       — Cognito gives you a pre-built login page.
                  Supports "Login with Google/Facebook/etc" buttons.
                  You can also build your own UI and use Cognito's API.

Identity Pool   — Maps authenticated users to AWS IAM roles.
  (Federated     (Used for accessing S3, DynamoDB, etc. directly)
   Identities)    NOT needed for typical web app auth.

Domain          — Cognito gives you a URL: https://your-app.auth.us-east-1.amazoncognito.com
                  This hosts the login/signup pages and OAuth endpoints.
```

**Setting up Cognito (AWS Console):**

```
1. Go to AWS Cognito → Create User Pool
2. Configure sign-in: Email
3. Configure security: Default password policy, No MFA (for learning)
4. Configure sign-up: Allow self-registration
5. Configure messaging: Email with Cognito (default)
6. Integrate your app:
   - App client name: "fastapi-graphql"
   - Generate client secret: Yes
   - OAuth flows: Authorization code grant
   - Callback URL: http://localhost:8000/auth/cognito/callback
   - Scopes: openid, email, profile
7. Under "Federated identity providers":
   - Add Google: paste your Google CLIENT_ID and CLIENT_SECRET
   - Cognito maps Google's user info to Cognito user attributes
8. Domain: Choose a prefix → gives you https://YOUR-PREFIX.auth.us-east-1.amazoncognito.com
```

**The Cognito OAuth flow in code:**

Add to **`app/config.py`**:

```python
class Settings(BaseSettings):
    # ... existing Google settings ...

    # Cognito settings
    cognito_domain: str = ""         # e.g., "your-app.auth.us-east-1.amazoncognito.com"
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    cognito_redirect_uri: str = "http://localhost:8000/auth/cognito/callback"
    cognito_region: str = "us-east-1"
    cognito_user_pool_id: str = ""

    class Config:
        env_file = ".env"
```

Add to **`app/auth.py`** — Cognito routes:

```python
import base64

# ──────────────────────────────────────────────
# Cognito OAuth — same Authorization Code flow!
# The only difference: we talk to Cognito instead of Google.
# ──────────────────────────────────────────────

@router.get("/cognito/login")
def cognito_login():
    """Redirect to Cognito's Hosted UI (which may show Google/Facebook buttons)."""
    state = secrets.token_urlsafe(32)
    cognito_url = (
        f"https://{settings.cognito_domain}/oauth2/authorize"
        f"?client_id={settings.cognito_client_id}"
        f"&redirect_uri={settings.cognito_redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile"
        f"&state={state}"
    )
    response = RedirectResponse(url=cognito_url)
    response.set_cookie("oauth_state", state, httponly=True, max_age=300)
    return response

@router.get("/cognito/callback")
async def cognito_callback(code: str, state: str, request: Request):
    # Verify state (same CSRF protection)
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for tokens — same pattern, different URLs
    # Cognito requires Basic auth header: base64(client_id:client_secret)
    credentials = base64.b64encode(
        f"{settings.cognito_client_id}:{settings.cognito_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"https://{settings.cognito_domain}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.cognito_redirect_uri,
            },
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code")

    tokens = token_response.json()

    # Cognito's id_token IS the user info (it's a JWT we can decode)
    # No need for a separate userinfo API call (though Cognito has one)
    id_token_payload = jwt.decode(
        tokens["id_token"],
        options={"verify_signature": False},  # In production: verify with Cognito's JWKS
    )
    # id_token_payload = {
    #   "sub": "a1b2c3d4-xxxx-xxxx-xxxx",   ← Cognito user ID
    #   "email": "user@gmail.com",
    #   "name": "John Doe",
    #   "cognito:username": "google_123456",
    #   "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx"
    # }

    # Create/update user in our DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == id_token_payload["email"]).first()
        if not user:
            user = User(
                email=id_token_payload["email"],
                name=id_token_payload.get("name", ""),
                picture=id_token_payload.get("picture"),
                provider="cognito",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    # Issue our own app JWT (same as Google flow)
    app_token = create_app_token(user_id=user.id, email=user.email)
    return {"access_token": app_token, "user": {"id": user.id, "name": user.name}}
```

**Comparing the two flows side by side:**

```
                        Direct Google          With Cognito
Login URL:              accounts.google.com    your-prefix.auth.region.amazoncognito.com
Token endpoint:         oauth2.googleapis.com  cognito-domain/oauth2/token
Auth header for token:  Not needed (in body)   Basic base64(client_id:secret)
User info:              Separate API call      Decode the id_token JWT
User ID format:         Numeric string         UUID (Cognito sub)
Multiple providers:     Build each one         Configure in Cognito console
MFA:                    Build it yourself      Toggle in Cognito settings
Password reset:         Build it yourself      Built-in
```

> **When to use Cognito?**
> - You need multiple OAuth providers (Google + GitHub + SAML)
> - You want managed password auth (sign-up, reset, MFA) without building it
> - You need AWS IAM integration (accessing S3/DynamoDB with user credentials)
>
> **When to go direct?**
> - Only one provider, simple setup
> - Don't want AWS vendor lock-in
> - Need full control over the UX

---

### Phase 13: Token Verification in Production

In Phase 10 we skipped signature verification (`verify_signature: False`). Here's how to do it properly:

**Cognito publishes its public keys at a JWKS (JSON Web Key Set) URL:**

```python
# The JWKS URL for your Cognito User Pool
# https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json

import jwt
from jwt import PyJWKClient

def verify_cognito_token(id_token: str) -> dict:
    """Verify a Cognito JWT using the public JWKS."""
    jwks_url = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
        f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )

    # PyJWKClient fetches and caches the public keys
    jwk_client = PyJWKClient(jwks_url)

    # Get the signing key that matches this token's "kid" header
    signing_key = jwk_client.get_signing_key_from_jwt(id_token)

    # Now verify the signature, expiry, and issuer
    payload = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.cognito_client_id,  # token must be for our app
        issuer=f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}",
    )
    return payload
```

**How JWKS verification works:**

```
1. Cognito signs JWTs with a private key (RSA)
2. Cognito publishes the matching public key at the JWKS URL
3. Your app downloads the public key (cached, not every request)
4. Your app uses the public key to verify the JWT signature
5. If the signature is valid → the token came from Cognito, not an attacker

This is asymmetric crypto:
- Private key (Cognito only) → signs tokens
- Public key (anyone)        → verifies tokens
```

> **For Google tokens:** Google's JWKS is at `https://www.googleapis.com/oauth2/v3/certs`.
> Same concept, same verification pattern.
> But since we issue our OWN JWT after Google login (Phase 10), we use symmetric
> HS256 (shared secret) for our app tokens. Simpler, fine for single-server apps.

---

### Phase 14: OAuth Refresh Token Flow

Access tokens expire. Refresh tokens let you get new ones without re-login:

```python
@router.post("/auth/refresh")
async def refresh_token(request: Request):
    """Use a refresh token to get a new access token."""
    body = await request.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token required")

    # Exchange refresh_token for new tokens
    # Works with both Google and Cognito (different URLs, same pattern)
    credentials = base64.b64encode(
        f"{settings.cognito_client_id}:{settings.cognito_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{settings.cognito_domain}/oauth2/token",
            data={
                "grant_type": "refresh_token",  # ← different grant_type
                "refresh_token": refresh_token,
            },
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Refresh failed — user must re-login")

    tokens = response.json()
    # Note: Cognito does NOT return a new refresh_token here.
    # Google does. Behavior varies by provider.
    return {
        "access_token": tokens["access_token"],
        "expires_in": tokens["expires_in"],
    }
```

**Token lifecycle:**

```
Login:
  → access_token (30 min), refresh_token (30 days)

After 30 min, access_token expires:
  → Frontend gets 401
  → Frontend calls /auth/refresh with refresh_token
  → Gets new access_token (30 min)
  → Retries the failed request

After 30 days, refresh_token expires:
  → /auth/refresh returns 401
  → User must log in again (full OAuth flow)

Frontend pattern:
  fetch('/graphql', { headers: { Authorization: `Bearer ${accessToken}` } })
    .then(res => {
      if (res.status === 401) {
        return refreshAndRetry();  // automatic refresh
      }
      return res.json();
    });
```

---

## Part 3: Deploying to AWS ECS

---

### Phase 15: Dockerize the Application

**`Dockerfile`** — multi-stage build:

```dockerfile
# Stage 1: Build (install deps)
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast installs
RUN pip install uv

# Copy dependency list first (Docker layer caching)
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Stage 2: Runtime (slim image)
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/

# Don't run as root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`requirements.txt`** — generate from your venv:

```bash
uv pip freeze > requirements.txt
```

**`.dockerignore`:**

```
.venv/
__pycache__/
*.pyc
.env
.git/
tests/
*.db
```

**Build and test locally:**

```bash
docker build -t graphql-todo .
docker run -p 8000:8000 --env-file .env graphql-todo
# Visit http://localhost:8000/graphql
```

> **Why multi-stage?** The builder stage has build tools. The final image only has
> the runtime — smaller image (~150MB vs ~500MB), less attack surface.

> **Why `--system`?** Inside Docker, there's no venv. We install directly into the
> system Python. The container IS the isolation.

---

### Phase 16: AWS ECS Concepts

Before deploying, understand the ECS building blocks:

```
┌─────────────────────────────────────────────────┐
│                   ECS Cluster                    │
│  (Logical grouping — like a Kubernetes cluster)  │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │              Service                        │ │
│  │  (Ensures N tasks are always running)       │ │
│  │  (Like a Kubernetes Deployment)             │ │
│  │                                             │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐    │ │
│  │  │  Task   │  │  Task   │  │  Task   │    │ │
│  │  │(1 copy) │  │(1 copy) │  │(1 copy) │    │ │
│  │  │         │  │         │  │         │    │ │
│  │  │Container│  │Container│  │Container│    │ │
│  │  │(Docker) │  │(Docker) │  │(Docker) │    │ │
│  │  └─────────┘  └─────────┘  └─────────┘    │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ┌──────────────────────┐                        │
│  │  Task Definition     │                        │
│  │  (Blueprint/recipe)  │                        │
│  │  - Docker image      │                        │
│  │  - CPU/Memory        │                        │
│  │  - Env vars          │                        │
│  │  - Port mappings     │                        │
│  │  - Log config        │                        │
│  └──────────────────────┘                        │
└─────────────────────────────────────────────────┘
```

**Key concepts:**

```
Task Definition    — The recipe. "Use this Docker image, with 512MB RAM, these env vars."
                     Like a docker-compose.yml but for ECS.
                     Versioned: revision 1, 2, 3... (update = new revision).

Task               — A running instance of a Task Definition. One or more containers.
                     Like `docker run` but managed by ECS.

Service            — Keeps N tasks running. If a task crashes, Service starts a new one.
                     Handles rolling deploys (spin up new, drain old).
                     Connects to a Load Balancer.

Cluster            — Logical grouping. Can have multiple Services.

Fargate            — Serverless compute for ECS. No EC2 instances to manage.
                     You just say "I need 0.5 CPU and 1GB RAM" and AWS handles the rest.
                     (vs EC2 launch type: you manage the VMs yourself)

ECR                — Elastic Container Registry. AWS's Docker Hub.
                     Where you push your Docker images.

ALB                — Application Load Balancer. Routes traffic to your tasks.
                     Health checks, HTTPS termination, path-based routing.
```

**Fargate vs EC2 launch type:**

```
                    Fargate                     EC2
What you manage:    Nothing (serverless)        EC2 instances, scaling, patching
Pricing:            Per-second for CPU/RAM      EC2 instance cost (can use spot/reserved)
Startup time:       ~30-60 seconds              Faster if instances are warm
Best for:           Variable/low traffic         Predictable high traffic, GPU, cost optimization
```

---

### Phase 17: Push Image to ECR

```bash
# 1. Create an ECR repository
aws ecr create-repository --repository-name graphql-todo --region us-east-1

# 2. Login Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 3. Tag your image for ECR
docker tag graphql-todo:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/graphql-todo:latest

# 4. Push
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/graphql-todo:latest
```

> Replace `ACCOUNT_ID` with your AWS account ID (12-digit number).
> You can find it with `aws sts get-caller-identity`.

---

### Phase 18: ECS Task Definition

Create **`ecs/task-definition.json`**:

```json
{
  "family": "graphql-todo",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "graphql-todo",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/graphql-todo:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        { "name": "GOOGLE_CLIENT_ID", "value": "your-client-id" }
      ],
      "secrets": [
        {
          "name": "GOOGLE_CLIENT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:google-oauth-secret"
        },
        {
          "name": "JWT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/graphql-todo",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

**What each field means:**

```
family                — Name of the task definition (like a project name)
networkMode: awsvpc   — Each task gets its own IP (required for Fargate)
cpu: "256"            — 0.25 vCPU (smallest Fargate size). "1024" = 1 vCPU
memory: "512"         — 512 MB RAM
executionRoleArn      — IAM role that ECS uses to pull images from ECR
                        and read secrets from Secrets Manager

containerDefinitions:
  image               — Your ECR image URI
  portMappings        — Expose port 8000

  environment         — Plain text env vars (non-sensitive)
  secrets             — Pulled from AWS Secrets Manager at runtime.
                        NEVER put secrets in environment[].
                        The container sees them as regular env vars.

  logConfiguration    — Ship container logs to CloudWatch Logs
  healthCheck         — ECS checks if the container is healthy
                        Unhealthy containers get replaced
```

Register the task definition:
```bash
aws ecs register-task-definition --cli-input-json file://ecs/task-definition.json
```

---

### Phase 19: Create ECS Cluster and Service

```bash
# 1. Create the cluster
aws ecs create-cluster --cluster-name graphql-cluster

# 2. Create a CloudWatch log group
aws logs create-log-group --log-group-name /ecs/graphql-todo

# 3. Store secrets in Secrets Manager
aws secretsmanager create-secret --name google-oauth-secret \
  --secret-string "your-google-client-secret"
aws secretsmanager create-secret --name jwt-secret \
  --secret-string "a-strong-random-secret"

# 4. Create the service (Fargate)
aws ecs create-service \
  --cluster graphql-cluster \
  --service-name graphql-todo-service \
  --task-definition graphql-todo \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxxxx,subnet-yyyyy],
    securityGroups=[sg-xxxxx],
    assignPublicIp=ENABLED
  }"
```

> **`desired-count: 2`** — Run 2 copies. If one crashes, traffic goes to the other
> while ECS starts a replacement.
>
> **`assignPublicIp: ENABLED`** — For learning. In production, put tasks in
> private subnets behind an ALB.
>
> You need to replace `subnet-xxxxx` and `sg-xxxxx` with your VPC's actual values.
> Find them with: `aws ec2 describe-subnets` and `aws ec2 describe-security-groups`.

---

### Phase 20: Add a Load Balancer

In production, you don't expose tasks directly. You put an ALB in front:

```bash
# 1. Create ALB
aws elbv2 create-load-balancer \
  --name graphql-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx

# 2. Create target group (ECS tasks register here)
aws elbv2 create-target-group \
  --name graphql-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx \
  --target-type ip \
  --health-check-path /health

# 3. Create listener (ALB listens on port 80, forwards to target group)
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...

# 4. Update ECS service to use the ALB
aws ecs update-service \
  --cluster graphql-cluster \
  --service graphql-todo-service \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=graphql-todo,containerPort=8000"
```

**Full architecture:**

```
Internet → ALB (port 80/443) → Target Group → ECS Tasks (port 8000)
                                                 ├── Task 1 (container)
                                                 └── Task 2 (container)

ALB handles:
- Health checks (removes unhealthy tasks)
- SSL/TLS termination (HTTPS at ALB, HTTP to tasks)
- Load balancing across tasks
```

---

### Phase 21: Deploying Updates

When you push code changes:

```bash
# 1. Build new image
docker build -t graphql-todo .

# 2. Tag with version (not just "latest")
docker tag graphql-todo:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/graphql-todo:v2

# 3. Push
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/graphql-todo:v2

# 4. Update task definition with new image tag
# Edit task-definition.json: change image tag to :v2
aws ecs register-task-definition --cli-input-json file://ecs/task-definition.json

# 5. Update service (triggers rolling deployment)
aws ecs update-service \
  --cluster graphql-cluster \
  --service graphql-todo-service \
  --task-definition graphql-todo:2 \
  --force-new-deployment
```

**Rolling deployment (what happens):**

```
Before:   [Task v1]  [Task v1]     (desired: 2)

Deploy:   [Task v1]  [Task v1]  [Task v2]  [Task v2]
          ↑ draining              ↑ starting

After:    [Task v2]  [Task v2]     (desired: 2)

ECS:
1. Starts new tasks with v2 image
2. Waits for health check to pass
3. Registers v2 tasks with ALB
4. Drains connections from v1 tasks (stops sending new requests)
5. Stops v1 tasks
→ Zero-downtime deployment
```

---

### Phase 22: Summary — Putting It All Together

**Full architecture:**

```
┌─────────┐     ┌─────────┐     ┌─────────────────────────────────────┐
│ Browser  │────→│   ALB   │────→│  ECS Fargate Cluster               │
│(React)   │     │(HTTPS)  │     │                                     │
│          │     │         │     │  ┌────────────────────────────┐     │
│          │     │         │     │  │ FastAPI Container           │     │
│          │     │         │     │  │                             │     │
│          │     │         │     │  │  /graphql  → Strawberry     │     │
│          │     │         │     │  │  /auth/*   → OAuth routes   │     │
│          │     │         │     │  │  /health   → health check   │     │
│          │     │         │     │  └─────────────┬──────────────┘     │
│          │     │         │     │                │                     │
│          │     │         │     │  ┌─────────────▼──────────────┐     │
│          │     │         │     │  │  SQLite / RDS Postgres     │     │
│          │     │         │     │  └────────────────────────────┘     │
│          │     │         │     └─────────────────────────────────────┘
└─────────┘     └─────────┘
                                 External:
                                   → Google OAuth / Cognito
                                   → AWS Secrets Manager
                                   → CloudWatch Logs
                                   → ECR (Docker images)
```

**What you learned:**

| Topic | Key Takeaway |
|---|---|
| GraphQL vs REST | Client controls response shape. One endpoint, flexible queries. |
| Strawberry | Python-native GraphQL with type hints. `@strawberry.type` = output, `@strawberry.input` = input. |
| Resolvers | Functions that fetch data for GraphQL fields. Like CRUD functions called by the engine. |
| OAuth2 Auth Code Flow | Redirect → login at provider → callback with code → exchange for tokens. |
| State parameter | CSRF protection. Random value in cookie, verified on callback. |
| JWT tokens | Base64 payload + signature. Not encrypted, but tamper-proof. |
| Cognito vs Direct | Cognito = managed multi-provider auth. Direct = simpler, one provider. |
| JWKS verification | Verify JWT signature using provider's public key. |
| Refresh tokens | Get new access tokens without re-login. |
| Docker multi-stage | Builder stage installs, runtime stage runs. Smaller images. |
| ECS concepts | Task Definition (recipe) → Task (running container) → Service (keeps N running). |
| Fargate | Serverless containers. No EC2 management. |
| ECR | AWS Docker registry. Push images, ECS pulls them. |
| ALB + ECS | Load balancer routes to healthy tasks. Rolling deploys = zero downtime. |

---

## Part 4: Database Migrations with Alembic

---

### Why do we need migrations?

Right now, `main.py` creates tables with:

```python
Base.metadata.create_all(bind=engine)
```

**Problem:** `create_all` only creates tables that **don't exist yet**. It **never modifies** existing tables.

So if you:
- Add a column (`index=True` on `owner_id`)
- Rename a column
- Change a type from `String` to `Text`

...`create_all` does **nothing**. Your database is stuck with the old schema.

**SQLAlchemy does NOT provide migration.** It's an ORM — it maps Python classes to tables. It doesn't track or apply schema changes over time.

**Alembic** is the migration tool built by the same author (Mike Bayer). Think of it as **git for your database schema** — it generates versioned migration scripts and applies them in order.

| Tool | Role |
|---|---|
| SQLAlchemy | Defines models, runs queries (the ORM) |
| Alembic | Tracks and applies schema changes over time (the migrator) |

---

### Phase 1: Install and Initialize Alembic

```bash
# Install alembic
uv pip install alembic

# Initialize — creates alembic/ folder and alembic.ini config
alembic init alembic
```

This creates:

```
alembic.ini          ← config file (DB URL goes here)
alembic/
  env.py             ← migration environment (connects to DB, knows your models)
  script.py.mako     ← template for new migration files
  versions/          ← migration scripts live here (like git commits)
```

---

### Phase 2: Configure Alembic to Use Your Database

**Step 1** — Set the database URL in `alembic.ini`:

Find this line:
```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Change it to:
```ini
sqlalchemy.url = sqlite:///./graphql_todos.db
```

> This must match the `DATABASE_URL` in `app/database.py`.

**Step 2** — Tell Alembic about your models by editing `alembic/env.py`:

Find:
```python
target_metadata = None
```

Replace with:
```python
from app.database import Base
from app import models  # force SQLAlchemy to register all models

target_metadata = Base.metadata
```

> **Why import models?** SQLAlchemy only knows about a model *after* Python executes its class definition. Without this import, `Base.metadata` would be empty and Alembic wouldn't see any tables.

---

### Phase 3: Generate Your First Migration

```bash
# Auto-generate a migration by comparing models vs actual DB
alembic revision --autogenerate -m "add index on todo owner_id"
```

Alembic compares:
- **What your models say** (Python classes with `Column`, `index=True`, etc.)
- **What the database actually has** (inspects the live schema)

It generates a file in `alembic/versions/` like:

```python
"""add index on todo owner_id"""

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = None  # first migration, no parent

from alembic import op
import sqlalchemy as sa

def upgrade():
    # What to do when migrating forward
    op.create_index('ix_todos_owner_id', 'todos', ['owner_id'])

def downgrade():
    # What to do when rolling back
    op.drop_index('ix_todos_owner_id', table_name='todos')
```

> **Always review the generated file.** Autogenerate is good but not perfect — it may miss renames (sees drop + add instead) or miss some changes entirely.

---

### Phase 4: Apply the Migration

```bash
# Apply all pending migrations
alembic upgrade head
```

- `head` means "latest version"
- Alembic records which migrations have been applied in an `alembic_version` table in your DB
- It only runs migrations that haven't been applied yet

Other useful commands:

```bash
# See current migration version
alembic current

# See migration history
alembic history

# Rollback the last migration
alembic downgrade -1

# Rollback to the very beginning
alembic downgrade base

# See what SQL would run (without executing)
alembic upgrade head --sql
```

---

### Phase 5: Update main.py

Once you use Alembic, **remove** `create_all` from `main.py`:

```python
# REMOVE this line — Alembic manages the schema now
# Base.metadata.create_all(bind=engine)
```

From now on, the workflow is:

1. Change your model in `models.py`
2. Run `alembic revision --autogenerate -m "describe the change"`
3. Review the generated migration file
4. Run `alembic upgrade head`

> **Think of it like git:** you don't manually edit files on the server. You commit changes and push. Same idea — you don't manually ALTER tables. You generate a migration and apply it.

---

### Phase 6: Common Migration Operations

Here are operations you'll use often. Type these in a migration's `upgrade()` function:

```python
from alembic import op
import sqlalchemy as sa

# Add a column
op.add_column('todos', sa.Column('priority', sa.Integer, default=0))

# Drop a column
op.drop_column('todos', 'priority')

# Rename a column
op.alter_column('todos', 'title', new_column_name='name')

# Create an index
op.create_index('ix_todos_owner_id', 'todos', ['owner_id'])

# Drop an index
op.drop_index('ix_todos_owner_id', table_name='todos')

# Create a new table
op.create_table(
    'tags',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String, nullable=False),
)

# Drop a table
op.drop_table('tags')
```

> **SQLite limitation:** SQLite doesn't support `ALTER TABLE DROP COLUMN` (before version 3.35) or `ALTER TABLE RENAME COLUMN` (before 3.25). Alembic handles this with "batch mode" — it recreates the table behind the scenes. You may need `with op.batch_alter_table('todos') as batch_op:` for some operations on SQLite.

---

### Phase 7: The Mental Model

```
models.py              alembic revision             alembic upgrade head
(Python classes)   →   --autogenerate          →    (changes the actual DB)
                       (generates migration file)

                          ↕ like git diff               ↕ like git push
```

| Concept | Git Analogy |
|---|---|
| `alembic revision` | `git commit` — snapshot a change |
| `alembic upgrade head` | `git push` — apply changes |
| `alembic downgrade -1` | `git revert` — undo last change |
| `alembic history` | `git log` — see all migrations |
| `alembic current` | `git status` — where are we now? |
| `alembic_version` table | like `.git/HEAD` — tracks current position |

**What you learned:**

| Topic | Key Takeaway |
|---|---|
| SQLAlchemy vs Alembic | SQLAlchemy = ORM (defines schema). Alembic = migrator (evolves schema over time). |
| `create_all` limitation | Only creates new tables. Never alters existing ones. |
| Autogenerate | Alembic diffs your models against the live DB to generate migration scripts. |
| Migration file | Has `upgrade()` and `downgrade()` — forward and rollback. Always review it. |
| `alembic_version` table | Tracks which migrations have been applied. Like a pointer to current schema version. |
| SQLite batch mode | SQLite has limited ALTER support. Alembic's batch mode works around it by recreating tables. |

---

### Phase 8: How Alembic Tracks Migrations Per Database

Alembic creates an `alembic_version` table **inside each database** it manages. This table has one row with one column — the current revision ID:

```sql
-- Connect to any of your databases and run:
SELECT * FROM alembic_version;

-- Result:
-- version_num
-- ----------------
-- a1b2c3d4e5f6
```

Each database is **independent**. Dev might be on the latest migration. Prod might be 3 migrations behind. Alembic doesn't know or care about the others — it only looks at the `alembic_version` in the database it's connected to.

---

### Phase 9: Multi-Environment Setup (Dev / QA / Prod)

The problem: `alembic.ini` has one hardcoded `sqlalchemy.url`. You don't want to edit the file every time you switch environments, and you definitely don't want prod credentials in a config file committed to git.

**Solution: Use an environment variable.**

**Step 1** — In `alembic.ini`, remove or comment out the hardcoded URL:

```ini
# sqlalchemy.url = sqlite:///./graphql_todos.db   ← comment this out
```

**Step 2** — In `alembic/env.py`, read the URL from an environment variable:

```python
import os
from app.database import Base
from app import models

target_metadata = Base.metadata

def run_migrations_online():
    # Read DATABASE_URL from environment, fall back to local SQLite
    url = os.environ.get("DATABASE_URL", "sqlite:///./graphql_todos.db")

    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
```

**Step 3** — Now you target any environment by setting the variable:

```bash
# Local development (SQLite)
alembic upgrade head

# Dev (RDS Postgres)
DATABASE_URL="postgresql://user:pass@dev-rds.amazonaws.com:5432/myapp" alembic upgrade head

# QA
DATABASE_URL="postgresql://user:pass@qa-rds.amazonaws.com:5432/myapp" alembic upgrade head

# Prod
DATABASE_URL="postgresql://user:pass@prod-rds.amazonaws.com:5432/myapp" alembic upgrade head
```

> **In practice**, you'd use AWS Secrets Manager or SSM Parameter Store for the credentials, not inline passwords. Your CI/CD pipeline (e.g., GitHub Actions, CodePipeline) would pull the secret and set `DATABASE_URL` before running `alembic upgrade head`.

**Step 4** — Check where each environment is at:

```bash
# What migration is dev on?
DATABASE_URL="postgresql://..." alembic current

# What migrations are pending on prod?
DATABASE_URL="postgresql://..." alembic history --indicate-current
```

**The full picture:**

```
alembic/versions/           ← migration files live in your git repo (shared)
  001_create_tables.py         same code deploys to all environments
  002_add_owner_id_index.py
  003_add_priority_column.py

dev DB                      qa DB                       prod DB
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ alembic_version  │        │ alembic_version  │        │ alembic_version  │
│ = 003 (latest)   │        │ = 002            │        │ = 001            │
└──────────────────┘        └──────────────────┘        └──────────────────┘
       ↑                           ↑                           ↑
  alembic upgrade head        needs 003                  needs 002, 003
  (already up to date)
```

| Concept | Key Takeaway |
|---|---|
| `alembic_version` table | Created inside each database. One row tracking current revision. |
| Independent environments | Each DB tracks its own state. Alembic only sees the DB it connects to. |
| `DATABASE_URL` env var | Point Alembic at different databases without editing config files. |
| Same migration files | The `alembic/versions/` folder is in git — shared across all environments. |
| CI/CD integration | Pipeline sets `DATABASE_URL` from secrets, runs `alembic upgrade head` on deploy. |

---

### Phase 10: Pulling Credentials from AWS Secrets Manager / Parameter Store

In Phase 9, we used `DATABASE_URL` as an environment variable. That works locally and in simple CI/CD setups. But in production on AWS, you don't want credentials sitting in env vars, `.env` files, or ECS task definitions in plain text. Instead, you pull them at runtime from AWS-managed secret stores.

**Two options:**

| Service | Best For | Auto-Rotation | Cost |
|---|---|---|---|
| Secrets Manager | Database credentials, API keys | Yes (built-in for RDS) | ~$0.40/secret/month |
| Parameter Store (SSM) | Config values, non-secret settings | No (manual) | Free for standard params |

> **Rule of thumb:** Use Secrets Manager for anything that's a password or key. Use Parameter Store for everything else (feature flags, endpoint URLs, etc.).

---

#### Option A: Secrets Manager

**How it works:** You store the DB credentials as a JSON blob in Secrets Manager. Your code fetches it at startup and builds the connection URL.

**Step 1** — Create the secret in AWS (one-time setup per environment):

```bash
# Using AWS CLI
aws secretsmanager create-secret \
  --name "myapp/dev/database" \
  --secret-string '{
    "engine": "postgresql",
    "host": "dev-rds.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "dbname": "myapp",
    "username": "admin",
    "password": "super-secret-password"
  }'

# Same structure for qa and prod, different secret names:
# myapp/qa/database
# myapp/prod/database
```

> **Naming convention:** `{app}/{environment}/{purpose}` keeps things organized.

**Step 2** — Create a helper to fetch and build the URL:

**`app/aws_secrets.py`**:

```python
import json
import boto3

def get_database_url_from_secrets(secret_name: str, region: str = "us-east-1") -> str:
    """
    Fetch DB credentials from AWS Secrets Manager and build a SQLAlchemy URL.

    The secret is a JSON blob like:
    {
      "engine": "postgresql",
      "host": "...",
      "port": 5432,
      "dbname": "...",
      "username": "...",
      "password": "..."
    }
    """
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])

    return (
        f"{secret['engine']}://{secret['username']}:{secret['password']}"
        f"@{secret['host']}:{secret['port']}/{secret['dbname']}"
    )
```

> **What's happening:** `boto3` is the AWS SDK for Python. It calls the Secrets Manager API, which returns the JSON blob. We parse it and build a `postgresql://user:pass@host:port/db` URL that SQLAlchemy understands.

**Step 3** — Use it in `alembic/env.py`:

```python
import os
from app.database import Base
from app import models

target_metadata = Base.metadata

def get_url():
    """Decide where to get the database URL from."""
    # If DATABASE_URL is set (local dev, simple CI), use it directly
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    # Otherwise, fetch from Secrets Manager (deployed environments)
    secret_name = os.environ.get("DB_SECRET_NAME", "myapp/dev/database")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    from app.aws_secrets import get_database_url_from_secrets
    return get_database_url_from_secrets(secret_name, aws_region)

def run_migrations_online():
    url = get_url()
    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
```

> **The logic:** If `DATABASE_URL` is set (local dev with `.env`), use it. Otherwise, fall back to Secrets Manager. This means the same code works everywhere — local SQLite, CI with env vars, and deployed environments with Secrets Manager.

**Step 4** — Running migrations per environment:

```bash
# Local — uses .env file (DATABASE_URL=sqlite:///...)
alembic upgrade head

# Dev on AWS — fetches from Secrets Manager
DB_SECRET_NAME="myapp/dev/database" alembic upgrade head

# Prod on AWS
DB_SECRET_NAME="myapp/prod/database" alembic upgrade head
```

---

#### Option B: Parameter Store (SSM)

Simpler approach — store the full URL as a single parameter instead of a JSON blob.

**Step 1** — Create the parameter:

```bash
# SecureString encrypts the value with KMS
aws ssm put-parameter \
  --name "/myapp/dev/database_url" \
  --type "SecureString" \
  --value "postgresql://admin:super-secret@dev-rds.us-east-1.rds.amazonaws.com:5432/myapp"
```

**Step 2** — Fetch it in Python:

```python
import boto3

def get_database_url_from_ssm(param_name: str, region: str = "us-east-1") -> str:
    """Fetch DATABASE_URL from AWS SSM Parameter Store."""
    client = boto3.client("ssm", region_name=region)
    response = client.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]
```

> **`WithDecryption=True`** tells SSM to decrypt the SecureString before returning it. Without this, you'd get the encrypted blob.

---

#### Which one should you pick?

| Scenario | Use This |
|---|---|
| RDS credentials that should auto-rotate | Secrets Manager (has built-in RDS rotation) |
| Simple key-value config | Parameter Store (free, simpler) |
| Need to store a structured JSON blob | Secrets Manager |
| Budget-conscious, don't need rotation | Parameter Store with SecureString |

> **In real teams**, it's common to use **both**: Secrets Manager for the database password (with auto-rotation enabled for RDS), and Parameter Store for everything else (feature flags, endpoint URLs, non-secret config).

---

#### IAM Permissions

Your ECS task (or the machine running Alembic) needs permission to read the secrets. This is an IAM policy attached to the ECS task role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789:secret:myapp/*"
    },
    {
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:us-east-1:123456789:parameter/myapp/*"
    }
  ]
}
```

> **Principle of least privilege:** The wildcard `myapp/*` means the task can only read secrets for this app. It can't read secrets for other apps. In production, you'd scope this even tighter — e.g., `myapp/prod/*` for the prod task role.

---

#### How It Fits Together in CI/CD

```
Developer pushes code
        ↓
CI/CD pipeline (GitHub Actions / CodePipeline)
        ↓
┌──────────────────────────────────────────────────┐
│  1. Build Docker image                           │
│  2. Push to ECR                                  │
│  3. Run: DB_SECRET_NAME="myapp/prod/database"    │
│         alembic upgrade head                     │
│     (fetches creds from Secrets Manager at       │
│      runtime — no secrets in the pipeline)       │
│  4. Deploy new ECS task definition               │
└──────────────────────────────────────────────────┘
        ↓
ECS task starts
        ↓
App calls get_database_url_from_secrets()
        ↓
Connects to RDS with fresh credentials
```

> **Key point:** Secrets never appear in your code, Docker image, env files, or CI/CD logs. They exist only in Secrets Manager and are fetched at runtime by code that has the right IAM permissions.

**What you learned:**

| Topic | Key Takeaway |
|---|---|
| Secrets Manager | Store structured secrets (JSON). Supports auto-rotation for RDS. ~$0.40/secret/month. |
| Parameter Store (SSM) | Store simple key-value config. SecureString encrypts with KMS. Free tier available. |
| Runtime fetching | Code calls AWS API at startup — secrets never touch disk, env files, or git. |
| IAM permissions | ECS task role needs explicit `GetSecretValue` / `GetParameter` permission. Scope it tight. |
| Fallback pattern | Check `DATABASE_URL` env var first (local dev), then fall back to Secrets Manager (deployed). |
| CI/CD integration | Pipeline passes `DB_SECRET_NAME`, Alembic fetches credentials itself. No secrets in logs. |
