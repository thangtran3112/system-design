def test_users_subgraph_health(ensure_services_up, http_get_json):
    status, payload = http_get_json("http://127.0.0.1:8001/health")
    assert status == 200
    assert payload["status"] == "ok"
    assert payload["subgraph"] == "users"


def test_todos_subgraph_health(ensure_services_up, http_get_json):
    status, payload = http_get_json("http://127.0.0.1:8002/health")
    assert status == 200
    assert payload["status"] == "ok"
    assert payload["subgraph"] == "todos"


def test_subgraphs_expose_federated_sdl(ensure_services_up, graphql_post):
    query = """
    query SubgraphSDL {
      _service {
        sdl
      }
    }
    """
    _, users_payload = graphql_post("http://127.0.0.1:8001/graphql", query)
    _, todos_payload = graphql_post("http://127.0.0.1:8002/graphql", query)

    users_sdl = users_payload["data"]["_service"]["sdl"]
    todos_sdl = todos_payload["data"]["_service"]["sdl"]

    assert "type User" in users_sdl
    assert "@key" in users_sdl
    assert "type Todo" in todos_sdl
    assert "@key" in todos_sdl
