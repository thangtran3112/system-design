import json
import urllib.error
import urllib.request
import uuid

from conftest import ROUTER_URL
from supergraph_client.input_types import CreateTodoInput, CreateUserInput, UpdateTodoInput


def _random_email():
    return f"federation-{uuid.uuid4().hex[:8]}@example.com"


def _random_name():
    return f"User-{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# 1. Cross-subgraph resolution (the original end-to-end test)
# ---------------------------------------------------------------------------

def test_supergraph_resolves_cross_subgraph_fields(client):
    user_resp = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name()))
    user = user_resp.create_user

    todo_resp = client.create_todo(input=CreateTodoInput(title="federation-e2e", owner_id=user.id, description="router-test"))
    todo = todo_resp.create_todo

    assert todo.owner.id == user.id

    todos_resp = client.todos(owner_id=user.id)
    matched = [t for t in todos_resp.todos if t.id == todo.id]
    assert matched, "Created todo not returned in supergraph query"
    assert matched[0].owner.email == user.email
    assert matched[0].owner.name == user.name


# ---------------------------------------------------------------------------
# 2. Router health / reachability
# ---------------------------------------------------------------------------

def test_router_is_reachable(ensure_services_up):
    req = urllib.request.Request(ROUTER_URL, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.getcode() < 500
    except urllib.error.HTTPError as exc:
        assert exc.code < 500


# ---------------------------------------------------------------------------
# 3. Introspection (raw queries — not part of generated SDK)
# ---------------------------------------------------------------------------

def test_router_introspection_returns_schema(ensure_services_up):
    query = '{ __schema { types { name } } }'
    payload = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        ROUTER_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read())["data"]
    type_names = {t["name"] for t in data["__schema"]["types"]}
    assert "UserType" in type_names
    assert "TodoType" in type_names
    assert "CreateUserInput" in type_names
    assert "CreateTodoInput" in type_names


def test_router_introspection_query_fields(ensure_services_up):
    query = '{ __type(name: "Query") { fields { name } } }'
    payload = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        ROUTER_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read())["data"]
    fields = {f["name"] for f in data["__type"]["fields"]}
    assert "users" in fields
    assert "user" in fields
    assert "todos" in fields
    assert "todo" in fields


# ---------------------------------------------------------------------------
# 4. Single-user query
# ---------------------------------------------------------------------------

def test_query_single_user_through_router(client):
    user_resp = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name()))
    user = user_resp.create_user

    fetched_resp = client.user(id=user.id)
    fetched = fetched_resp.user
    assert fetched.email == user.email
    assert fetched.name == user.name


# ---------------------------------------------------------------------------
# 5. Single-todo query
# ---------------------------------------------------------------------------

def test_query_single_todo_through_router(client):
    user = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name())).create_user
    todo = client.create_todo(input=CreateTodoInput(title="single-lookup", owner_id=user.id, description="desc")).create_todo

    fetched = client.todo(id=todo.id).todo
    assert fetched.title == "single-lookup"
    assert fetched.description == "desc"
    assert fetched.completed is False
    assert fetched.owner.id == user.id


# ---------------------------------------------------------------------------
# 6. Update todo
# ---------------------------------------------------------------------------

def test_update_todo_through_router(client):
    user = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name())).create_user
    todo = client.create_todo(input=CreateTodoInput(title="before-update", owner_id=user.id)).create_todo

    updated = client.update_todo(id=todo.id, input=UpdateTodoInput(title="after-update", completed=True)).update_todo
    assert updated.title == "after-update"
    assert updated.completed is True


# ---------------------------------------------------------------------------
# 7. Delete todo
# ---------------------------------------------------------------------------

def test_delete_todo_through_router(client):
    user = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name())).create_user
    todo = client.create_todo(input=CreateTodoInput(title="to-delete", owner_id=user.id)).create_todo

    result = client.delete_todo(id=todo.id)
    assert result.delete_todo is True

    assert client.todo(id=todo.id).todo is None


# ---------------------------------------------------------------------------
# 8. Default provider
# ---------------------------------------------------------------------------

def test_create_user_default_provider(client):
    user = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name())).create_user
    assert user.provider == "local"


# ---------------------------------------------------------------------------
# 9. Reverse federation: user -> todos
# ---------------------------------------------------------------------------

def test_user_todos_reverse_federation(client):
    user = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name())).create_user
    client.create_todo(input=CreateTodoInput(title="rev-fed-1", owner_id=user.id))
    client.create_todo(input=CreateTodoInput(title="rev-fed-2", owner_id=user.id))

    result = client.user(id=user.id).user
    titles = {t.title for t in result.todos}
    assert "rev-fed-1" in titles
    assert "rev-fed-2" in titles


# ---------------------------------------------------------------------------
# 10. Error handling: invalid mutation input
# ---------------------------------------------------------------------------

def test_router_returns_error_for_invalid_input(ensure_services_up):
    body = json.dumps({
        "query": "mutation($input: CreateUserInput!) { createUser(input: $input) { id } }",
        "variables": {"input": {"email": "bad@test.com"}},
    }).encode("utf-8")
    req = urllib.request.Request(
        ROUTER_URL, data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            payload = json.loads(resp.read())
            assert "errors" in payload
    except urllib.error.HTTPError as exc:
        assert exc.code == 400


# ---------------------------------------------------------------------------
# 11. Non-existent user returns null
# ---------------------------------------------------------------------------

def test_query_nonexistent_user_returns_null(client):
    assert client.user(id=999999).user is None


# ---------------------------------------------------------------------------
# 12. Non-existent todo returns null
# ---------------------------------------------------------------------------

def test_query_nonexistent_todo_returns_null(client):
    assert client.todo(id=999999).todo is None


# ---------------------------------------------------------------------------
# 13. Users list query
# ---------------------------------------------------------------------------

def test_users_list_through_router(client):
    user1 = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name())).create_user
    user2 = client.create_user(input=CreateUserInput(email=_random_email(), name=_random_name())).create_user

    ids = {u.id for u in client.users().users}
    assert user1.id in ids
    assert user2.id in ids
