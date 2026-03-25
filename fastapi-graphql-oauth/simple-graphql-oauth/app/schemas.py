import strawberry
from typing import Optional

# GraphQL types — these define what the CLIENT sees
# They are NOT your DB models. They're the "response shape."

@strawberry.type
class UserType:
    id: int
    email: str
    name: str
    picture: Optional[str]
    provider: str

@strawberry.type
class TodoType:
    id: int
    title: str
    description: str
    completed: bool
    owner: UserType  # nested! Client can query todo { owner { name } }

# Input types — what the client SENDS for mutations
# Like Pydantic's "Create" schemas

@strawberry.input
class CreateTodoInput:
    title: str
    description: str = ""

@strawberry.input
class UpdateTodoInput:
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
