from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Todo
from app.schemas import TodoCreate

async def create_todo(db: AsyncSession, todo: TodoCreate) -> Todo:
    db_todo = Todo(**todo.model_dump())
    db.add(db_todo)
    await db.commit()
    await db.refresh(db_todo)
    return db_todo

async def get_todos(db: AsyncSession) -> list[Todo]:
    result = await db.execute(select(Todo))
    # response have form of [(Todo1, _), (Todo2, ), ...]
    # scalar extract only the first values in all tuples.
    return list(result.scalars().all())

async def get_todo(db: AsyncSession, todo_id: int) -> Todo | None:
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    return result.scalar_one_or_none()