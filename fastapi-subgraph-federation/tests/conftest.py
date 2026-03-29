from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from supergraph_client import SupergraphClient

ROUTER_URL = "http://127.0.0.1:4000/"


# ---------------------------------------------------------------------------
# Low-level HTTP helpers (still needed for raw / non-SDK tests)
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
    """Generated SDK client for the federated supergraph router."""
    return SupergraphClient(url=ROUTER_URL)
