def test_create_and_query_todo(client):
    # Create
    mutation = """
        mutation {
            createTodo(input: { title: "Test Todo" }, ownerId: 1) {
                id
                title
                description
                completed
            }
        }
    """
    response = client.post("/graphql", json={"query": mutation})
    assert response.status_code == 200
    data = response.json()["data"]["createTodo"]
    assert data["title"] == "Test Todo"
    assert data["completed"] is False
    todo_id = data["id"]

    # Query
    query = f"""
        {{
            todo(id: {todo_id}) {{
                title
                completed
                owner {{
                    name
                }}
            }}
        }}
    """
    response = client.post("/graphql", json={"query": query})
    data = response.json()["data"]["todo"]
    assert data["title"] == "Test Todo"
    assert data["owner"]["name"] == "Tester"

def test_update_todo(client):
    # Create first
    create = """
        mutation {
            createTodo(input: { title: "Update Me" }, ownerId: 1) { id }
        }
    """
    response = client.post("/graphql", json={"query": create})
    todo_id = response.json()["data"]["createTodo"]["id"]

    # Update
    update = f"""
        mutation {{
            updateTodo(id: {todo_id}, input: {{ completed: true, title: "Updated" }}) {{
                title
                completed
            }}
        }}
    """
    response = client.post("/graphql", json={"query": update})
    data = response.json()["data"]["updateTodo"]
    assert data["title"] == "Updated"
    assert data["completed"] is True

def test_delete_todo(client):
    create = """
        mutation {
            createTodo(input: { title: "Delete Me" }, ownerId: 1) { id }
        }
    """
    response = client.post("/graphql", json={"query": create})
    todo_id = response.json()["data"]["createTodo"]["id"]

    delete = f"""
        mutation {{
            deleteTodo(id: {todo_id})
        }}
    """
    response = client.post("/graphql", json={"query": delete})
    assert response.json()["data"]["deleteTodo"] is True

def test_query_empty_todos(client):
    query = "{ todos { id title } }"
    response = client.post("/graphql", json={"query": query})
    assert response.json()["data"]["todos"] == []