from fastapi import FastAPI
import strawberry
from strawberry.fastapi import GraphQLRouter

from app.database import Base, engine
from app.schema import Mutation, Query

Base.metadata.create_all(bind=engine)

schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
)

graphql_app = GraphQLRouter(schema)

app = FastAPI(title="Users Subgraph")
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "subgraph": "users"}
