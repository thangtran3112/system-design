from typing import Optional

import strawberry
from strawberry.dataloader import DataLoader

from app.database import SessionLocal
from app.models import User


def to_user_type(user: User) -> "UserType":
    return UserType(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        provider=user.provider,
    )


async def load_users(ids: list[int]) -> list[Optional["UserType"]]:
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.id.in_(ids)).all()
        user_map = {u.id: u for u in users}
        return [to_user_type(user_map[uid]) if uid in user_map else None for uid in ids]
    finally:
        db.close()


user_loader = DataLoader(load_fn=load_users)


@strawberry.federation.type(keys=["id"])
class UserType:
    id: int
    email: str
    name: str
    picture: Optional[str]
    provider: str

    @classmethod
    async def resolve_reference(cls, id: int) -> Optional["UserType"]:
        return await user_loader.load(id)


@strawberry.input
class CreateUserInput:
    email: str
    name: str
    picture: Optional[str] = None
    provider: str = "local"


@strawberry.type
class Query:
    @strawberry.field
    def users(self) -> list[UserType]:
        db = SessionLocal()
        try:
            return [to_user_type(u) for u in db.query(User).all()]
        finally:
            db.close()

    @strawberry.field
    def user(self, id: int) -> Optional[UserType]:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == id).first()
            return to_user_type(user) if user else None
        finally:
            db.close()


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, input: CreateUserInput) -> UserType:
        db = SessionLocal()
        try:
            user = User(
                email=input.email,
                name=input.name,
                picture=input.picture,
                provider=input.provider,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return to_user_type(user)
        finally:
            db.close()
