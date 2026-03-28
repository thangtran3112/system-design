import json
import urllib.request
import uuid

ROUTER_URL = "http://127.0.0.1:4000/"


# ---------------------------------------------------------------------------
# Helper: create a user + todo through the router for reuse across tests
# ---------------------------------------------------------------------------

def _create_user_via_router(graphql_post):
    email = f"federation-{uuid.uuid4().hex[:8]}@example.com"
    name = f"User-{uuid.uuid4().hex[:6]}"
    mutation = """
    mutation CreateUser($input: CreateUserInput!) {
      createUser(input: $input) { id email name provider }
    }
    """
    _, payload = graphql_post(
        ROUTER_URL, mutation, {"input": {"email": email, "name": name}}
    )
    assert "errors" not in payload, payload
    return payload["data"]["createUser"]


def _create_todo_via_router(graphql_post, owner_id, title=None, description=""):
    title = title or f"todo-{uuid.uuid4().hex[:6]}"
    mutation = """
    mutation CreateTodo($input: CreateTodoInput!) {
      createTodo(input: $input) { id title description completed owner { id } }
    }
    """
    _, payload = graphql_post(
        ROUTER_URL,
        mutation,
        {"input": {"title": title, "ownerId": owner_id, "description": description}},
    )
    assert "errors" not in payload, payload
    return payload["data"]["createTodo"]


# ---------------------------------------------------------------------------
# 1. Original cross-subgraph resolution test (kept as-is)
# ---------------------------------------------------------------------------

def test_supergraph_resolves_cross_subgraph_fields(ensure_services_up, graphql_post):
    email = f"federation-{uuid.uuid4().hex[:8]}@example.com"
    name = f"User-{uuid.uuid4().hex[:6]}"

    create_user_mutation = """
    mutation CreateUser($input: CreateUserInput!) {
      createUser(input: $input) {
        id
        email
        name
      }
    }
    """
    _, create_user_payload = graphql_post(
        "http://127.0.0.1:4000/",
        create_user_mutation,
        {"input": {"email": email, "name": name}},
    )
    assert "errors" not in create_user_payload
    user = create_user_payload["data"]["createUser"]

    create_todo_mutation = """
    mutation CreateTodo($input: CreateTodoInput!) {
      createTodo(input: $input) {
        id
        title
        owner {
          id
        }
      }
    }
    """
    title = f"federation-todo-{uuid.uuid4().hex[:6]}"
    _, create_todo_payload = graphql_post(
        "http://127.0.0.1:4000/",
        create_todo_mutation,
        {
            "input": {
                "title": title,
                "ownerId": user["id"],
                "description": "router-test",
            }
        },
    )
    assert "errors" not in create_todo_payload
    todo = create_todo_payload["data"]["createTodo"]
    assert int(todo["owner"]["id"]) == int(user["id"])

    query = """
    query TodosWithOwner($ownerId: Int!) {
      todos(ownerId: $ownerId) {
        id
        title
        owner {
          id
          name
          email
        }
      }
    }
    """
    _, query_payload = graphql_post(
        "http://127.0.0.1:4000/", query, {"ownerId": int(user["id"])}
    )
    assert "errors" not in query_payload

    todos = query_payload["data"]["todos"]
    matched = [item for item in todos if item["id"] == todo["id"]]
    assert matched, "Created todo not returned in supergraph query"

    owner = matched[0]["owner"]
    assert owner["email"] == email
    assert owner["name"] == name


# ---------------------------------------------------------------------------
# 2. Router health / reachability
# ---------------------------------------------------------------------------

def test_router_is_reachable(ensure_services_up):
    """Router should respond to HTTP requests (400 on bare GET is expected)."""
    req = urllib.request.Request(ROUTER_URL, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.getcode() < 500
    except urllib.error.HTTPError as exc:
        assert exc.code < 500


# ---------------------------------------------------------------------------
# 3. Introspection via the router (--dev mode enables this)
# ---------------------------------------------------------------------------

def test_router_introspection_returns_schema(ensure_services_up, graphql_post):
    """Introspection should expose types from both subgraphs."""
    query = """
    {
      __schema {
        types { name }
      }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query)
    assert "errors" not in payload, payload
    type_names = {t["name"] for t in payload["data"]["__schema"]["types"]}
    assert "UserType" in type_names
    assert "TodoType" in type_names
    assert "CreateUserInput" in type_names
    assert "CreateTodoInput" in type_names


def test_router_introspection_query_fields(ensure_services_up, graphql_post):
    """The federated Query type should surface fields from both subgraphs."""
    query = """
    {
      __type(name: "Query") {
        fields { name }
      }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query)
    assert "errors" not in payload, payload
    field_names = {f["name"] for f in payload["data"]["__type"]["fields"]}
    assert "users" in field_names
    assert "user" in field_names
    assert "todos" in field_names
    assert "todo" in field_names


# ---------------------------------------------------------------------------
# 4. Single-user query via router
# ---------------------------------------------------------------------------

def test_query_single_user_through_router(ensure_services_up, graphql_post):
    user = _create_user_via_router(graphql_post)
    query = """
    query GetUser($id: Int!) {
      user(id: $id) { id email name }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query, {"id": int(user["id"])})
    assert "errors" not in payload, payload
    assert payload["data"]["user"]["email"] == user["email"]


# ---------------------------------------------------------------------------
# 5. Single-todo query via router
# ---------------------------------------------------------------------------

def test_query_single_todo_through_router(ensure_services_up, graphql_post):
    user = _create_user_via_router(graphql_post)
    todo = _create_todo_via_router(graphql_post, int(user["id"]), description="single-lookup")
    query = """
    query GetTodo($id: Int!) {
      todo(id: $id) { id title description completed owner { id email } }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query, {"id": int(todo["id"])})
    assert "errors" not in payload, payload
    result = payload["data"]["todo"]
    assert result["title"] == todo["title"]
    assert result["description"] == "single-lookup"
    assert result["completed"] is False
    assert int(result["owner"]["id"]) == int(user["id"])


# ---------------------------------------------------------------------------
# 6. Update todo through the router
# ---------------------------------------------------------------------------

def test_update_todo_through_router(ensure_services_up, graphql_post):
    user = _create_user_via_router(graphql_post)
    todo = _create_todo_via_router(graphql_post, int(user["id"]))

    mutation = """
    mutation UpdateTodo($id: Int!, $input: UpdateTodoInput!) {
      updateTodo(id: $id, input: $input) { id title completed }
    }
    """
    _, payload = graphql_post(
        ROUTER_URL,
        mutation,
        {"id": int(todo["id"]), "input": {"title": "updated-title", "completed": True}},
    )
    assert "errors" not in payload, payload
    updated = payload["data"]["updateTodo"]
    assert updated["title"] == "updated-title"
    assert updated["completed"] is True


# ---------------------------------------------------------------------------
# 7. Delete todo through the router
# ---------------------------------------------------------------------------

def test_delete_todo_through_router(ensure_services_up, graphql_post):
    user = _create_user_via_router(graphql_post)
    todo = _create_todo_via_router(graphql_post, int(user["id"]))

    mutation = """
    mutation DeleteTodo($id: Int!) {
      deleteTodo(id: $id)
    }
    """
    _, payload = graphql_post(ROUTER_URL, mutation, {"id": int(todo["id"])})
    assert "errors" not in payload, payload
    assert payload["data"]["deleteTodo"] is True

    # Confirm it's gone
    query = """
    query GetTodo($id: Int!) {
      todo(id: $id) { id }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query, {"id": int(todo["id"])})
    assert "errors" not in payload, payload
    assert payload["data"]["todo"] is None


# ---------------------------------------------------------------------------
# 8. User default provider field via router
# ---------------------------------------------------------------------------

def test_create_user_default_provider(ensure_services_up, graphql_post):
    """Users created without explicit provider should default to 'local'."""
    user = _create_user_via_router(graphql_post)
    assert user["provider"] == "local"


# ---------------------------------------------------------------------------
# 9. Reverse federation: user -> todos (User.todos field from todos subgraph)
# ---------------------------------------------------------------------------

def test_user_todos_reverse_federation(ensure_services_up, graphql_post):
    """Query user { todos { ... } } — the router must join users + todos subgraphs."""
    user = _create_user_via_router(graphql_post)
    todo1 = _create_todo_via_router(graphql_post, int(user["id"]), title="rev-fed-1")
    todo2 = _create_todo_via_router(graphql_post, int(user["id"]), title="rev-fed-2")

    query = """
    query GetUser($id: Int!) {
      user(id: $id) {
        id
        todos { id title }
      }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query, {"id": int(user["id"])})
    assert "errors" not in payload, payload
    todos = payload["data"]["user"]["todos"]
    titles = {t["title"] for t in todos}
    assert "rev-fed-1" in titles
    assert "rev-fed-2" in titles


# ---------------------------------------------------------------------------
# 10. Error handling: invalid mutation input
# ---------------------------------------------------------------------------

def test_router_returns_error_for_invalid_input(ensure_services_up):
    """Sending a mutation with missing required fields should return an error."""
    mutation = """
    mutation CreateUser($input: CreateUserInput!) {
      createUser(input: $input) { id }
    }
    """
    body = json.dumps({
        "query": mutation,
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
        # Router may return 400 for validation errors — that counts as rejected
        assert exc.code == 400


# ---------------------------------------------------------------------------
# 11. Query non-existent user returns null
# ---------------------------------------------------------------------------

def test_query_nonexistent_user_returns_null(ensure_services_up, graphql_post):
    query = """
    query GetUser($id: Int!) {
      user(id: $id) { id email }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query, {"id": 999999})
    assert "errors" not in payload, payload
    assert payload["data"]["user"] is None


# ---------------------------------------------------------------------------
# 12. Query non-existent todo returns null
# ---------------------------------------------------------------------------

def test_query_nonexistent_todo_returns_null(ensure_services_up, graphql_post):
    query = """
    query GetTodo($id: Int!) {
      todo(id: $id) { id title }
    }
    """
    _, payload = graphql_post(ROUTER_URL, query, {"id": 999999})
    assert "errors" not in payload, payload
    assert payload["data"]["todo"] is None


# ---------------------------------------------------------------------------
# 13. Multiple users list query
# ---------------------------------------------------------------------------

def test_users_list_through_router(ensure_services_up, graphql_post):
    user1 = _create_user_via_router(graphql_post)
    user2 = _create_user_via_router(graphql_post)

    query = "{ users { id email } }"
    _, payload = graphql_post(ROUTER_URL, query)
    assert "errors" not in payload, payload
    ids = {u["id"] for u in payload["data"]["users"]}
    assert user1["id"] in ids
    assert user2["id"] in ids
