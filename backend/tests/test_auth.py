import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.deps import get_db
from app.models import Base  # This imports all models via __init__.py
from app.models.user import UserRole
from app.core.security import create_access_token

from sqlalchemy.pool import StaticPool

# Setup In-memory SQLite with StaticPool for consistent single-connection-like behavior
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_register_user():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "role": "CUSTOMER"
        }
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password" not in data

def test_register_duplicate_email():
    payload = {
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    }
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["message"]

def test_register_admin_fails():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.com",
            "password": "password123",
            "full_name": "Admin",
            "role": "ADMIN"
        }
    )
    assert response.status_code == 403

def test_login_success():
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        }
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123", "full_name": "Test"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def get_token_for_user(email: str, role: UserRole):
    db = TestingSessionLocal()
    from app.services.auth import auth_service
    from app.schemas.auth import UserCreate
    user = auth_service.register_user(db, UserCreate(email=email, password="password123", full_name="Test", role=role))
    token = create_access_token(subject=user.id)
    db.close()
    return token

def test_rbac_customer():
    token = get_token_for_user("customer@example.com", UserRole.CUSTOMER)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Can access customer-only
    assert client.get("/api/v1/test/customer-only", headers=headers).status_code == 200
    # Cannot access organiser-only
    assert client.get("/api/v1/test/organiser-only", headers=headers).status_code == 403
    # Cannot access admin-only
    assert client.get("/api/v1/test/admin-only", headers=headers).status_code == 403

def test_rbac_organiser():
    token = get_token_for_user("org@example.com", UserRole.ORGANISER)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Can access organiser-only
    assert client.get("/api/v1/test/organiser-only", headers=headers).status_code == 200
    # Can access organiser-or-admin
    assert client.get("/api/v1/test/organiser-or-admin", headers=headers).status_code == 200
    # Cannot access customer-only (logic: unless specified otherwise)
    assert client.get("/api/v1/test/customer-only", headers=headers).status_code == 403

def test_rbac_admin():
    # We need to manually create an admin in the test DB because registration blocks it
    db = TestingSessionLocal()
    from app.core.security import get_password_hash
    from app.models.user import User
    admin = User(email="admin@example.com", hashed_password=get_password_hash("password123"), full_name="Admin", role=UserRole.ADMIN)
    db.add(admin)
    db.commit()
    token = create_access_token(subject=admin.id)
    db.close()
    
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/test/admin-only", headers=headers).status_code == 200
    assert client.get("/api/v1/test/organiser-or-admin", headers=headers).status_code == 200
