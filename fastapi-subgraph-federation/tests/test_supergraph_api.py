import json
import urllib.error
import urllib.request
import uuid

from conftest import ROUTER_URL


def _random_email():
    return f"federation-{uuid.uuid4().hex[:8]}@example.com"


def _random_name():
    return f"User-{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# 1. Cross-subgraph resolution (the original end-to-end test)
# ---------------------------------------------------------------------------

def test_supergraph_resolves_cross_subgraph_fields(client):
    user = client.create_user(_random_email(), _random_name())
    todo = client.create_todo(int(user["id"]), title="federation-e2e", description="router-test")

    assert int(todo["owner"]["id"]) == int(user["id"])

    todos = client.list_todos(owner_id=int(user["id"]))
    matched = [t for t in todos if t["id"] == todo["id"]]
    assert matched, "Created todo not returned in supergraph query"
    assert matched[0]["owner"]["email"] == user["email"]
    assert matched[0]["owner"]["name"] == user["name"]


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
# 3. Introspection
# ---------------------------------------------------------------------------

def test_router_introspection_returns_schema(client):
    type_names = client.introspect_type_names()
    assert "UserType" in type_names
    assert "TodoType" in type_names
    assert "CreateUserInput" in type_names
    assert "CreateTodoInput" in type_names


def test_router_introspection_query_fields(client):
    fields = client.introspect_query_fields()
    assert "users" in fields
    assert "user" in fields
    assert "todos" in fields
    assert "todo" in fields


# ---------------------------------------------------------------------------
# 4. Single-user query
# ---------------------------------------------------------------------------

def test_query_single_user_through_router(client):
    user = client.create_user(_random_email(), _random_name())
    fetched = client.get_user(int(user["id"]))
    assert fetched["email"] == user["email"]
    assert fetched["name"] == user["name"]


# ---------------------------------------------------------------------------
# 5. Single-todo query
# ---------------------------------------------------------------------------

def test_query_single_todo_through_router(client):
    user = client.create_user(_random_email(), _random_name())
    todo = client.create_todo(int(user["id"]), title="single-lookup", description="desc")

    fetched = client.get_todo(int(todo["id"]))
    assert fetched["title"] == "single-lookup"
    assert fetched["description"] == "desc"
    assert fetched["completed"] is False
    assert int(fetched["owner"]["id"]) == int(user["id"])


# ---------------------------------------------------------------------------
# 6. Update todo
# ---------------------------------------------------------------------------

def test_update_todo_through_router(client):
    user = client.create_user(_random_email(), _random_name())
    todo = client.create_todo(int(user["id"]), title="before-update")

    updated = client.update_todo(int(todo["id"]), title="after-update", completed=True)
    assert updated["title"] == "after-update"
    assert updated["completed"] is True


# ---------------------------------------------------------------------------
# 7. Delete todo
# ---------------------------------------------------------------------------

def test_delete_todo_through_router(client):
    user = client.create_user(_random_email(), _random_name())
    todo = client.create_todo(int(user["id"]), title="to-delete")

    assert client.delete_todo(int(todo["id"])) is True
    assert client.get_todo(int(todo["id"])) is None


# ---------------------------------------------------------------------------
# 8. Default provider
# ---------------------------------------------------------------------------

def test_create_user_default_provider(client):
    user = client.create_user(_random_email(), _random_name())
    assert user["provider"] == "local"


# ---------------------------------------------------------------------------
# 9. Reverse federation: user -> todos
# ---------------------------------------------------------------------------

def test_user_todos_reverse_federation(client):
    user = client.create_user(_random_email(), _random_name())
    client.create_todo(int(user["id"]), title="rev-fed-1")
    client.create_todo(int(user["id"]), title="rev-fed-2")

    result = client.get_user_with_todos(int(user["id"]))
    titles = {t["title"] for t in result["todos"]}
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
    assert client.get_user(999999) is None


# ---------------------------------------------------------------------------
# 12. Non-existent todo returns null
# ---------------------------------------------------------------------------

def test_query_nonexistent_todo_returns_null(client):
    assert client.get_todo(999999) is None


# ---------------------------------------------------------------------------
# 13. Users list query
# ---------------------------------------------------------------------------

def test_users_list_through_router(client):
    user1 = client.create_user(_random_email(), _random_name())
    user2 = client.create_user(_random_email(), _random_name())

    ids = {u["id"] for u in client.list_users()}
    assert user1["id"] in ids
    assert user2["id"] in ids
