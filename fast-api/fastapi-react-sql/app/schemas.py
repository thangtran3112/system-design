from pydantic import BaseModel

class TodoCreate(BaseModel):
    title: str
    description: str = ""
    completed: bool = False

class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None

class TodoResponse(BaseModel):
    id: int
    title: str
    description: str
    completed: bool
    # tell pydantic to read SQL Alchemy model attributes directly
    model_config = {"from_attributes": True}
