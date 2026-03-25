# FastAPI Subgraph Federation

Hands-on starter for learning GraphQL federation with FastAPI + Strawberry.

This project is split into:

- `services/users`: Users subgraph (owns `User` entity)
- `services/todos`: Todos subgraph (owns `Todo`, references `User`)
- `router`: Apollo Router composition config

Read `LEARN-FEDERATION.md` for the step-by-step learning plan.

## Quick start

1. Set up Python virtual environments:

```bash
./scripts/setup_envs.sh
```

2. Start users subgraph:

```bash
cd services/users
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

3. Start todos subgraph in another terminal:

```bash
cd services/todos
source .venv/bin/activate
uvicorn app.main:app --reload --port 8002
```

4. Compose supergraph (requires `rover`):

```bash
./scripts/compose_supergraph.sh
```

5. Start Apollo Router:

```bash
router --supergraph router/supergraph.graphql --dev
```

Then open:

- Users subgraph: `http://localhost:8001/graphql`
- Todos subgraph: `http://localhost:8002/graphql`
- Supergraph router: `http://localhost:4000`

## API tests

With users, todos, and router running, execute:

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```
