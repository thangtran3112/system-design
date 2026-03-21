"""
Tests for the Todo CRUD API.
Each test gets a fresh database (tables created/dropped per test via conftest.py).
"""

def test_create_todo(client):
    response = client.post("/todos", json={
        "title": "Learn FastAPI",
        "description": "Build a CRUD app"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Learn FastAPI"
    assert data["description"] == "Build a CRUD app"
    assert data["completed"] is False  # default value
    assert "id" in data

def test_create_todo_minimal(client):
    """POST /todos with only required field (title) should work."""
    response = client.post("/todos", json={"title" : "Minimal todo"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal todo"
    assert data["description"] == ""  # default

def test_read_todos_empty(client):
    """GET /todos on empty database should return empty list."""
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_read_todos(client):
    """GET /todos should return all created todos."""
    client.post("/todos", json={"title": "First"})
    client.post("/todos", json={"title": "Second"})

    response = client.get("/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "First"
    assert data[1]["title"] == "Second"

# ─── READ ONE ─────────────────────────────────────────────────────────

def test_read_todo(client):
    """GET /todos/{id} should return the specific todo."""
    create_resp = client.post("/todos", json={"title": "Find me"})
    todo_id = create_resp.json()["id"]

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Find me"


def test_read_todo_not_found(client):
    """GET /todos/{id} with non-existent id should return 404."""
    response = client.get("/todos/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"

# ─── UPDATE ───────────────────────────────────────────────────────────

def test_update_todo(client):
    """PUT /todos/{id} should update specified fields only."""
    create_resp = client.post("/todos", json={
        "title": "Original",
        "description": "Old description",
    })
    todo_id = create_resp.json()["id"]

    response = client.put(f"/todos/{todo_id}", json={
        "title": "Updated",
        "completed": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["completed"] is True
    assert data["description"] == "Old description"  # unchanged


def test_update_todo_not_found(client):
    """PUT /todos/{id} with non-existent id should return 404."""
    response = client.put("/todos/999", json={"title": "Nope"})
    assert response.status_code == 404

# ─── DELETE ───────────────────────────────────────────────────────────

def test_delete_todo(client):
    """DELETE /todos/{id} should remove the todo and return 204."""
    create_resp = client.post("/todos", json={"title": "Delete me"})
    todo_id = create_resp.json()["id"]

    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = client.get(f"/todos/{todo_id}")
    assert get_resp.status_code == 404


def test_delete_todo_not_found(client):
    """DELETE /todos/{id} with non-existent id should return 404."""
    response = client.delete("/todos/999")
    assert response.status_code == 404