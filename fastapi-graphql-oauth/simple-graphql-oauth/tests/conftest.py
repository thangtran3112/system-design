import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User
from app import database as db_module

TEST_DB_URL = "sqlite:///./test_graphql.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Seed a test user
    db = TestSession()
    user = User(email="test@test.com", name="Tester", provider="local")
    db.add(user)
    db.commit()
    db.close()

    # Patch SessionLocal so resolvers use the test database
    original = db_module.SessionLocal
    db_module.SessionLocal = TestSession
    yield
    db_module.SessionLocal = original
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)
