from sqlalchemy.orm import Session
from app.models import Todo
from app.schemas import TodoCreate, TodoUpdate

def create_todo(db: Session, todo: TodoCreate) -> Todo:
    # convert Pydantic TodoCreate schema to dict
    # and ** convert to keyword argument, to construct SQL Alchemy model object
    db_todo = Todo(**todo.model_dump())
    db.add(db_todo) # add but not yet save
    db.commit() # commit the change, but it may take a while
    db.refresh(db_todo) # reloads from DB after commit, may get generated id
    return db_todo

def get_todos(db: Session) -> list[Todo]:
    return db.query(Todo).all()

def get_todo(db: Session, todo_id: int) -> Todo | None:
    return db.query(Todo).filter(Todo.id == todo_id).first()

def update_todo(db: Session, todo_id: int, todo: TodoUpdate) -> Todo | None:
    todo_doc = db.query(Todo).filter(Todo.id == todo_id).first()

    if todo_doc is None:
        return None
    for key, value in todo.model_dump(exclude_unset=True).items():
        setattr(todo_doc, key, value)
    db.commit()
    db.refresh(todo_doc)
    return todo_doc

def delete_todo(db: Session, todo_id: int) -> bool:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if db_todo is None:
        return None
    db.delete(db_todo)
    db.commit()
    return True