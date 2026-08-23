import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.deps import get_db
from app.models import Base


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Shared engine for all tests
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Shared session factory for all tests
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="session")
def db_engine():
    # Keep one connection open to ensure the in-memory database persists
    connection = engine.connect()
    Base.metadata.create_all(bind=connection)
    yield engine
    Base.metadata.drop_all(bind=connection)
    connection.close()


@pytest.fixture(autouse=True)
def setup_db(db_session):
    yield
    # Ensure any failed transactions are rolled back before cleanup
    db_session.rollback()
    # Clean up data after each test to ensure isolation
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()


@pytest.fixture(scope="session")
def session_factory(db_engine):
    return TestingSessionLocal


@pytest.fixture
def db_session(db_engine):
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def mock_redis_pool():
    """
    Globally mocks the ARQ Redis pool to prevent tests from attempting 
    real Redis connections.
    """
    from unittest.mock import AsyncMock, patch
    
    mock_pool = AsyncMock()
    with patch("app.core.worker.get_redis_pool", return_value=mock_pool), \
         patch("app.core.worker.create_pool", return_value=mock_pool):
        yield mock_pool
