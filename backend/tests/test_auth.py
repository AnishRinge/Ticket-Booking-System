import pytest
from app.models.user import UserRole
from app.core.security import create_access_token

def test_register_user(client):
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

def test_register_duplicate_email(client):
    payload = {
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    }
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["message"]

def test_register_admin_fails(client):
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

def test_login_success(client):
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

def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123", "full_name": "Test"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def get_token_for_user(db, email: str, role: UserRole):
    from app.services.auth import auth_service
    from app.schemas.auth import UserCreate
    user = auth_service.register_user(db, UserCreate(email=email, password="password123", full_name="Test", role=role))
    token = create_access_token(subject=user.id)
    return token

def test_rbac_customer(client, db_session):
    token = get_token_for_user(db_session, "customer@example.com", UserRole.CUSTOMER)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Can access customer-only
    assert client.get("/api/v1/test/customer-only", headers=headers).status_code == 200
    # Cannot access organiser-only
    assert client.get("/api/v1/test/organiser-only", headers=headers).status_code == 403
    # Cannot access admin-only
    assert client.get("/api/v1/test/admin-only", headers=headers).status_code == 403

def test_rbac_organiser(client, db_session):
    token = get_token_for_user(db_session, "org@example.com", UserRole.ORGANISER)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Can access organiser-only
    assert client.get("/api/v1/test/organiser-only", headers=headers).status_code == 200
    # Can access organiser-or-admin
    assert client.get("/api/v1/test/organiser-or-admin", headers=headers).status_code == 200
    # Cannot access customer-only (logic: unless specified otherwise)
    assert client.get("/api/v1/test/customer-only", headers=headers).status_code == 403

def test_rbac_admin(client, db_session):
    # We need to manually create an admin in the test DB because registration blocks it
    db = db_session
    from app.core.security import get_password_hash
    from app.models.user import User
    admin = User(email="admin@example.com", hashed_password=get_password_hash("password123"), full_name="Admin", role=UserRole.ADMIN)
    db.add(admin)
    db.commit()
    token = create_access_token(subject=admin.id)
    
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/test/admin-only", headers=headers).status_code == 200
    assert client.get("/api/v1/test/organiser-or-admin", headers=headers).status_code == 200
