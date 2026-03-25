from typing import Optional

import strawberry

from app.database import SessionLocal
from app.models import Todo


@strawberry.federation.type(keys=["id"])
class UserType:
    id: int

    @strawberry.field
    def todos(self, info: strawberry.types.Info) -> list["TodoType"]:
        db = SessionLocal()
        try:
            todos = db.query(Todo).filter(Todo.owner_id == self.id).all()
            return [to_todo_type(todo) for todo in todos]
        finally:
            db.close()


@strawberry.federation.type
class TodoType:
    id: int
    title: str
    description: str
    completed: bool
    owner: UserType


@strawberry.input
class CreateTodoInput:
    title: str
    owner_id: int
    description: str = ""


@strawberry.input
class UpdateTodoInput:
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


def to_todo_type(todo: Todo) -> TodoType:
    return TodoType(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        owner=UserType(id=todo.owner_id),
    )


@strawberry.type
class Query:
    @strawberry.field
    def todos(self, owner_id: Optional[int] = None) -> list[TodoType]:
        db = SessionLocal()
        try:
            query = db.query(Todo)
            if owner_id is not None:
                query = query.filter(Todo.owner_id == owner_id)
            return [to_todo_type(todo) for todo in query.all()]
        finally:
            db.close()

    @strawberry.field
    def todo(self, id: int) -> Optional[TodoType]:
        db = SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            return to_todo_type(todo) if todo else None
        finally:
            db.close()


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_todo(self, input: CreateTodoInput) -> TodoType:
        db = SessionLocal()
        try:
            todo = Todo(
                title=input.title,
                description=input.description,
                owner_id=input.owner_id,
            )
            db.add(todo)
            db.commit()
            db.refresh(todo)
            return to_todo_type(todo)
        finally:
            db.close()

    @strawberry.mutation
    def update_todo(self, id: int, input: UpdateTodoInput) -> Optional[TodoType]:
        db = SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            if todo is None:
                return None
            if input.title is not None:
                todo.title = input.title
            if input.description is not None:
                todo.description = input.description
            if input.completed is not None:
                todo.completed = input.completed
            db.commit()
            db.refresh(todo)
            return to_todo_type(todo)
        finally:
            db.close()

    @strawberry.mutation
    def delete_todo(self, id: int) -> bool:
        db = SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            if todo is None:
                return False
            db.delete(todo)
            db.commit()
            return True
        finally:
            db.close()
