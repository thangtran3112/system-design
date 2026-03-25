# GraphQL Federation with FastAPI + Strawberry (Combined Guide)

This file combines:

- the full learning direction from `simple-graphql-oauth/LEARN-FEDERATION.md`
- the local scaffold and workflow in `fastapi-subgraph-federation`

Goal: learn federation concepts while running a ready project structure.

---

## Part 1: What Federation Solves

Monolithic GraphQL works early, but gets hard with many teams/domains.

- One schema and resolver file become a bottleneck.
- One deploy pipeline means all teams are coupled.
- One failure can impact all features.

Federation splits your graph into independent subgraphs, then composes them into one supergraph.

Core terms:

- `Subgraph`: a GraphQL service owning one domain slice.
- `Supergraph`: the unified schema clients see.
- `Router`: query planner that fans out to subgraphs and merges results.
- `Entity`: shared type resolved across subgraphs.
- `@key`: lookup key for entity resolution.
- `resolve_reference`: subgraph callback to hydrate entity by key.

---

## Part 2: This Repository Layout

```
fastapi-subgraph-federation/
├── services/
│   ├── users/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   └── schema.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── todos/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── database.py
│       │   ├── main.py
│       │   ├── models.py
│       │   └── schema.py
│       ├── requirements.txt
│       └── Dockerfile
├── router/
│   └── supergraph.yaml
├── scripts/
│   ├── setup_envs.sh
│   └── compose_supergraph.sh
├── docker-compose.yml
└── .env.example
```

Domain split used here:

- `users` subgraph owns `User` as entity (`@key(fields: "id")`).
- `todos` subgraph owns `Todo` and references `User` by `id` only.

---

## Part 3: Python Setup with uv (Recommended)

You can keep separate environments per subgraph to mimic independent services.

### 1) Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart shell, then verify:

```bash
uv --version
```

### 2) Create venvs with uv

From project root:

```bash
cd /home/thangtran3112/workspace/system-design/fastapi-graphql-oauth/fastapi-subgraph-federation

uv venv services/users/.venv
uv venv services/todos/.venv
```

### 3) Install dependencies per subgraph

```bash
uv pip install --python services/users/.venv/bin/python -r services/users/requirements.txt
uv pip install --python services/todos/.venv/bin/python -r services/todos/requirements.txt
```

You can also use the helper script (uses venv + pip):

```bash
./scripts/setup_envs.sh
```

### 4) Run users subgraph (terminal 1)

```bash
cd services/users
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

### 5) Run todos subgraph (terminal 2)

```bash
cd services/todos
source .venv/bin/activate
uvicorn app.main:app --reload --port 8002
```

### 6) Compose and run router

Install tools once:

```bash
curl -sSL https://rover.apollo.dev/nix/latest | sh
curl -sSL https://router.apollo.dev/download/nix/latest | sh
```

Compose supergraph:

```bash
./scripts/compose_supergraph.sh
```

Run router:

```bash
router --supergraph router/supergraph.graphql --dev
```

Endpoints:

- `http://localhost:8001/graphql` (users)
- `http://localhost:8002/graphql` (todos)
- `http://localhost:4000` (supergraph router)

---

## Part 4: Learning Path (Hands-on)

### Phase 1: Validate each subgraph independently

- Create user on users subgraph.
- Create todo on todos subgraph using `ownerId`.
- Confirm todos subgraph can only return `owner { id }` locally.

### Phase 2: Validate composition

```bash
rover supergraph compose --config router/supergraph.yaml > router/supergraph.graphql
APOLLO_ELV2_LICENSE=accept ./scripts/compose_supergraph.sh
```

If this fails, schemas are incompatible.

### Phase 3: Query across subgraphs through router

```graphql
{
  todos {
    id
    title
    owner {
      id
      name
      email
    }
  }
}
```

Expected behavior:

- Todos subgraph returns `owner.id`.
- Router calls users subgraph `_entities`.
- Router merges and returns full owner fields.

### Phase 4: Inspect federation internals

Run on users subgraph:

```graphql
{
  _service {
    sdl
  }
}
```

Look for `@key(fields: "id")` on `User`.

### Phase 5: Extend entity

Add `User.todos` field inside `services/todos/app/schema.py`, then recompose and query:

```graphql
{
  user(id: 1) {
    name
    todos {
      id
      title
    }
  }
}
```

---

## Part 5: Architecture and Operational Notes

- Federation is best when domains/teams need independent release cycles.
- For 1-3 devs and simple domain, monolith GraphQL is often simpler.
- Run composition checks (`rover supergraph compose`) in CI.
- Add DataLoader for entity lookups to avoid N+1 inside subgraphs.
- Router is stateless and can scale separately from subgraphs.

---

## Part 6: Optional Docker Workflow

If you prefer one command local startup:

1. Compose supergraph first (`router/supergraph.graphql` must exist).
2. Run:

```bash
docker compose up --build
```

This starts users, todos, and router from `docker-compose.yml`.

---

## Validation Checklist

- users health: `GET http://localhost:8001/health`
- todos health: `GET http://localhost:8002/health`
- router up: `GET http://localhost:4000`
- federated query returns owner fields from users through router
- `rover supergraph compose` succeeds after schema changes
