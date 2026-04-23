import strawberry
from typing import Optional
from app import database as db_module
from app.models import Todo, User
from app.schemas import TodoType, UserType, CreateTodoInput, UpdateTodoInput

def db_todo_to_type(todo: Todo) -> TodoType:
    """Convert SQLAlchemy model → GraphQL type."""
    return TodoType(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        owner=UserType(
            id=todo.owner.id,
            email=todo.owner.email,
            name=todo.owner.name,
            picture=todo.owner.picture,
            provider=todo.owner.provider,
        ),
    )

@strawberry.type
class Query:
    @strawberry.field
    def todos(self, owner_id: Optional[int] = None) -> list[TodoType]:
        """Fetch all todos, optionally filtered by owner."""
        db = db_module.SessionLocal()
        try:
            query = db.query(Todo)
            if owner_id is not None:
                query = query.filter(Todo.owner_id == owner_id)
            return [db_todo_to_type(t) for t in query.all()]
        finally:
            db.close()

    @strawberry.field
    def todo(self, id: int) -> Optional[TodoType]:
        """Fetch a single todo by ID."""
        db = db_module.SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            return db_todo_to_type(todo) if todo else None
        finally:
            db.close()

    @strawberry.field
    def users(self) -> list[UserType]:
        db = db_module.SessionLocal()
        try:
            return [
                UserType(
                    id=u.id, email=u.email, name=u.name,
                    picture=u.picture, provider=u.provider,
                )
                for u in db.query(User).all()
            ]
        finally:
            db.close()

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_todo(self, input: CreateTodoInput, owner_id: int) -> TodoType:
        db = db_module.SessionLocal()
        try:
            todo = Todo(
                title=input.title,
                description=input.description,
                owner_id=owner_id,
            )
            db.add(todo)
            db.commit()
            db.refresh(todo)
            return db_todo_to_type(todo)
        finally:
            db.close()

    @strawberry.mutation
    def update_todo(self, id: int, input: UpdateTodoInput) -> Optional[TodoType]:
        db = db_module.SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            if not todo:
                return None
            if input.title is not None:
                todo.title = input.title
            if input.description is not None:
                todo.description = input.description
            if input.completed is not None:
                todo.completed = input.completed
            db.commit()
            db.refresh(todo)
            return db_todo_to_type(todo)
        finally:
            db.close()

    @strawberry.mutation
    def delete_todo(self, id: int) -> bool:
        db = db_module.SessionLocal()
        try:
            todo = db.query(Todo).filter(Todo.id == id).first()
            if not todo:
                return False
            db.delete(todo)
            db.commit()
            return True
        finally:
            db.close()
