from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import strawberry
from strawberry.fastapi import GraphQLRouter
from app.database import engine, Base
from app.resolvers import Query, Mutation
from app.auth import router as auth_router  # ← add this

# Create tables
Base.metadata.create_all(bind=engine)

# Build the GraphQL schema from our Query + Mutation classes
schema = strawberry.Schema(query=Query, mutation=Mutation)

# GraphQLRouter is a FastAPI router that handles POST /graphql
graphql_app = GraphQLRouter(schema)

# add auth with Google Oauth
# graphql_app.include_router(auth_router)  # ← add this

app = FastAPI(title="GraphQL Todo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount at /graphql — this gives us the endpoint AND the GraphiQL playground
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok"}