import uuid


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
