from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

import pytest

ROUTER_URL = "http://127.0.0.1:4000/"


# ---------------------------------------------------------------------------
# Low-level HTTP helpers
# ---------------------------------------------------------------------------

def _http_get_json(url: str, timeout: float = 2.0):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.getcode(), json.loads(response.read().decode("utf-8"))


def _graphql_post(
    url: str, query: str, variables: dict | None = None, timeout: float = 3.0
):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.getcode(), json.loads(response.read().decode("utf-8"))


def _http_is_reachable(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.getcode() < 400
    except (urllib.error.URLError, TimeoutError):
        return False


# ---------------------------------------------------------------------------
# Typed SDK client for the federated supergraph
# ---------------------------------------------------------------------------

@dataclass
class GraphQLError(Exception):
    errors: list[dict]
    def __str__(self):
        return str(self.errors)


class SupergraphClient:
    """Typed client that talks to the Apollo Router supergraph endpoint."""

    def __init__(self, url: str = ROUTER_URL):
        self.url = url

    # -- raw execute --------------------------------------------------------

    def execute(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL operation and return the full payload.

        Raises ``GraphQLError`` if the response contains errors.
        """
        _, payload = _graphql_post(self.url, query, variables)
        if "errors" in payload:
            raise GraphQLError(payload["errors"])
        return payload["data"]

    def execute_raw(self, query: str, variables: dict | None = None) -> dict:
        """Like execute but returns the full payload without raising on errors."""
        _, payload = _graphql_post(self.url, query, variables)
        return payload

    # -- users --------------------------------------------------------------

    def create_user(self, email: str, name: str, provider: str = "local") -> dict:
        data = self.execute(
            """
            mutation($input: CreateUserInput!) {
                createUser(input: $input) { id email name provider }
            }
            """,
            {"input": {"email": email, "name": name, "provider": provider}},
        )
        return data["createUser"]

    def get_user(self, user_id: int) -> dict | None:
        data = self.execute(
            """
            query($id: Int!) {
                user(id: $id) { id email name provider }
            }
            """,
            {"id": user_id},
        )
        return data["user"]

    def get_user_with_todos(self, user_id: int) -> dict | None:
        data = self.execute(
            """
            query($id: Int!) {
                user(id: $id) {
                    id email name
                    todos { id title description completed }
                }
            }
            """,
            {"id": user_id},
        )
        return data["user"]

    def list_users(self) -> list[dict]:
        data = self.execute("{ users { id email name } }")
        return data["users"]

    # -- todos --------------------------------------------------------------

    def create_todo(
        self, owner_id: int, title: str, description: str = ""
    ) -> dict:
        data = self.execute(
            """
            mutation($input: CreateTodoInput!) {
                createTodo(input: $input) {
                    id title description completed
                    owner { id email name }
                }
            }
            """,
            {"input": {"title": title, "ownerId": owner_id, "description": description}},
        )
        return data["createTodo"]

    def get_todo(self, todo_id: int) -> dict | None:
        data = self.execute(
            """
            query($id: Int!) {
                todo(id: $id) {
                    id title description completed
                    owner { id email name }
                }
            }
            """,
            {"id": todo_id},
        )
        return data["todo"]

    def list_todos(self, owner_id: int | None = None) -> list[dict]:
        data = self.execute(
            """
            query($ownerId: Int) {
                todos(ownerId: $ownerId) {
                    id title description completed
                    owner { id email name }
                }
            }
            """,
            {"ownerId": owner_id},
        )
        return data["todos"]

    def update_todo(
        self,
        todo_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
    ) -> dict | None:
        input_fields: dict = {}
        if title is not None:
            input_fields["title"] = title
        if description is not None:
            input_fields["description"] = description
        if completed is not None:
            input_fields["completed"] = completed
        data = self.execute(
            """
            mutation($id: Int!, $input: UpdateTodoInput!) {
                updateTodo(id: $id, input: $input) { id title description completed }
            }
            """,
            {"id": todo_id, "input": input_fields},
        )
        return data["updateTodo"]

    def delete_todo(self, todo_id: int) -> bool:
        data = self.execute(
            """
            mutation($id: Int!) { deleteTodo(id: $id) }
            """,
            {"id": todo_id},
        )
        return data["deleteTodo"]

    # -- introspection ------------------------------------------------------

    def introspect_type_names(self) -> set[str]:
        data = self.execute("{ __schema { types { name } } }")
        return {t["name"] for t in data["__schema"]["types"]}

    def introspect_query_fields(self) -> set[str]:
        data = self.execute('{ __type(name: "Query") { fields { name } } }')
        return {f["name"] for f in data["__type"]["fields"]}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def http_get_json():
    return _http_get_json


@pytest.fixture(scope="session")
def graphql_post():
    return _graphql_post


@pytest.fixture(scope="session")
def ensure_services_up():
    targets = [
        "http://127.0.0.1:8001/health",
        "http://127.0.0.1:8002/health",
        "http://127.0.0.1:8088/health",
    ]
    down = [url for url in targets if not _http_is_reachable(url)]

    if down:
        pytest.skip(
            "Required endpoints are not reachable. Start users/todos/router first: "
            + ", ".join(down)
        )


@pytest.fixture(scope="session")
def client(ensure_services_up) -> SupergraphClient:
    """A typed SDK client for the federated supergraph router."""
    return SupergraphClient()
