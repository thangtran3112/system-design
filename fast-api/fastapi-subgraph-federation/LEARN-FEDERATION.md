# GraphQL Federation with Strawberry — Learning Guide

Split your monolithic GraphQL API into independent subgraphs that compose into one unified schema.
**Builds on the Todo + Users API from LEARN.md.** You type everything yourself — copy from snippets, edit, and learn by doing.

---

## Part 1: Understanding Federation

---

### Phase 1: The Problem — Monolithic GraphQL at Scale

Right now, your entire GraphQL API lives in one service:

```
app/
├── resolvers.py      ← ALL queries and mutations (todos + users)
├── schemas.py        ← ALL types (TodoType, UserType, inputs)
├── models.py         ← ALL database models
└── main.py           ← one server, one schema, one deploy
```

This works great for a small app. But imagine your app grows:

- **Notifications** — a new team builds email/push alerts
- **Comments** — another team adds comments on todos
- **Tags** — yet another team adds tagging/categorization
- **Activity Feed** — an analytics team tracks user actions

Now you have one `resolvers.py` with 50+ resolvers, owned by 5 teams, deployed as one unit. Every change risks breaking someone else's work. Every deploy requires coordinating across teams.

| Problem with Monolithic GraphQL | How Federation Solves It |
|---|---|
| One giant schema file owned by everyone | Each team owns their own subgraph (independent schema) |
| Single deploy — one bad change breaks everything | Independent deploys per subgraph |
| One team blocks another's release | Teams release on their own schedule |
| Single point of failure | One subgraph going down doesn't crash the others |
| Merge conflicts in shared resolver files | Each subgraph is a separate codebase |

> **When do you NOT need federation?** If you're a small team (1-3 people) with a simple domain, keep the monolith. Federation adds operational complexity. Use it when you have **multiple teams** or **multiple domains** that need to evolve independently.

---

### Phase 2: Core Concepts

Before writing code, learn the vocabulary:

```
Subgraph           — An independent GraphQL service that owns a slice of the schema.
                     Example: "Users subgraph" owns User type and user queries.

Supergraph         — The combined schema from all subgraphs. What clients see.
                     Clients don't know subgraphs exist — they query one unified API.

Router (Gateway)   — Receives client queries, splits them across subgraphs, merges responses.
                     It is NOT a GraphQL server — it has no resolvers. It's a query planner.

Entity             — A type that can be resolved across multiple subgraphs.
                     Example: User is defined in Users subgraph but referenced in Todos subgraph.

@key               — Marks a type as an entity and defines its lookup key.
                     Like a primary key — "you can find any User by their id."

resolve_reference  — A function that resolves an entity by its @key.
                     The router calls this when another subgraph references the entity.

_entities          — A special query the router uses to fetch entities from a subgraph.
                     You never call this yourself — the router does it automatically.

_service           — A special query that returns the subgraph's SDL (schema definition).
                     Used during composition to build the supergraph schema.
```

**How a federated query flows:**

```
                          ┌─────────────────────┐
                          │      Client          │
                          │                      │
                          │  query {             │
                          │    todos {           │
                          │      title           │
                          │      owner { name }  │
                          │    }                 │
                          │  }                   │
                          └──────────┬───────────┘
                                     │
                              1. Send query
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │      Router          │
                          │   (port 4000)        │
                          │                      │
                          │  Plans: "todos" goes │
                          │  to Todos subgraph,  │
                          │  "owner.name" needs  │
                          │  Users subgraph      │
                          └───┬─────────────┬────┘
                              │             │
                 2. fetch todos        3. fetch User(id=5)
                              │             │
                              ▼             ▼
                ┌──────────────┐   ┌──────────────┐
                │    Todos     │   │    Users     │
                │  Subgraph    │   │  Subgraph    │
                │ (port 8002)  │   │ (port 8001)  │
                │              │   │              │
                │ returns:     │   │ returns:     │
                │ { title,     │   │ { name,      │
                │   owner:     │   │   email }    │
                │   { id: 5 }} │   │              │
                └──────────────┘   └──────────────┘
                              │             │
                              └──────┬──────┘
                                     │
                          4. Merge responses
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │      Client          │
                          │                      │
                          │  { todos: [{         │
                          │    title: "Buy milk", │
                          │    owner: {           │
                          │      name: "Alice"    │
                          │    }                  │
                          │  }]}                  │
                          └─────────────────────┘
```

> **The key insight:** The Todos subgraph returns `owner: { id: 5 }` — just the key. It doesn't know the user's name or email. The router sees this is an entity reference, calls the Users subgraph to resolve `User(id=5)`, and merges the full data before sending it back to the client.

---

### Phase 3: Planning the Split

Let's map your current monolithic app to two subgraphs:

| Subgraph | Owns | Types | Resolvers |
|---|---|---|---|
| **Users** (port 8001) | User identity, profiles | User (entity) | `users`, `user(id)`, `createUser` |
| **Todos** (port 8002) | Todo CRUD | Todo + references User | `todos`, `todo(id)`, `createTodo`, `updateTodo`, `deleteTodo` |

**The key decision:** `User` is the **entity** — both subgraphs need it. The Users subgraph **owns** User (defines all fields). The Todos subgraph **references** User (only knows `id`, the router fills in the rest).

**New folder structure:**

```
fastapi-graphql-oauth/
├── app/                        ← your existing monolith (keep for reference)
├── services/
│   ├── users/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py        ← FastAPI + federation schema, port 8001
│   │   │   ├── models.py      ← User model only
│   │   │   ├── database.py    ← DB connection
│   │   │   └── schema.py      ← UserType as entity + resolvers
│   │   └── requirements.txt
│   └── todos/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py        ← FastAPI + federation schema, port 8002
│       │   ├── models.py      ← Todo model only
│       │   ├── database.py    ← DB connection
│       │   └── schema.py      ← TodoType + User stub + resolvers
│       └── requirements.txt
├── router/
│   └── supergraph.yaml        ← Apollo Router config
└── docker-compose.yml          ← run everything together
```

Set this up:

```bash
# Create the folder structure
mkdir -p services/users/app services/todos/app router

touch services/users/app/__init__.py services/users/app/main.py
touch services/users/app/models.py services/users/app/database.py
touch services/users/app/schema.py services/users/requirements.txt

touch services/todos/app/__init__.py services/todos/app/main.py
touch services/todos/app/models.py services/todos/app/database.py
touch services/todos/app/schema.py services/todos/requirements.txt
```

---

## Part 2: Building the Users Subgraph

---

### Phase 4: Users Subgraph — Entity with @key

The Users subgraph **owns** the User type. It defines all User fields and tells the router: "I am the authority on Users. You can look up any User by their `id`."

Install the federation dependency:

```bash
cd services/users
uv pip install fastapi uvicorn sqlalchemy strawberry-graphql[federation]
```

**`services/users/app/database.py`** — Same pattern as your monolith, separate DB:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Each subgraph can have its own DB, or share one — your choice.
# For learning, we use a separate SQLite file per subgraph.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./users.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
```

**`services/users/app/models.py`** — Only the User model:

```python
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    picture = Column(String, nullable=True)
    provider = Column(String, default="local")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

> **Notice:** No `todos = relationship(...)` here. The Users subgraph doesn't know about todos. That's the Todos subgraph's job.

**`services/users/app/schema.py`** — The federated schema with entity:

```python
import strawberry
from typing import Optional
from app.database import SessionLocal
from app.models import User

# @strawberry.federation.type(keys=["id"]) tells the router:
# "User is an entity. You can look up any User by their id."
@strawberry.federation.type(keys=["id"])
class UserType:
    id: int
    email: str
    name: str
    picture: Optional[str]
    provider: str

    @classmethod
    def resolve_reference(cls, id: int) -> "UserType":
        """
        Called by the router when another subgraph references User(id=X).
        The router sends: { __typename: "User", id: 5 }
        This function returns the full User data.
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == id).first()
            if user is None:
                return None
            return UserType(
                id=user.id,
                email=user.email,
                name=user.name,
                picture=user.picture,
                provider=user.provider,
            )
        finally:
            db.close()

@strawberry.input
class CreateUserInput:
    email: str
    name: str
    picture: Optional[str] = None
    provider: str = "local"

@strawberry.type
class Query:
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

    @strawberry.field
    def user(self, id: int) -> Optional[UserType]:
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.id == id).first()
            if u is None:
                return None
            return UserType(
                id=u.id, email=u.email, name=u.name,
                picture=u.picture, provider=u.provider,
            )
        finally:
            db.close()

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, input: CreateUserInput) -> UserType:
        db = SessionLocal()
        try:
            user = User(
                email=input.email,
                name=input.name,
                picture=input.picture,
                provider=input.provider,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return UserType(
                id=user.id, email=user.email, name=user.name,
                picture=user.picture, provider=user.provider,
            )
        finally:
            db.close()
```

> **The magic is `resolve_reference`.** When the Todos subgraph returns `owner: { id: 5 }`, the router calls this function with `id=5`. It's how entities are "stitched" across subgraphs.

**`services/users/app/main.py`** — Mount the federated schema:

```python
from fastapi import FastAPI
import strawberry
from strawberry.fastapi import GraphQLRouter
from app.database import engine, Base
from app.schema import Query, Mutation

# Create tables
Base.metadata.create_all(bind=engine)

# KEY DIFFERENCE: use strawberry.federation.Schema instead of strawberry.Schema
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    enable_federation_2=True,  # use Federation v2 (latest)
)

graphql_app = GraphQLRouter(schema)

app = FastAPI(title="Users Subgraph")
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok", "subgraph": "users"}
```

> **Key difference from the monolith:**
> ```
> Monolith:    schema = strawberry.Schema(query=Query, mutation=Mutation)
> Federated:   schema = strawberry.federation.Schema(query=Query, mutation=Mutation, enable_federation_2=True)
> ```
> That one change makes the subgraph expose `_service` and `_entities` queries that the router needs.

Run it:

```bash
cd services/users
uvicorn app.main:app --port 8001 --reload
```

Open **http://localhost:8001/graphql** — you get GraphiQL, just like the monolith.

---

### Phase 5: Test the Users Subgraph Standalone

Each subgraph is a **fully functional GraphQL API** on its own. Test it:

**Create a user:**

```graphql
mutation {
  createUser(input: { email: "alice@example.com", name: "Alice" }) {
    id
    email
    name
  }
}
```

**Query all users:**

```graphql
{
  users {
    id
    email
    name
    provider
  }
}
```

**Check the federated SDL** — this is what the router reads during composition:

```graphql
{
  _service {
    sdl
  }
}
```

You should see something like:

```graphql
type User @key(fields: "id") {
  id: Int!
  email: String!
  name: String!
  picture: String
  provider: String!
}

type Query {
  users: [User!]!
  user(id: Int!): User
}
```

> **`@key(fields: "id")`** in the SDL — this is the federation directive that came from `@strawberry.federation.type(keys=["id"])`. The router uses this to know how to look up Users.

---

## Part 3: Building the Todos Subgraph

---

### Phase 6: Todos Subgraph — Referencing an Entity

The Todos subgraph **owns** the Todo type but **references** the User type. It doesn't define User's fields — it just says "the owner is User(id=X)" and trusts the router to fill in the rest.

```bash
cd services/todos
uv pip install fastapi uvicorn sqlalchemy strawberry-graphql[federation]
```

**`services/todos/app/database.py`** — Same pattern:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./todos.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
```

**`services/todos/app/models.py`** — Only the Todo model:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone
from app.database import Base

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    completed = Column(Boolean, default=False)
    owner_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

> **Notice:** `owner_id` is just an integer column — no `ForeignKey("users.id")`. This subgraph has its own database. It stores the owner's ID but doesn't have the users table. The relationship lives at the GraphQL level, not the database level.

**`services/todos/app/schema.py`** — Todo type + User stub entity:

```python
import strawberry
from typing import Optional
from app.database import SessionLocal
from app.models import Todo

# User STUB — this is NOT the full User type.
# We only define the @key field (id). The router fills in name, email, etc.
# from the Users subgraph.
@strawberry.federation.type(keys=["id"])
class UserType:
    id: int

# Todo is owned by this subgraph — define all fields here.
@strawberry.federation.type
class TodoType:
    id: int
    title: str
    description: str
    completed: bool
    owner: UserType  # returns UserType(id=X) — the router resolves the rest

@strawberry.input
class CreateTodoInput:
    title: str
    owner_id: int
    description: str = ""

@strawberry.input
class UpdateTodoInput:
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

def db_todo_to_type(todo: Todo) -> TodoType:
    return TodoType(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        owner=UserType(id=todo.owner_id),  # just the ID — router does the rest
    )

@strawberry.type
class Query:
    @strawberry.field
    def todos(self, owner_id: Optional[int] = None) -> list[TodoType]:
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
        db = SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            return db_todo_to_type(todo) if todo else None
        finally:
            db.close()

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_todo(self, input: CreateTodoInput) -> TodoType:
        db = SessionLocal()
        try:
            todo = Todo(
                title=input.title,
                description=input.description,
                owner_id=input.owner_id,
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
            if todo is None:
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
            if todo is None:
                return False
            db.delete(todo)
            db.commit()
            return True
        finally:
            db.close()
```

> **This is the magic of federation.** The Todos subgraph returns `owner: UserType(id=5)` — just the key. It has no idea what the user's name or email is. The router sees this is an entity reference, calls the Users subgraph's `resolve_reference` with `id=5`, gets back the full User data, and merges it into the response.

**`services/todos/app/main.py`** — Mount the federated schema:

```python
from fastapi import FastAPI
import strawberry
from strawberry.fastapi import GraphQLRouter
from app.database import engine, Base
from app.schema import Query, Mutation

Base.metadata.create_all(bind=engine)

schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    enable_federation_2=True,
)

graphql_app = GraphQLRouter(schema)

app = FastAPI(title="Todos Subgraph")
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok", "subgraph": "todos"}
```

Run it:

```bash
cd services/todos
uvicorn app.main:app --port 8002 --reload
```

---

### Phase 7: Test the Todos Subgraph Standalone

Open **http://localhost:8002/graphql** and try:

**Create a todo** (use an owner_id that exists in the Users subgraph):

```graphql
mutation {
  createTodo(input: { title: "Buy milk", ownerId: 1 }) {
    id
    title
    owner {
      id
    }
  }
}
```

**Query todos:**

```graphql
{
  todos {
    id
    title
    owner {
      id
    }
  }
}
```

**Notice:** `owner` only returns `id`. If you try to query `owner { name }`, it will fail — this subgraph doesn't know about `name`. That's proof it only knows what it owns.

**Check the federated SDL:**

```graphql
{
  _service {
    sdl
  }
}
```

You should see `User @key(fields: "id")` with only the `id` field, and `Todo` with all its fields.

---

## Part 4: The Router (Gateway)

---

### Phase 8: Apollo Router — Composing the Supergraph

The router is **not** a GraphQL server. It has no resolvers, no database, no business logic. It's a **query planner** — it receives a client query, figures out which subgraphs to call, executes the calls, and merges the results.

**Option A: Using Apollo Router (recommended, Rust binary)**

```bash
# Install Apollo's CLI tool (rover) for schema composition
curl -sSL https://rover.apollo.dev/nix/latest | sh

# Install Apollo Router
curl -sSL https://router.apollo.dev/download/nix/latest | sh
```

**Option B: Using Docker (simpler)**

```bash
# We'll use this in the Docker Compose setup later
# For now, install rover for schema composition
curl -sSL https://rover.apollo.dev/nix/latest | sh
```

**Step 1** — Create the supergraph config:

**`router/supergraph.yaml`**:

```yaml
federation_version: =2.0.0
subgraphs:
  users:
    routing_url: http://localhost:8001/graphql
    schema:
      subgraph_url: http://localhost:8001/graphql
  todos:
    routing_url: http://localhost:8002/graphql
    schema:
      subgraph_url: http://localhost:8002/graphql
```

**Step 2** — Compose the supergraph schema:

> Make sure both subgraphs are running (port 8001 and 8002) before running this.

```bash
# Compose: fetches SDL from each subgraph, validates, and merges
rover supergraph compose --config router/supergraph.yaml > router/supergraph.graphql
```

> **What just happened?** `rover` called `_service { sdl }` on each subgraph, validated that the schemas are compatible (no conflicts, entities resolve correctly), and produced a single `supergraph.graphql` file — the combined schema.

**Step 3** — Start the router:

```bash
./router --supergraph router/supergraph.graphql --dev
```

The router starts on **http://localhost:4000**.

> **`--dev` flag** enables: sandbox UI (like GraphiQL), introspection, and detailed error messages. Don't use `--dev` in production.

---

### Phase 9: Query the Supergraph

Open **http://localhost:4000** and run:

```graphql
{
  todos {
    id
    title
    completed
    owner {
      id
      name
      email
    }
  }
}
```

**This query spans two subgraphs.** The client doesn't know — it just queries one endpoint.

Here's what happens behind the scenes:

```
Step 1: Router receives the query

Step 2: Router builds a query plan:
        "todos" field        → send to Todos subgraph
        "owner.name/email"   → needs Users subgraph (entity lookup)

Step 3: Router calls Todos subgraph:
        query { todos { id title completed owner { id } } }

        Todos returns:
        [{ id: 1, title: "Buy milk", completed: false, owner: { id: 5 } }]

Step 4: Router sees owner is a User entity (has @key).
        Calls Users subgraph:
        query {
          _entities(representations: [{ __typename: "User", id: 5 }]) {
            ... on User { name email }
          }
        }

        Users returns:
        [{ name: "Alice", email: "alice@example.com" }]

Step 5: Router merges:
        [{ id: 1, title: "Buy milk", completed: false,
           owner: { id: 5, name: "Alice", email: "alice@example.com" } }]

Step 6: Router sends merged response to client.
```

> **The client sent ONE query to ONE endpoint.** The router handled the orchestration across two subgraphs. This is why federation is powerful — the client's experience is identical to a monolith.

---

## Part 5: Advanced Federation Patterns

---

### Phase 10: Extending Types Across Subgraphs

Right now, you can query `todos { owner { name } }` — starting from todos, navigating to the owner. But what about the reverse? You might want:

```graphql
{
  user(id: 1) {
    name
    todos {
      title
      completed
    }
  }
}
```

The `todos` field on User doesn't exist in the Users subgraph — it doesn't know about todos. But the Todos subgraph can **contribute** this field to the User entity.

**Update `services/todos/app/schema.py`** — add a `todos` field to the User stub:

```python
@strawberry.federation.type(keys=["id"])
class UserType:
    id: int

    @strawberry.field
    def todos(self, info: strawberry.types.Info) -> list["TodoType"]:
        """
        This field is CONTRIBUTED by the Todos subgraph to the User entity.
        The Users subgraph doesn't know about this field.
        The router knows to call this subgraph when someone queries user.todos.
        """
        db = SessionLocal()
        try:
            todos = db.query(Todo).filter(Todo.owner_id == self.id).all()
            return [db_todo_to_type(t) for t in todos]
        finally:
            db.close()
```

> **What changed?** The User stub in the Todos subgraph now has a `todos` field. The Todos subgraph is saying: "If anyone asks for `User.todos`, send it to me — I know how to resolve it given a User's `id`."

After this change, recompose the supergraph:

```bash
rover supergraph compose --config router/supergraph.yaml > router/supergraph.graphql
```

Restart the router, and the query above now works — even though the Users subgraph has no idea that `todos` exists on User.

---

### Phase 11: Entity References and the _entities Query

Let's look under the hood at what the router actually sends to subgraphs.

The `_entities` query is a **special federated query** that every subgraph exposes automatically. The router uses it to resolve entity references.

**Test it manually** — go to **http://localhost:8001/graphql** (Users subgraph) and run:

```graphql
{
  _entities(representations: [{ __typename: "User", id: 1 }]) {
    ... on User {
      id
      name
      email
    }
  }
}
```

> **`representations`** is an array of "entity pointers" — each one has `__typename` (which entity) and the `@key` fields (how to find it). The router constructs these automatically from what subgraphs return.

**Batching:** If 10 todos are owned by 3 different users, the router batches:

```graphql
{
  _entities(representations: [
    { __typename: "User", id: 1 },
    { __typename: "User", id: 2 },
    { __typename: "User", id: 5 }
  ]) {
    ... on User { name email }
  }
}
```

One call to the Users subgraph for all 3 users — not 10 calls for 10 todos.

---

### Phase 12: Handling N+1 in Federation — DataLoaders

The router batches entity lookups into one `_entities` call. But inside `resolve_reference`, if you're not careful, you still get N queries to your database:

```python
# BAD: called once per entity in the batch — N database queries
@classmethod
def resolve_reference(cls, id: int) -> "UserType":
    db = SessionLocal()
    user = db.query(User).filter(User.id == id).first()  # 1 query per user
    ...
```

**Solution: Use a DataLoader** to batch database lookups.

**Update `services/users/app/schema.py`** — add a DataLoader:

```python
import strawberry
from strawberry.dataloader import DataLoader
from typing import Optional
from app.database import SessionLocal
from app.models import User

async def load_users(ids: list[int]) -> list[Optional["UserType"]]:
    """
    Batch function: receives ALL requested user IDs at once,
    makes ONE database query, returns results in the same order.
    """
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.id.in_(ids)).all()
        user_map = {u.id: u for u in users}
        return [
            UserType(
                id=u.id, email=u.email, name=u.name,
                picture=u.picture, provider=u.provider,
            ) if (u := user_map.get(uid)) else None
            for uid in ids
        ]
    finally:
        db.close()

# Create the loader
user_loader = DataLoader(load_fn=load_users)

@strawberry.federation.type(keys=["id"])
class UserType:
    id: int
    email: str
    name: str
    picture: Optional[str]
    provider: str

    @classmethod
    async def resolve_reference(cls, id: int) -> Optional["UserType"]:
        # Now uses the DataLoader — all resolve_reference calls in a batch
        # are collected and resolved with ONE database query
        return await user_loader.load(id)
```

**Before and after:**

```
Before (N queries):
  resolve_reference(id=1) → SELECT * FROM users WHERE id = 1
  resolve_reference(id=2) → SELECT * FROM users WHERE id = 2
  resolve_reference(id=5) → SELECT * FROM users WHERE id = 5

After (1 query):
  DataLoader collects [1, 2, 5]
  load_users([1, 2, 5]) → SELECT * FROM users WHERE id IN (1, 2, 5)
```

> **DataLoaders are a GraphQL pattern, not a federation-specific thing.** They batch and cache individual lookups into bulk queries. In federation, they're especially important because `resolve_reference` is called once per entity in a batch.

---

## Part 6: Running Everything Together

---

### Phase 13: Docker Compose for Local Development

Running three terminals with `uvicorn` gets tedious. Use Docker Compose to start everything at once.

**`services/users/Dockerfile`**:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`services/todos/Dockerfile`**:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> Both Dockerfiles use port 8000 internally — Docker Compose maps them to different external ports.

**`docker-compose.yml`** (project root):

```yaml
services:
  users:
    build: ./services/users
    ports:
      - "8001:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      retries: 3

  todos:
    build: ./services/todos
    ports:
      - "8002:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      retries: 3

  router:
    image: ghcr.io/apollographql/router:v2.0.0
    ports:
      - "4000:4000"
    volumes:
      - ./router/supergraph.graphql:/etc/config/supergraph.graphql
    command:
      - --supergraph
      - /etc/config/supergraph.graphql
      - --dev
    depends_on:
      users:
        condition: service_healthy
      todos:
        condition: service_healthy
```

Run everything:

```bash
# Compose the supergraph first (subgraphs must be running, or use pre-composed file)
docker compose up --build
```

Now:
- **http://localhost:8001/graphql** — Users subgraph directly
- **http://localhost:8002/graphql** — Todos subgraph directly
- **http://localhost:4000** — Router (what clients use)

---

### Phase 14: Testing Federated Schemas

| Test Type | What It Validates | How to Run |
|---|---|---|
| Unit | Single subgraph resolvers work in isolation | `pytest` with TestClient per subgraph |
| Composition | Subgraph schemas compose without conflicts | `rover supergraph compose` |
| Integration | End-to-end queries through router return correct data | `pytest` against router URL |
| Contract | One subgraph's changes don't break another | `rover subgraph check` |

**Unit test example** — `services/users/tests/test_schema.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_and_query_user():
    # Create
    response = client.post("/graphql", json={
        "query": """
            mutation {
                createUser(input: { email: "test@test.com", name: "Test" }) {
                    id
                    email
                }
            }
        """
    })
    data = response.json()["data"]["createUser"]
    assert data["email"] == "test@test.com"

    # Query
    response = client.post("/graphql", json={
        "query": "{ users { id email name } }"
    })
    users = response.json()["data"]["users"]
    assert len(users) >= 1
```

**Composition validation** — run this in CI before deploying:

```bash
# If this fails, the schemas are incompatible
rover supergraph compose --config router/supergraph.yaml > /dev/null
echo "Composition succeeded"
```

> **Run composition checks in CI.** If a team changes their subgraph in a way that breaks composition (e.g., removes an entity key), `rover supergraph compose` will fail — catching the issue before it reaches production.

---

## Part 7: Real-World Architecture

---

### Phase 15: Mapping to Microservice Architectures

Federation is GraphQL's answer to microservices. Here's how the concepts map:

| Microservice Concept | Federation Equivalent |
|---|---|
| Service boundary | Subgraph |
| API gateway (e.g., Kong, AWS ALB) | Apollo Router |
| Service-to-service REST call | Entity reference + `_entities` query |
| Shared data model / proto file | Entity with `@key` |
| Schema registry (for Protobuf/OpenAPI) | Apollo Schema Registry / `rover` |
| Independent deploy | Deploy one subgraph without touching others |
| Service discovery | Router config (`supergraph.yaml`) |
| Eventual consistency across services | Each subgraph owns its own data, references by key |

**When to add a new subgraph vs extend an existing one:**

| Scenario | Decision |
|---|---|
| New domain (e.g., Notifications) with its own DB | New subgraph |
| New field on an existing type (e.g., `User.avatarUrl`) | Extend the subgraph that owns User |
| Cross-cutting feature (e.g., analytics events on all types) | New subgraph that extends multiple entities |
| Small helper type used by one subgraph | Keep it in that subgraph — don't over-split |

**Production federation architecture:**

```
                          ┌──────────────┐
                          │   Clients    │
                          │ (web, mobile)│
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │     ALB      │
                          │ (AWS/Cloud)  │
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │Apollo Router │
                          │  (Fargate)   │
                          └──┬───┬───┬───┘
                             │   │   │
              ┌──────────────┘   │   └──────────────┐
              │                  │                   │
       ┌──────▼──────┐   ┌──────▼──────┐   ┌───────▼─────┐
       │   Users     │   │   Todos     │   │ Notifications│
       │  Subgraph   │   │  Subgraph   │   │  Subgraph    │
       │  (Fargate)  │   │  (Fargate)  │   │  (Fargate)   │
       └──────┬──────┘   └──────┬──────┘   └───────┬──────┘
              │                  │                   │
       ┌──────▼──────┐   ┌──────▼──────┐   ┌───────▼──────┐
       │  Users DB   │   │  Todos DB   │   │    SQS +     │
       │ (RDS Postgres)│ │ (RDS Postgres)│ │   DynamoDB   │
       └─────────────┘   └─────────────┘   └──────────────┘

       Team: Identity       Team: Product      Team: Engagement
```

> **Each team owns their subgraph end-to-end** — schema, resolvers, database, deployment. They can release independently as long as schema composition still passes. The router is the only shared infrastructure, and it's stateless — it just plans and proxies queries.

---

### Phase 16: Summary — What You Learned

| Topic | Key Takeaway |
|---|---|
| Federation problem | Monolithic GraphQL doesn't scale with multiple teams/domains. |
| Subgraph | Independent GraphQL service owning a slice of the schema. |
| Supergraph | The merged schema from all subgraphs — what clients see. |
| Entity + `@key` | Types that can be resolved across subgraph boundaries. Defined with `@strawberry.federation.type(keys=["id"])`. |
| `resolve_reference` | How a subgraph provides entity data when the router asks for it. |
| Router | Receives queries, plans execution across subgraphs, merges responses. Not a GraphQL server. |
| User stub | A subgraph that references an entity defines a stub with only `@key` fields. |
| Extending types | A subgraph can add fields to an entity it doesn't own (e.g., Todos adds `User.todos`). |
| `_entities` query | Special query the router sends to resolve entity references. Batches by default. |
| DataLoaders | Batch `resolve_reference` calls into one DB query. Prevents N+1 inside subgraphs. |
| Composition | `rover supergraph compose` validates and merges subgraph schemas. Run in CI. |
| Docker Compose | Run all subgraphs + router locally with one command. |
| Team ownership | Each team owns a subgraph end-to-end — schema, code, DB, deploy. |

**Next steps to explore:**

- Add a **Notifications** subgraph that extends Todo with a `notifications` field
- Add **authentication at the router layer** — pass JWT headers to subgraphs
- Deploy each subgraph as a **separate ECS Fargate service** (see Part 3 of LEARN.md)
- Set up **Apollo Schema Registry** for managed composition and change tracking

---

## Part 8: This Repo's Scaffold + uv Workflow

This folder already includes a working scaffold:

```
fastapi-subgraph-federation/
├── services/
│   ├── users/
│   │   ├── app/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── todos/
│       ├── app/
│       ├── requirements.txt
│       └── Dockerfile
├── router/
│   └── supergraph.yaml
├── scripts/
│   ├── setup_envs.sh
│   └── compose_supergraph.sh
└── docker-compose.yml
```

### Phase 17: Setup Python with uv

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create venv per subgraph:

```bash
cd /home/thangtran3112/workspace/system-design/fastapi-graphql-oauth/fastapi-subgraph-federation
uv venv services/users/.venv
uv venv services/todos/.venv
```

Install dependencies:

```bash
uv pip install --python services/users/.venv/bin/python -r services/users/requirements.txt
uv pip install --python services/todos/.venv/bin/python -r services/todos/requirements.txt
```

Or use helper script:

```bash
./scripts/setup_envs.sh
```

### Phase 18: Run all pieces

Terminal 1:

```bash
cd services/users
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

Terminal 2:

```bash
cd services/todos
source .venv/bin/activate
uvicorn app.main:app --reload --port 8002
```

Compose supergraph and run router:

```bash
cd /home/thangtran3112/workspace/system-design/fastapi-subgraph-federation
./scripts/compose_supergraph.sh
./router/router --supergraph router/supergraph.graphql --dev
```

### Phase 19: Verify with tests

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

Tests cover:

- subgraph health endpoints
- federated SDL exposure (`_service { sdl }`)
- end-to-end supergraph flow (`createUser` → `createTodo` → query owner fields via router)

---

## Part 9: Deploying Federation on EKS (Subgraphs + Supergraph)

Use this part as the Kubernetes/EKS learning path for this repo, modeled after:

- `simple-graphql-oauth/terraform-eks`
- `simple-graphql-oauth/k8s`

The difference is deployment topology: monolith deploys one GraphQL API, federation deploys three workloads (`users`, `todos`, `router`).

### Phase 20: EKS Infrastructure Plan (Terraform)

Create a new folder in this project:

```text
fastapi-subgraph-federation/
└── terraform-eks/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── terraform.tfvars.example
```

Start from the same pattern as `simple-graphql-oauth/terraform-eks`:

- VPC + 2 public subnets + 2 private subnets
- IGW + NAT Gateway
- EKS cluster + managed node group
- ECR repositories for container images

For federation, create separate ECR repos (recommended):

- `<project>-users`
- `<project>-todos`
- `<project>-router`

Suggested variable values:

```hcl
project_name       = "graphql-federation"
aws_region         = "us-east-1"
cluster_version    = "1.29"
node_instance_type = "t3.medium"
```

Terraform workflow:

```bash
cd terraform-eks
terraform init
terraform plan
terraform apply
```

Then configure kubectl (same as monolith flow):

```bash
aws eks update-kubeconfig --name <cluster-name> --region <aws-region>
kubectl get nodes
```

### Phase 21: Container Build and Push Strategy

Build and push three images:

- `services/users` image
- `services/todos` image
- `router` image that includes `supergraph.graphql`

Recommended release flow:

1. Run integration tests.
2. Compose supergraph via `./scripts/compose_supergraph.sh` in CI.
3. Build router artifact with the new `router/supergraph.graphql`.
4. Push all versioned images to ECR (`:<git-sha>` tags).
5. Update Kubernetes manifests to new immutable tags.

### Phase 22: Kubernetes Manifests Layout for Federation

Create a new Kubernetes folder for this project:

```text
fastapi-subgraph-federation/
└── k8s/
    ├── namespace.yaml
    ├── configmap.yaml
    ├── secrets.yaml
    ├── users-deployment.yaml
    ├── users-service.yaml
    ├── todos-deployment.yaml
    ├── todos-service.yaml
    ├── router-deployment.yaml
    ├── router-service.yaml
    └── ingress.yaml
```

Reuse monolith conventions from `simple-graphql-oauth/k8s`:

- Namespace isolation
- ConfigMap for non-sensitive values
- Secret for sensitive values
- Readiness/liveness probes
- ALB Ingress Controller annotations

Key federation-specific wiring:

- `users` and `todos` Services are `ClusterIP` (internal only).
- `router` Service is the only public entry point.
- Ingress sends `/` traffic to `router-service`.
- Router reads subgraph URLs via env vars or mounted config:
  - `http://users-service/graphql`
  - `http://todos-service/graphql`

### Phase 23: Deploy Order in EKS

Apply in this order:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

kubectl apply -f k8s/users-deployment.yaml
kubectl apply -f k8s/users-service.yaml
kubectl apply -f k8s/todos-deployment.yaml
kubectl apply -f k8s/todos-service.yaml

kubectl apply -f k8s/router-deployment.yaml
kubectl apply -f k8s/router-service.yaml
kubectl apply -f k8s/ingress.yaml
```

Verification checks:

```bash
kubectl get pods -n graphql-federation
kubectl get svc -n graphql-federation
kubectl get ingress -n graphql-federation
kubectl logs deploy/router -n graphql-federation
```

### Phase 24: Federated Health and Functional Validation

Validate layers in sequence:

1. Subgraph health:
   - `GET /health` on users and todos pods/services.
2. Subgraph GraphQL availability:
   - `_service { sdl }` query to each subgraph endpoint.
3. Router availability:
   - check router startup logs and `/:` endpoint.
4. End-to-end federation query through ingress/router:
   - `createUser` -> `createTodo` -> query `owner { id name email }`.

This mirrors your local test contract in `tests/test_supergraph_api.py`, but against EKS endpoint URLs.

### Phase 25: Rollout and Scaling Roadmap (EKS)

After baseline deploy works, apply progressive delivery:

- Add HPA for `users`, `todos`, and `router`.
- Use Argo Rollouts for:
  - canary on `router` (highest blast radius)
  - canary or blue/green on subgraphs
- Keep composition validation in CI before rollout:
  - `rover supergraph compose --config router/supergraph.yaml`

Recommended promotion sequence:

1. Deploy subgraph change (`users` or `todos`) with canary.
2. Compose and release matching router supergraph.
3. Promote router rollout after federated smoke tests pass.

> Practical rule: treat `router/supergraph.graphql` as a versioned release artifact. Subgraph and router deploys should be coordinated by composition checks, not manual guesswork.

---

## Part 10: CI/CD with GitHub Actions for dev, qa, prod

Use one build pipeline and one deployment pipeline with environment promotion.

### Phase 26: Environment model

Recommended setup:

- `dev`: auto deploy from feature merge to `main` (or `develop`).
- `qa`: auto deploy from `main` after `dev` succeeds.
- `prod`: deploy only from version tags (`v*`) with manual approval.

For isolation, prefer separate AWS accounts and EKS clusters:

- `graphql-federation-dev`
- `graphql-federation-qa`
- `graphql-federation-prod`

If separate clusters are not possible, use one cluster with strict namespace + IAM isolation:

- namespace: `graphql-federation-dev`
- namespace: `graphql-federation-qa`
- namespace: `graphql-federation-prod`

### Phase 27: GitHub Environments and secrets

Create GitHub Environments: `dev`, `qa`, `prod`.

In each environment, configure:

- `AWS_REGION`
- `AWS_ROLE_ARN` (OIDC deploy role for that environment)
- `EKS_CLUSTER_NAME`
- `ECR_USERS_REPO`
- `ECR_TODOS_REPO`
- `ECR_ROUTER_REPO`

Enable protection rules:

- `dev`: no approval required.
- `qa`: 1 required reviewer.
- `prod`: 2 required reviewers + restricted branch/tag policy.

### Phase 28: Pipeline architecture

Split workflows into 3 stages:

1. **CI (every PR)**
   - lint + tests
   - start users/todos locally in CI
   - run `./scripts/compose_supergraph.sh`
   - run federated tests (`pytest -q`)

2. **Build (merge to main / release tag)**
   - build images: users, todos, router
   - tag all with same immutable tag (`${GITHUB_SHA}`)
   - push to ECR
   - publish deploy metadata artifact (image tags + supergraph checksum)

3. **Deploy (environment promotion)**
   - apply manifests to target env
   - update image tags in deployments
   - update router supergraph ConfigMap
   - rollout status + smoke query through router

### Phase 29: Promotion strategy (important)

Build once, promote same artifact:

- do **not** rebuild for qa/prod
- deploy exact image digests built in CI
- keep router supergraph artifact version aligned with subgraph image versions

Promotion flow:

```text
PR -> CI pass
main merge -> deploy dev
manual promotion -> deploy qa
tag vX.Y.Z + approval -> deploy prod
```

### Phase 30: Suggested workflow files

```text
.github/workflows/
├── federation-ci.yml
├── federation-build.yml
└── federation-deploy.yml
```

`federation-ci.yml` triggers on PR changes under `fastapi-subgraph-federation/**`.

`federation-build.yml` triggers on `main` and `v*` tags, builds/pushes images, uploads deployment metadata.

`federation-deploy.yml` is reusable (`workflow_call`) and takes `environment` input (`dev|qa|prod`).

### Phase 31: Example deploy workflow shape

```yaml
name: federation-deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, qa, prod]
        required: true
      image_tag:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Configure kubectl
        run: aws eks update-kubeconfig --name "${{ secrets.EKS_CLUSTER_NAME }}" --region "${{ secrets.AWS_REGION }}"

      - name: Set image tags
        run: |
          kubectl -n graphql-federation-${{ inputs.environment }} set image deployment/users users=${{ secrets.ECR_USERS_REPO }}:${{ inputs.image_tag }}
          kubectl -n graphql-federation-${{ inputs.environment }} set image deployment/todos todos=${{ secrets.ECR_TODOS_REPO }}:${{ inputs.image_tag }}

      - name: Apply router supergraph + restart router
        run: |
          kubectl apply -f fastapi-subgraph-federation/k8s/router-supergraph-configmap.yaml
          kubectl -n graphql-federation-${{ inputs.environment }} rollout restart deployment/router

      - name: Wait for rollouts
        run: |
          kubectl -n graphql-federation-${{ inputs.environment }} rollout status deployment/users --timeout=180s
          kubectl -n graphql-federation-${{ inputs.environment }} rollout status deployment/todos --timeout=180s
          kubectl -n graphql-federation-${{ inputs.environment }} rollout status deployment/router --timeout=180s
```

### Phase 32: Terraform and Kubernetes per environment

For Terraform state, separate by environment:

- backend key: `federation/dev/terraform.tfstate`
- backend key: `federation/qa/terraform.tfstate`
- backend key: `federation/prod/terraform.tfstate`

For Kubernetes manifests, prefer overlays (Kustomize or Helm):

- base: common resources
- overlays/dev: namespace, replica counts, hostnames
- overlays/qa: tighter limits, QA ingress host
- overlays/prod: higher replicas, stricter pod disruption and autoscaling

### Phase 33: Federation-specific checks in CI/CD

Always enforce:

- `rover supergraph compose --config router/supergraph.yaml`
- fail build if composition fails
- run one federated smoke query after deploy:
  - `createUser`
  - `createTodo`
  - query `todos { owner { id name email } }`

This guarantees router + subgraph compatibility in each environment.
